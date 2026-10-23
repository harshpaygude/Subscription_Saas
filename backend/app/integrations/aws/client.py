"""AWS SDK helpers using credentials supplied for an individual connection."""
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ParamValidationError
from app.integrations.credentials import (
    CredentialStorageError,
    decrypt_credentials as _decrypt_credentials,
    encrypt_credentials as _encrypt_credentials,
)


class AWSIntegrationError(Exception):
    def __init__(self, message: str, *, category: str = "unknown"):
        super().__init__(message)
        self.category = category


def encrypt_credentials(credentials: Dict[str, Any]) -> str:
    try:
        return _encrypt_credentials(credentials)
    except CredentialStorageError as exc:
        raise AWSIntegrationError("AWS credentials could not be stored securely.", category="storage") from exc


def decrypt_credentials(token: str) -> Dict[str, Any]:
    try:
        return _decrypt_credentials(token)
    except CredentialStorageError as exc:
        raise AWSIntegrationError("Stored AWS credentials could not be decrypted.", category="storage") from exc


def _aws_error(exc: Exception, operation: str) -> AWSIntegrationError:
    """Map SDK failures to safe, user-facing categories without echoing AWS errors."""
    if isinstance(exc, NoCredentialsError):
        return AWSIntegrationError(
            "The supplied AWS credentials are missing or invalid.", category="authentication"
        )
    if isinstance(exc, ClientError):
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"InvalidClientTokenId", "SignatureDoesNotMatch", "ExpiredToken", "UnrecognizedClientException"}:
            return AWSIntegrationError(
                "AWS rejected the supplied credentials. Check the access key, secret key, and session token.",
                category="authentication",
            )
        if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "ForbiddenException"}:
            return AWSIntegrationError(
                f"AWS credentials are valid, but the identity is not authorized to {operation}.",
                category="authorization",
            )
        if code in {"InvalidRegion", "OptInRequired", "UnknownEndpoint", "EndpointConnectionError"}:
            return AWSIntegrationError(
                "The configured AWS region or service endpoint is unavailable.", category="region"
            )
    if isinstance(exc, ParamValidationError):
        return AWSIntegrationError("The AWS connection settings are invalid.", category="configuration")
    if isinstance(exc, BotoCoreError):
        return AWSIntegrationError(
            "AWS could not be reached. Check network access and the configured region.", category="network"
        )
    return AWSIntegrationError(f"AWS {operation} failed.", category="service")


def validate_region(region: str) -> str:
    normalized = (region or "").strip().lower()
    if not normalized:
        raise AWSIntegrationError("An AWS region is required.", category="configuration")
    available = set(boto3.Session().get_available_regions("ec2"))
    if normalized not in available:
        raise AWSIntegrationError(
            f"'{region}' is not a valid AWS region.", category="region"
        )
    return normalized


def _session(credentials: Dict[str, Any], region: str = "us-east-1"):
    try:
        validate_region(region)
        return boto3.Session(
            aws_access_key_id=credentials["access_key_id"],
            aws_secret_access_key=credentials["secret_access_key"],
            aws_session_token=credentials.get("session_token"),
            region_name=region,
        )
    except KeyError as exc:
        raise AWSIntegrationError("AWS access key and secret access key are required.", category="configuration") from exc


def get_aws_identity(credentials: Dict[str, Any], region: str = "us-east-1") -> Dict[str, Any]:
    try:
        return _session(credentials, region).client("sts").get_caller_identity()
    except AWSIntegrationError:
        raise
    except (ClientError, BotoCoreError, NoCredentialsError, ParamValidationError) as exc:
        raise _aws_error(exc, "identity verification") from exc


def verify_aws_connection(credentials: Dict[str, Any], region: str = "us-east-1") -> Dict[str, Any]:
    """Verify identity and the read-only Cost Explorer capability."""
    normalized_region = validate_region(region)
    identity = get_aws_identity(credentials, normalized_region)
    cost_access = check_cost_access(credentials, normalized_region)
    return {
        "account_id": identity.get("Account", ""),
        "identity_arn": identity.get("Arn", ""),
        "region": normalized_region,
        "cost_access": cost_access,
    }


def check_cost_access(credentials: Dict[str, Any], region: str = "us-east-1") -> bool:
    """Return False if Cost Explorer is not authorized or not enabled."""
    validate_region(region)
    today = date.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)  # AWS Cost Explorer's End date is exclusive.
    try:
        _session(credentials, "us-east-1").client("ce").get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        return True
    except (ClientError, BotoCoreError, NoCredentialsError, ParamValidationError):
        return False


def get_month_to_date_cost(credentials: Dict[str, Any], region: str = "us-east-1") -> Dict[str, Any]:
    validate_region(region)
    today = date.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)
    try:
        response = _session(credentials, "us-east-1").client("ce").get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
    except (ClientError, BotoCoreError, NoCredentialsError, ParamValidationError) as exc:
        raise _aws_error(exc, "retrieve AWS costs") from exc

    periods = response.get("ResultsByTime", [])
    total = "0"
    currency = "USD"
    if periods:
        metric = periods[0].get("Total", {}).get("UnblendedCost", {})
        total = metric.get("Amount", "0")
        currency = metric.get("Unit", "USD")
    return {
        "amount": total,
        "currency": currency,
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
    }


def get_account_plan_state(credentials: Dict[str, Any], region: str = "us-east-1") -> Dict[str, Any]:
    """Retrieve the AWS Free Tier plan and remaining credit balance.

    Uses the AWS Free Tier API. The caller needs freetier:GetAccountPlanState.
    """
    validate_region(region)
    try:
        response = _session(credentials, "us-east-1").client("freetier").get_account_plan_state()
    except (ClientError, BotoCoreError, NoCredentialsError, ParamValidationError) as exc:
        if isinstance(exc, ClientError) and exc.response.get("Error", {}).get("Code", "") in {
            "AccessDeniedException", "AccessDenied", "UnauthorizedOperation"
        }:
            raise AWSIntegrationError(
                "AWS Free Tier plan access is denied. Attach freetier:GetAccountPlanState to the configured AWS identity.",
                category="authorization",
            ) from exc
        raise _aws_error(exc, "retrieve AWS Free Tier plan details") from exc

    remaining = response.get("accountPlanRemainingCredits") or {}
    expiration = response.get("accountPlanExpirationDate")
    days_remaining = None
    expiration_iso = None
    if expiration is not None:
        # Botocore deserializes AWS timestamp fields to datetime objects.
        try:
            if hasattr(expiration, "date"):
                expiration_date = expiration.astimezone(timezone.utc).date() if getattr(expiration, "tzinfo", None) else expiration.date()
            else:
                expiration_date = datetime.fromtimestamp(float(expiration), tz=timezone.utc).date()
        except (TypeError, ValueError, OverflowError, OSError) as exc:
            raise AWSIntegrationError(
                "AWS returned an invalid Free Tier expiration date.", category="service"
            ) from exc
        days_remaining = (expiration_date - datetime.now(timezone.utc).date()).days
        expiration_iso = expiration_date.isoformat()

    return {
        "account_id": response.get("accountId", ""),
        "plan_type": response.get("accountPlanType", "UNKNOWN"),
        "plan_status": response.get("accountPlanStatus", "UNKNOWN"),
        "credits_remaining": remaining.get("amount"),
        "currency": remaining.get("unit", "USD"),
        "expiration_date": expiration_iso,
        "days_remaining": days_remaining,
        "original_amount": None,
        "retrieved_at": datetime.now(timezone.utc),
        "data_status": "AVAILABLE",
    }
