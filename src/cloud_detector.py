"""
Cloud provider detection and configuration helper.

This module detects which cloud platform the application is running on
and provides appropriate configuration without breaking existing GCP functionality.
"""

import os
import logging

logger = logging.getLogger(__name__)


def detect_cloud_provider():
    """
    Detect which cloud provider we're running on.

    Returns:
        str: One of 'gcp', 'aws', 'azure', or 'local'

    Note: GCP detection remains exactly as it was to maintain backward compatibility.
    """
    # Check for GCP Cloud SQL (existing logic preserved)
    if os.getenv("CLOUD_SQL_CONNECTION_NAME"):
        logger.info("Detected Google Cloud Platform (Cloud SQL)")
        return "gcp"

    # Check for AWS
    if os.getenv("AWS_EXECUTION_ENV") or os.getenv("AWS_RDS_ENDPOINT"):
        logger.info("Detected Amazon Web Services")
        return "aws"

    # Check for Azure
    if os.getenv("WEBSITE_INSTANCE_ID") or os.getenv("AZURE_POSTGRES_HOST"):
        logger.info("Detected Microsoft Azure")
        return "azure"

    # Check for generic DATABASE_URL (could be any cloud or local)
    if os.getenv("DATABASE_URL"):
        logger.info("Using DATABASE_URL - assuming local/generic deployment")
        return "local"

    logger.info("No cloud provider detected, assuming local development")
    return "local"


def get_aws_connection_string():
    """
    Build connection string for AWS RDS PostgreSQL.

    Returns:
        str: PostgreSQL connection string for AWS RDS

    Note: This is EXPERIMENTAL and UNTESTED.
    """
    logger.warning("AWS RDS support is EXPERIMENTAL and has not been tested in production")

    endpoint = os.getenv("AWS_RDS_ENDPOINT")
    port = os.getenv("AWS_RDS_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "synthea")

    # Support for IAM authentication (future enhancement)
    use_iam = os.getenv("AWS_RDS_USE_IAM", "false").lower() == "true"

    if use_iam:
        logger.warning("AWS RDS IAM authentication is not yet implemented")
        # Future: Implement IAM token generation

    if not endpoint:
        logger.error("AWS_RDS_ENDPOINT not set")
        return ""

    # SSL is recommended for RDS
    ssl_mode = "require" if os.getenv("AWS_RDS_SSL", "true").lower() == "true" else "prefer"

    return (
        f"postgresql://{db_user}:{db_password}@{endpoint}:{port}/{db_name}"
        f"?sslmode={ssl_mode}"
    )


def get_azure_connection_string():
    """
    Build connection string for Azure Database for PostgreSQL.

    Returns:
        str: PostgreSQL connection string for Azure

    Note: This is EXPERIMENTAL and UNTESTED.
    """
    logger.warning("Azure PostgreSQL support is EXPERIMENTAL and has not been tested in production")

    host = os.getenv("AZURE_POSTGRES_HOST")
    port = os.getenv("AZURE_POSTGRES_PORT", "5432")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "synthea")

    # Azure often uses username@servername format
    if host and db_user and "@" not in db_user:
        server_name = host.split('.')[0]  # Extract server name from FQDN
        db_user = f"{db_user}@{server_name}"

    if not host:
        logger.error("AZURE_POSTGRES_HOST not set")
        return ""

    # SSL is required for Azure PostgreSQL
    ssl_mode = "require"

    return (
        f"postgresql://{db_user}:{db_password}@{host}:{port}/{db_name}"
        f"?sslmode={ssl_mode}"
    )


def get_connection_string_for_provider(provider=None):
    """
    Get the appropriate connection string for the detected or specified cloud provider.

    Args:
        provider: Optional provider override. If None, auto-detects.

    Returns:
        str: PostgreSQL connection string

    Note: This function is designed to be called from synthea_server.py
          without breaking existing GCP functionality.
    """
    if provider is None:
        provider = detect_cloud_provider()

    if provider == "gcp":
        # Return None to let synthea_server.py use its existing GCP logic
        # This ensures 100% backward compatibility
        return None
    elif provider == "aws":
        return get_aws_connection_string()
    elif provider == "azure":
        return get_azure_connection_string()
    else:
        # Local or generic deployment
        return os.getenv("DATABASE_URL", "")


def get_cloud_specific_settings(provider=None):
    """
    Get cloud-specific settings and recommendations.

    Returns:
        dict: Cloud-specific configuration settings
    """
    if provider is None:
        provider = detect_cloud_provider()

    settings = {
        "provider": provider,
        "tested": provider == "gcp",  # Only GCP is tested
        "warning": None
    }

    if provider == "aws":
        settings["warning"] = "AWS deployment is EXPERIMENTAL and UNTESTED. Use at your own risk."
        settings["recommendations"] = [
            "Use RDS PostgreSQL 13+ for JSONB support",
            "Enable automated backups",
            "Configure VPC security groups appropriately",
            "Consider using RDS Proxy for connection pooling"
        ]
    elif provider == "azure":
        settings["warning"] = "Azure deployment is EXPERIMENTAL and UNTESTED. Use at your own risk."
        settings["recommendations"] = [
            "Use Azure Database for PostgreSQL Flexible Server",
            "Enable SSL enforcement",
            "Configure firewall rules appropriately",
            "Consider using connection pooling"
        ]
    elif provider == "gcp":
        settings["recommendations"] = [
            "Use Cloud SQL PostgreSQL 13+ for JSONB support",
            "Enable automated backups",
            "Use Cloud SQL Proxy for secure connections",
            "Configure VPC for private IP if needed"
        ]

    return settings