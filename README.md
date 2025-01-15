# Keboola MCP Server

[![CI](https://github.com/jordanburger/keboola-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/jordanburger/keboola-mcp-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jordanburger/keboola-mcp-server/branch/main/graph/badge.svg)](https://codecov.io/gh/jordanburger/keboola-mcp-server)
<a href="https://glama.ai/mcp/servers/72mwt1x862"><img width="380" height="200" src="https://glama.ai/mcp/servers/72mwt1x862/badge" alt="Keboola Explorer Server MCP server" /></a>

A Model Context Protocol (MCP) server for interacting with Keboola Connection. This server provides tools for listing and accessing data from Keboola Storage API.

## Installation

First, install `uv` if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repository and create a virtual environment:

```bash
git clone https://github.com/jordanburger/keboola-mcp-server.git
cd keboola-mcp-server
uv venv
source .venv/bin/activate
```

Install the package in development mode:

```bash
uv pip install -e .
```

For development dependencies:

```bash
uv pip install -e ".[dev]"
```

## Running the MCP Inspector

To test the server locally with the MCP Inspector:

1. Make sure you're in the virtual environment:
```bash
source .venv/bin/activate
```

2. Set your Keboola Storage API token:
```bash
export KBC_STORAGE_TOKEN="your-keboola-storage-token"
```

3. Run the server with the MCP Inspector:
```bash
uv pip install mcp[inspector]  # Install the inspector if you haven't already
uv run -m mcp.inspector -s "uv run -m keboola_mcp_server.cli --api-url https://connection.YOUR_REGION.keboola.com"
```

Replace:
- `your-keboola-storage-token` with your actual Keboola Storage API token
- `YOUR_REGION` with your Keboola region (e.g., `north-europe.azure`, `connection`, etc.)

The MCP Inspector will open in your default web browser, allowing you to test all available tools and resources.

## Claude Desktop Setup

To use this server with Claude Desktop, follow these steps:

1. Create or edit the Claude Desktop configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the following configuration (adjust paths according to your setup):

```json
{
  "mcpServers": {
    "keboola": {
      "command": "/usr/local/bin/uv",
      "args": [
        "run",
        "-m",
        "keboola_mcp_server.cli",
        "--log-level",
        "DEBUG",
        "--api-url",
        "https://connection.YOUR_REGION.keboola.com"
      ],
      "env": {
        "KBC_STORAGE_TOKEN": "your-keboola-storage-token",
        "PYTHONPATH": "/path/to/keboola-mcp-server/src"
      }
    }
  }
}
```

Replace:
- `/usr/local/bin/uv` with the path to your `uv` installation (find it using `which uv`)
- `/path/to/keboola-mcp-server` with your actual path to the cloned repository
- `your-keboola-storage-token` with your Keboola Storage API token
- `YOUR_REGION` with your Keboola region (e.g., `north-europe.azure`, `connection`, etc.)

3. After updating the configuration:
   - Completely quit Claude Desktop (don't just close the window)
   - Restart Claude Desktop
   - Look for the hammer icon in the bottom right corner, indicating the server is connected

### Troubleshooting

If you encounter connection issues:
1. Check the logs in Claude Desktop for any error messages
2. Verify your Keboola Storage API token is correct
3. Ensure all paths in the configuration are absolute paths (use `which uv` to find the correct path)
4. Make sure the PYTHONPATH points to the `src` directory
5. Try running the server with the MCP Inspector to test if it works outside Claude Desktop

## Available Tools

The server provides the following tools for interacting with Keboola Connection:

- List buckets and tables
- Get bucket and table information
- Preview table data
- Export table data to CSV
- List components and configurations

## Development

Run tests:

```bash
uv run pytest
```

Format code:

```bash
uv run black .
uv run isort .
```

Type checking:

```bash
uv run mypy .
```

## License

MIT License - see LICENSE file for details.
