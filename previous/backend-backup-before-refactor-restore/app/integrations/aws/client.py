
"""AWS operations using per-connection IAM role assumption."""

from datetime import date, timedelta
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.config import settings
from app.integrations.aws.identity import AWSBackendIdentity, AWSIdentityError


class AWSIntegrationError(Exception):
    """Raised when an AWS integration operation fails."""


def _base_sts_client():
    """Compatibility helper returning the configured backend STS client."""
    try:
        return AWSBackendIdentity()._backend_sts()
    except AWSIdentityError as exc:
        raise AWSIntegrationError(str(exc)) from exc


def get_aws_identity() -> Dict[str, Any]:
    """Return the backend's AWS identity for diagnostics only."""
    try:
        return AWSBackendIdentity().caller_identity()
    except AWSIdentityError as exc:
        raise AWSIntegrationError(str(exc)) from exc


def assume_connection_role(
    role_arn: str,
    external_id: str,
    expected_account_id: str,
    session_name: str = "UniSoraIntegration",
) -> Dict[str, Any]:
    """
    Assume a customer-provided role and verify the resulting AWS account.

    Never trust the account ID supplied by the frontend without verifying it
    against the identity returned by AWS STS.
    """
    if not role_arn or not role_arn.startswith(("arn:aws:iam::", "arn:aws-us-gov:iam::", "arn:aws-cn:iam::")):
        raise AWSIntegrationError("Enter a valid AWS IAM role ARN.")

    if not external_id:
        raise AWSIntegrationError("The AWS external ID is missing.")

    if (
        not expected_account_id
        or not expected_account_id.isdigit()
        or len(expected_account_id) != 12
    ):
        raise AWSIntegrationError(
            "The AWS account ID must contain exactly 12 digits."
        )

    parts = role_arn.split(":")
    if len(parts) != 6 or parts[2] != "iam" or not parts[5].startswith("role/"):
        raise AWSIntegrationError("Enter a valid AWS IAM role ARN.")
    role_account_id = parts[4]
    if role_account_id != expected_account_id:
        raise AWSIntegrationError(
            "The role ARN account does not match the supplied account ID."
        )

    try:
        result = AWSBackendIdentity().assume_customer_role(
            role_arn=role_arn, external_id=external_id, session_name=session_name
        )
        session = result["session"]
        identity = result["identity"]

        if identity.get("Account") != expected_account_id:
            raise AWSIntegrationError(
                "The assumed role resolved to a different AWS account."
            )

        return {
            "session": session,
            "identity": identity,
            "expiration": result["expiration"],
        }

    except AWSIntegrationError:
        raise
    except AWSIdentityError as exc:
        raise AWSIntegrationError(str(exc)) from exc
    except (ClientError, BotoCoreError, KeyError) as exc:
        error_code = ""
        if isinstance(exc, ClientError):
            error_code = exc.response.get("Error", {}).get("Code", "")

        if error_code in (
            "AccessDenied",
            "AccessDeniedException",
            "InvalidClientTokenId",
        ):
            raise AWSIntegrationError(
                "AWS role assumption was denied. Check the role trust policy, "
                "external ID, backend IAM identity, and permissions."
            ) from exc

        raise AWSIntegrationError(
            "Could not assume the configured AWS role."
        ) from exc


def check_cost_access(session: boto3.Session) -> bool:
    """Check Cost Explorer access using the supplied AWS session."""
    today = date.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)

    try:
        session.client(
            "ce", region_name=settings.aws_region
        ).get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": end.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        return True
    except (ClientError, BotoCoreError):
        return False


def get_month_to_date_cost(session: boto3.Session) -> Dict[str, Any]:
    """Retrieve month-to-date costs from the specified AWS account."""
    today = date.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)

    try:
        response = session.client(
            "ce", region_name=settings.aws_region
        ).get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": end.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
    except (ClientError, BotoCoreError) as exc:
        raise AWSIntegrationError(
            "Could not retrieve AWS costs. Check Cost Explorer access "
            "and the connected role's permissions."
        ) from exc

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


def get_account_plan_state(session: boto3.Session) -> Dict[str, Any]:
    """Retrieve the connected AWS account's Free Tier plan and credits."""
    try:
        response = session.client(
            "freetier", region_name=settings.aws_region
        ).get_account_plan_state()
    except (ClientError, BotoCoreError) as exc:
        error_code = ""
        if isinstance(exc, ClientError):
            error_code = exc.response.get("Error", {}).get("Code", "")

        if error_code in (
            "AccessDeniedException",
            "AccessDenied",
            "UnauthorizedOperation",
        ):
            raise AWSIntegrationError(
                "Free Tier plan access is denied. Check the connected "
                "role's freetier:GetAccountPlanState permission."
            ) from exc

        raise AWSIntegrationError(
            "Could not retrieve AWS Free Tier plan details."
        ) from exc

    remaining = response.get("accountPlanRemainingCredits") or {}
    expiration = response.get("accountPlanExpirationDate")
    days_remaining: Optional[int] = None
    expiration_iso: Optional[str] = None

    if expiration is not None:
        if hasattr(expiration, "date"):
            expiration_date = expiration.date()
        else:
            from datetime import datetime

            expiration_date = datetime.fromtimestamp(float(expiration)).date()

        days_remaining = max((expiration_date - date.today()).days, 0)
        expiration_iso = expiration_date.isoformat()

    return {
        "account_id": response.get("accountId", ""),
        "plan_type": response.get("accountPlanType", "UNKNOWN"),
        "plan_status": response.get("accountPlanStatus", "UNKNOWN"),
        "credits_remaining": remaining.get("amount"),
        "currency": remaining.get("unit", "USD"),
        "expiration_date": expiration_iso,
        "days_remaining": days_remaining,
    }

