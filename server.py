from mcp.server.fastmcp import FastMCP, Context
import httpx
from typing import List, Dict, Any, Optional
import pandas as pd
from io import StringIO

class KeboolaClient:
    """Helper class to interact with Keboola Storage API"""
    def __init__(self, storage_api_token: str, storage_api_url: str = "https://connection.keboola.com"):
        self.token = storage_api_token
        self.base_url = f"{storage_api_url}/v2/storage"
        self.headers = {
            "X-StorageApi-Token": self.token,
            "Content-Type": "application/json"
        }
    
    async def get(self, endpoint: str) -> Dict[str, Any]:
        """Make a GET request to Keboola Storage API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{endpoint}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_csv(self, endpoint: str) -> str:
        """Make a GET request expecting CSV response"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{endpoint}",
                headers={**self.headers, "Content-Type": "text/csv"}
            )
            response.raise_for_status()
            return response.text

# Initialize FastMCP server
mcp = FastMCP(
    "Keboola Explorer",
    dependencies=["httpx", "pandas"]
)

# Create Keboola client instance
keboola: Optional[KeboolaClient] = None

# Initialize Keboola client
def initialize_client():
    """Initialize Keboola client from environment variables"""
    import os
    
    token = os.getenv("KEBOOLA_STORAGE_TOKEN")
    api_url = os.getenv("KEBOOLA_STORAGE_API_URL", "https://connection.keboola.com")
    
    if not token:
        raise ValueError("KEBOOLA_STORAGE_TOKEN environment variable is required")
        
    return KeboolaClient(token, api_url)

# Set up logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Initializing Keboola client...")
try:
    # Create Keboola client instance
    keboola = initialize_client()
    logger.info("Successfully initialized Keboola client")
except Exception as e:
    logger.error(f"Failed to initialize Keboola client: {e}")
    raise

# Resources
@mcp.resource("keboola://buckets")
async def list_buckets() -> str:
    """List all available buckets in Keboola project"""
    buckets = await keboola.get("buckets")
    return "\n".join(f"- {bucket['id']}: {bucket['name']} ({bucket['description']})" 
                    for bucket in buckets)

@mcp.resource("keboola://buckets/{bucket_id}/tables")
async def list_bucket_tables(bucket_id: str) -> str:
    """List all tables in a specific bucket"""
    tables = await keboola.get(f"buckets/{bucket_id}/tables")
    return "\n".join(f"- {table['id']}: {table['name']} (Rows: {table['rowsCount']})" 
                    for table in tables)

@mcp.resource("keboola://components")
async def list_components() -> str:
    """List all available components and their configurations"""
    components = await keboola.get("components")
    return "\n".join(f"- {comp['id']}: {comp['name']}" 
                    for comp in components)

# Tools
@mcp.tool()
async def get_bucket_info(bucket_id: str) -> str:
    """Get detailed information about a specific bucket
    
    Args:
        bucket_id: ID of the bucket to get info for
    """
    bucket = await keboola.get(f"buckets/{bucket_id}")
    return (f"Bucket Information:\n"
            f"ID: {bucket['id']}\n"
            f"Name: {bucket['name']}\n"
            f"Description: {bucket['description']}\n"
            f"Created: {bucket['created']}\n"
            f"Tables Count: {bucket['tablesCount']}\n"
            f"Data Size Bytes: {bucket['dataSizeBytes']}")

@mcp.tool()
async def get_table_preview(table_id: str, limit: int = 100) -> str:
    """Get a preview of data from a specific table as CSV
    
    Args:
        table_id: ID of the table to preview
        limit: Maximum number of rows to return (default: 100)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{keboola.base_url}/tables/{table_id}/data-preview/",
            headers={
                'X-StorageApi-Token': keboola.token,
                'Content-Type': 'text/csv',
                'Accept-encoding': 'gzip'
            }
        )
        response.raise_for_status()
        
        # Read into pandas to handle the row limit
        df = pd.read_csv(StringIO(response.text))
        df = df.head(limit)
        
        # Convert back to CSV and add metadata header for Claude
        csv_data = df.to_csv(index=False)
        return f"```csv\n{csv_data}```"

@mcp.tool()
async def get_table_info(table_id: str) -> str:
    """Get detailed information about a specific table
    
    Args:
        table_id: ID of the table to get info for
    """
    table = await keboola.get(f"tables/{table_id}")
    return (f"Table Information:\n"
            f"ID: {table['id']}\n"
            f"Name: {table.get('name', 'N/A')}\n"
            f"Primary Key: {', '.join(table.get('primaryKey', []))}\n"
            f"Created: {table.get('created', 'N/A')}\n"
            f"Row Count: {table.get('rowsCount', 'N/A')}\n"
            f"Data Size Bytes: {table.get('dataSizeBytes', 'N/A')}\n"
            f"Columns: {', '.join(table.get('columns', []))}")

@mcp.tool()
async def list_component_configs(component_id: str) -> str:
    """List all configurations for a specific component
    
    Args:
        component_id: ID of the component to list configurations for
    """
    configs = await keboola.get(f"components/{component_id}/configs")
    return "\n".join(
        f"Configuration: {config['id']}\n"
        f"Name: {config['name']}\n"
        f"Description: {config['description']}\n"
        f"Created: {config['created']}\n"
        f"---"
        for config in configs
    )

@mcp.tool()
async def list_all_buckets() -> str:
    """List all buckets in the project with their basic information"""
    buckets = await keboola.get("buckets")
    return "\n".join(
        f"Bucket: {bucket['id']}\n"
        f"Name: {bucket.get('name', 'N/A')}\n"
        f"Description: {bucket.get('description', 'N/A')}\n"
        f"Stage: {bucket.get('stage', 'N/A')}\n"
        f"Created: {bucket.get('created', 'N/A')}\n"
        f"---"
        for bucket in buckets
    )

@mcp.tool()
async def list_bucket_tables_tool(bucket_id: str) -> str:
    """List all tables in a specific bucket with their basic information
    
    Args:
        bucket_id: ID of the bucket to list tables from
    """
    tables = await keboola.get(f"buckets/{bucket_id}/tables")
    return "\n".join(
        f"Table: {table['id']}\n"
        f"Name: {table.get('name', 'N/A')}\n"
        f"Rows: {table.get('rowsCount', 'N/A')}\n"
        f"Size: {table.get('dataSizeBytes', 'N/A')} bytes\n"
        f"Columns: {', '.join(table.get('columns', []))}\n"
        f"---"
        for table in tables
    )

if __name__ == "__main__":
    mcp.run(transport="stdio")