"""Configuration handling for the Keboola MCP server."""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Server configuration."""

    storage_token: str
    storage_api_url: str = "https://connection.keboola.com"
    log_level: str = "INFO"
    # Add Snowflake credentials
    snowflake_account: Optional[str] = None
    snowflake_user: Optional[str] = None
    snowflake_password: Optional[str] = None
    snowflake_warehouse: Optional[str] = None
    snowflake_database: Optional[str] = None
    snowflake_schema: Optional[str] = None
    snowflake_role: Optional[str] = None

    def __init__(
        self,
        storage_token: str,
        storage_api_url: str = "https://connection.keboola.com",
        snowflake_account: Optional[str] = None,
        snowflake_user: Optional[str] = None,
        snowflake_password: Optional[str] = None,
        snowflake_warehouse: Optional[str] = None,
        snowflake_database: Optional[str] = None,
        snowflake_role: Optional[str] = None,
        snowflake_schema: Optional[str] = None,
        log_level: str = "INFO",
    ):
        self.storage_token = storage_token
        self.storage_api_url = storage_api_url
        self.snowflake_account = snowflake_account
        self.snowflake_user = snowflake_user
        self.snowflake_password = snowflake_password
        self.snowflake_warehouse = snowflake_warehouse
        self.snowflake_database = snowflake_database
        self.snowflake_role = snowflake_role
        self.snowflake_schema = snowflake_schema
        self.log_level = log_level

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        # Add debug logging using logger instead of print
        for env_var in [
            "KBC_SNOWFLAKE_ACCOUNT",
            "KBC_SNOWFLAKE_USER",
            "KBC_SNOWFLAKE_PASSWORD",
            "KBC_SNOWFLAKE_WAREHOUSE",
            "KBC_SNOWFLAKE_DATABASE",
            "KBC_SNOWFLAKE_ROLE",
            "KBC_SNOWFLAKE_SCHEMA",
        ]:
            logger.debug(f"Reading {env_var}: {'set' if os.getenv(env_var) else 'not set'}")

        storage_token = os.getenv("KBC_STORAGE_TOKEN")
        if not storage_token:
            raise ValueError("KBC_STORAGE_TOKEN environment variable is required")

        return cls(
            storage_token=storage_token,
            storage_api_url=os.getenv("KBC_STORAGE_API_URL", "https://connection.keboola.com"),
            snowflake_account=os.getenv("KBC_SNOWFLAKE_ACCOUNT"),
            snowflake_user=os.getenv("KBC_SNOWFLAKE_USER"),
            snowflake_password=os.getenv("KBC_SNOWFLAKE_PASSWORD"),
            snowflake_warehouse=os.getenv("KBC_SNOWFLAKE_WAREHOUSE"),
            snowflake_database=os.getenv("KBC_SNOWFLAKE_DATABASE"),
            snowflake_role=os.getenv("KBC_SNOWFLAKE_ROLE"),
            snowflake_schema=os.getenv("KBC_SNOWFLAKE_SCHEMA"),
            log_level=os.getenv("KBC_LOG_LEVEL", "INFO"),
        )

    def validate(self) -> None:
        """Validate the configuration."""
        if not self.storage_token:
            raise ValueError("Storage token not configured")
        if not self.storage_api_url:
            raise ValueError("Storage API URL is required")
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.log_level}")

    def has_snowflake_config(self) -> bool:
        """Check if Snowflake configuration is complete."""
        return all(
            [
                self.snowflake_account,
                self.snowflake_user,
                self.snowflake_password,
                self.snowflake_warehouse,
                self.snowflake_database,
            ]
        )
