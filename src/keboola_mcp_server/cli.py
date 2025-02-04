"""Command-line interface for the Keboola MCP server."""

import argparse
import asyncio
import logging
import sys
from typing import List, Optional

from .config import Config
from .server import create_server

logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments. If None, uses sys.argv[1:].

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Keboola MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport to use for MCP communication",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--api-url", help="Keboola Storage API URL (defaults to https://connection.keboola.com)"
    )

    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> None:
    """Run the MCP server.

    Args:
        args: Command line arguments. If None, uses sys.argv[1:].
    """
    parsed_args = parse_args(args)

    # Create config from environment, but override with CLI args
    config = Config.from_env()
    if parsed_args.api_url:
        config.storage_api_url = parsed_args.api_url
    config.log_level = parsed_args.log_level

    try:
        # Create and run server
        mcp = create_server(config)
        mcp.run(transport=parsed_args.transport)
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
