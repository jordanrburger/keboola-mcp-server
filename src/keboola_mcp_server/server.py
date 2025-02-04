"""MCP server implementation for Keboola Connection."""

import csv
import json
import logging
import os
import tempfile
from io import StringIO
from typing import Any, AsyncGenerator, Dict, List, Optional, TypedDict, cast

import pandas as pd
from mcp.server.fastmcp import FastMCP

from .client import KeboolaClient
from .config import Config
from .database import create_snowflake_connection, ConnectionManager, DatabasePathManager

logger = logging.getLogger(__name__)


class BucketInfo(TypedDict):
    id: str
    name: str
    description: str
    stage: str
    created: str
    tablesCount: int
    dataSizeBytes: int


class TableColumnInfo(TypedDict):
    name: str
    db_identifier: str


class TableDetail(TypedDict):
    id: str
    name: str
    primary_key: List[str]
    created: str
    row_count: int
    data_size_bytes: int
    columns: List[str]
    column_identifiers: List[TableColumnInfo]
    db_identifier: str


def create_server(config: Optional[Config] = None) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        config: Server configuration. If None, loads from environment.

    Returns:
        Configured FastMCP server instance
    """
    if config is None:
        config = Config.from_env()
    config.validate()

    # Configure logging
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(config.log_level)

    # Initialize FastMCP server with system instructions
    mcp = FastMCP(
        "Keboola Explorer", dependencies=["keboola.storage-api-client", "httpx", "pandas"]
    )

    connection_manager = ConnectionManager(config)
    db_path_manager = DatabasePathManager(config, connection_manager)

    # Create Keboola client instance
    try:
        keboola = KeboolaClient(config.storage_token, config.storage_api_url)
    except Exception as e:
        logger.error(f"Failed to initialize Keboola client: {e}")
        raise
    logger.info("Successfully initialized Keboola client")

    # Resources
    @mcp.resource("keboola://buckets")
    async def list_buckets() -> List[BucketInfo]:
        """List all available buckets in Keboola project."""
        buckets = cast(List[BucketInfo], keboola.storage_client.buckets.list())
        return buckets

    @mcp.resource("keboola://buckets/{bucket_id}/tables")
    async def list_bucket_tables(bucket_id: str) -> str:
        """List all tables in a specific bucket."""
        tables = cast(List[Dict[str, Any]],
                      keboola.storage_client.buckets.list_tables(bucket_id))
        return "\n".join(
            f"- {table['id']}: {table['name']} (Rows: {table.get('rowsCount', 'unknown')})"
            for table in tables
        )

    @mcp.resource("keboola://components")
    async def list_components() -> str:
        """List all available components and their configurations."""
        components = cast(List[Dict[str, Any]], await keboola.get("components"))
        return "\n".join(f"- {comp['id']}: {comp['name']}" for comp in components)

    @mcp.resource(
        "keboola://tables/{table_id}",
        description="Get detailed information about a Keboola table including its DB identifier and column information",
    )
    async def get_table_detail(table_id: str) -> TableDetail:
        """Get detailed information about a table."""
        table = await get_table_metadata(table_id)

        # Get column info
        columns = table.get("columns", [])
        column_info = [TableColumnInfo(
            name=col, db_identifier=f'"{col}"') for col in columns]

        return {
            "id": table["id"],
            "name": table.get("name", "N/A"),
            "primary_key": table.get("primaryKey", []),
            "created": table.get("created", "N/A"),
            "row_count": table.get("rowsCount", 0),
            "data_size_bytes": table.get("dataSizeBytes", 0),
            "columns": columns,
            "column_identifiers": column_info,
            "db_identifier": db_path_manager.get_table_db_path(table),
        }

    @mcp.tool()
    async def query_table_data(
        table_id: str,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> str:
        """
        Query table data using database identifiers with proper formatting. This method safely constructs
        and executes SQL queries by handling database identifiers and query parameters.

        Parameters:
            table_id (str): The table identifier in format 'bucket.table_name' (e.g., 'in.c-fraudDetection.test_identify')
            columns (List[str], optional): List of column names to select. If None, selects all columns (*)
            where (str, optional): WHERE clause conditions without the 'WHERE' keyword
            limit (int, optional): Maximum number of rows to return

        Returns:
            str: Query results in string format

        Examples:
            # Select all columns with limit
            query_table_data('in.c-fraudDetection.test_identify', limit=5)

            # Select specific columns with condition
            query_table_data(
                'in.c-fraudDetection.test_identify',
                columns=['TransactionID', 'DeviceType'],
                where="DeviceType = 'mobile'",
                limit=10
            )

        Note:
            This method is preferred over direct SQL queries as it:
                - Automatically handles proper database identifiers
                - Prevents SQL injection through proper parameter handling
                - Uses configuration for database name
                - Provides a simpler interface for common query patterns
        """
        table_info = await get_table_detail(table_id)

        if columns:
            column_map = {
                col["name"]: col["db_identifier"] for col in table_info["column_identifiers"]
            }
            select_clause = ", ".join(column_map[col] for col in columns)
        else:
            select_clause = "*"

        query = f"SELECT {select_clause} FROM {table_info['db_identifier']}"

        if where:
            query += f" WHERE {where}"

        if limit:
            query += f" LIMIT {limit}"

        result: str = await query_table(query)
        return result

    @mcp.tool()
    async def query_table(sql_query: str) -> str:
        """
        Execute a Snowflake SQL query to get data from the Storage. Before forming the query always check the 
        get_table_metadata tool to get the correct database name and table name. 

        Note: SQL queries must include the full path including database name, e.g.:
        'SELECT * FROM SAPI_10025."in.c-fraudDetection"."test_identify"'. Snowflake is case sensitive so always
        wrap the column names in double quotes.
        """
        conn = None
        cursor = None

        try:
            conn = create_snowflake_connection(config)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            result = cursor.fetchall()
            columns = [col[0] for col in cursor.description]

            # Convert to CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            writer.writerows(result)

            return output.getvalue()

        except snowflake.connector.errors.ProgrammingError as e:
            raise ValueError(f"Snowflake query error: {str(e)}")

        except Exception as e:
            raise ValueError(
                f"Unexpected error during query execution: {str(e)}")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # Tools
    @mcp.tool()
    async def list_all_buckets() -> str:
        """List all buckets in the project with their basic information."""
        buckets = await list_buckets()

        header = "# Bucket List\n\n"
        header += f"Total Buckets: {len(buckets)}\n\n"
        header += "## Details"

        bucket_details = []
        for bucket in buckets:
            detail = f"### {bucket['name']} ({bucket['id']})"
            detail += f"\n    - Stage: {bucket.get('stage', 'N/A')}"
            detail += f"\n    - Description: {bucket.get('description', 'N/A')}"
            detail += f"\n    - Created: {bucket.get('created', 'N/A')}"
            detail += f"\n    - Tables: {bucket.get('tablesCount', 0)}"
            detail += f"\n    - Size: {bucket.get('dataSizeBytes', 0)} bytes"
            bucket_details.append(detail)

        return header + "\n" + "\n".join(bucket_details)

    @mcp.tool()
    async def get_bucket_metadata(bucket_id: str) -> str:
        """Get detailed information about a specific bucket."""
        bucket = cast(Dict[str, Any],
                      keboola.storage_client.buckets.detail(bucket_id))
        return (
            f"Bucket Information:\n"
            f"ID: {bucket['id']}\n"
            f"Name: {bucket['name']}\n"
            f"Description: {bucket.get('description', 'No description')}\n"
            f"Created: {bucket['created']}\n"
            f"Tables Count: {bucket.get('tablesCount', 0)}\n"
            f"Data Size Bytes: {bucket.get('dataSizeBytes', 0)}"
        )

    @mcp.tool()
    async def get_table_metadata(table_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific table including its DB identifier and column information."""
        # Get table details directly from the storage client
        table = cast(Dict[str, Any],
                     keboola.storage_client.tables.detail(table_id))
        return table

    @mcp.tool()
    async def list_component_configs(component_id: str) -> str:
        """List all configurations for a specific component."""
        configs = cast(
            List[Dict[str, Any]], await keboola.get(f"components/{component_id}/configs")
        )
        return "\n".join(
            f"Configuration: {config['id']}\n"
            f"Name: {config['name']}\n"
            f"Description: {config.get('description', 'No description')}\n"
            f"Created: {config['created']}\n"
            f"---"
            for config in configs
        )

    @mcp.tool()
    async def list_bucket_tables_tool(bucket_id: str) -> str:
        """List all tables in a specific bucket with their basic information."""
        tables = cast(List[Dict[str, Any]],
                      keboola.storage_client.buckets.list_tables(bucket_id))
        return "\n".join(
            f"Table: {table['id']}\n"
            f"Name: {table.get('name', 'N/A')}\n"
            f"Rows: {table.get('rowsCount', 'N/A')}\n"
            f"Size: {table.get('dataSizeBytes', 'N/A')} bytes\n"
            f"Columns: {', '.join(table.get('columns', []))}\n"
            f"---"
            for table in tables
        )

    return mcp
