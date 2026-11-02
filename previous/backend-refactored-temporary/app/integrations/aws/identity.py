"""AWS backend identity abstraction.

The provider uses this boundary instead of depending on a developer's
credentials. In local development, the configured AWS profile/default chain
may bootstrap the dedicated backend role, but that identity is never stored
as a customer connection and is never presented as the customer principal.
"""

from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.config import settings


class AWSIdentityError(Exception):
    pass


class AWSBackendIdentity:
    def _bootstrap_session(self):
        if settings.aws_bootstrap_profile:
            return boto3.Session(profile_name=settings.aws_bootstrap_profile)
        return boto3.Session()

    def _backend_sts(self):
        if not settings.aws_backend_role_arn:
            raise AWSIdentityError(
                "AWS_BACKEND_ROLE_ARN is required. Configure the dedicated "
                "UniSora backend IAM role before using AWS integrations."
            )
        try:
            bootstrap = self._bootstrap_session()
            sts = bootstrap.client("sts", region_name=settings.aws_region)
            assumed = sts.assume_role(
                RoleArn=settings.aws_backend_role_arn,
                RoleSessionName="UniSoraBackendIdentity",
                DurationSeconds=settings.aws_role_session_duration_seconds,
            )
            credentials = assumed["Credentials"]
            return boto3.client(
                "sts",
                region_name=settings.aws_region,
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
        except (BotoCoreError, ClientError, NoCredentialsError, KeyError) as exc:
            raise AWSIdentityError(
                "Could not assume the configured UniSora backend IAM role. "
                "Check AWS_BACKEND_ROLE_ARN and the local bootstrap credentials."
            ) from exc

    def principal_arn(self) -> str:
        if not settings.aws_backend_role_arn:
            raise AWSIdentityError(
                "AWS_BACKEND_ROLE_ARN is required to generate AWS trust policy instructions."
            )
        return settings.aws_backend_role_arn

    def caller_identity(self) -> Dict[str, Any]:
        try:
            return self._backend_sts().get_caller_identity()
        except (AWSIdentityError, BotoCoreError, ClientError) as exc:
            if isinstance(exc, AWSIdentityError):
                raise
            raise AWSIdentityError("Could not verify the UniSora backend AWS identity.") from exc

    def assume_customer_role(
        self, role_arn: str, external_id: str, session_name: str
    ) -> Dict[str, Any]:
        try:
            response = self._backend_sts().assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                ExternalId=external_id,
                DurationSeconds=settings.aws_role_session_duration_seconds,
            )
            credentials = response["Credentials"]
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=settings.aws_region,
            )
            identity = session.client("sts", region_name=settings.aws_region).get_caller_identity()
            return {"session": session, "identity": identity, "expiration": credentials["Expiration"]}
        except (AWSIdentityError, BotoCoreError, ClientError, KeyError) as exc:
            if isinstance(exc, AWSIdentityError):
                raise
            code = exc.response.get("Error", {}).get("Code", "") if isinstance(exc, ClientError) else ""
            if code in ("AccessDenied", "AccessDeniedException", "InvalidClientTokenId"):
                raise AWSIdentityError(
                    "AWS role assumption was denied. Check the customer trust policy, "
                    "external ID, backend IAM role, and permissions."
                ) from exc
            raise AWSIdentityError("Could not assume the configured AWS customer role.") from exc
