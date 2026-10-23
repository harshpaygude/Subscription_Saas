"""AWS SDK helpers. Uses the standard Boto3 credential chain (AWS CLI profile/env/role)."""
from datetime import date, timedelta
from typing import Dict, Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


class AWSIntegrationError(Exception):
    pass


def get_aws_identity() -> Dict[str, Any]:
    try:
        return boto3.client("sts").get_caller_identity()
    except NoCredentialsError as exc:
        raise AWSIntegrationError(
            "AWS credentials were not found. Configure AWS CLI credentials on the backend machine."
        ) from exc
    except (ClientError, BotoCoreError) as exc:
        raise AWSIntegrationError("Could not verify AWS identity: {}".format(exc)) from exc


def check_cost_access() -> bool:
    """Return False if Cost Explorer is not authorized or not enabled."""
    today = date.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)  # AWS Cost Explorer's End date is exclusive.
    try:
        boto3.client("ce", region_name="us-east-1").get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        return True
    except (ClientError, BotoCoreError):
        return False


def get_month_to_date_cost() -> Dict[str, Any]:
    today = date.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)
    try:
        response = boto3.client("ce", region_name="us-east-1").get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
    except (ClientError, BotoCoreError) as exc:
        raise AWSIntegrationError(
            "Could not retrieve AWS costs. Check Cost Explorer access and IAM permissions: {}".format(exc)
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
