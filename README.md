# Agmarknet MCP Server

[![Model Context Protocol](https://img.shields.io/badge/MCP-Ready-blue.svg)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://python.org)

An AI-native [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides Large Language Models (like Claude) with real-time access to Indian agricultural commodity prices across 3,000+ markets.

This server acts as a bridge between LLMs and the Indian Government's Agmarknet database (via data.gov.in), allowing you to ask natural language questions like *"Where is the cheapest place to buy onions in Maharashtra today?"*

## Features

- **MCP Protocol Native:** Built with the official Anthropic `mcp` SDK using the modern FastMCP architecture.
- **Graceful Degradation (Offline Mode):** Government APIs frequently block requests via Akamai WAFs or experience downtime. This server implements a robust fallback architecture that automatically switches to a sample offline dataset if the primary API is unreachable. *(Note: Until you provide a valid `data.gov.in` API key, the server uses static sample data for demonstration purposes, which does not reflect live market prices).*
- **Strict Data Validation:** Uses `pydantic` to enforce rigid data schemas on government API payloads, preventing AI hallucinations caused by malformed data.

## Available AI Tools

The server exposes the following tools to the LLM:

1. `get_commodity_price(commodity, state?, district?, market?)`: Get daily wholesale prices (min/max/modal) for a specific commodity.
2. `compare_markets(commodity, state?, top_n=10)`: Rank markets to find the absolute cheapest places to buy a specific commodity.
3. `get_price_summary(commodity, state?)`: Get statistical aggregates (average price, spread, most expensive market).
4. `list_commodities(search?)`: List all commodities available in the database today.
5. `list_markets(state?, commodity?)`: List all reporting mandis (markets).

## Quickstart

### 1. Installation

Clone the repository and install the Python package:

```bash
git clone https://github.com/Krishna-Baldwa/agmarket-mcp.git
cd agmarknet-mcp

# Create virtual environment and install
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configuration

Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Add your data.gov.in API key. If you leave it empty or the API is unresponsive, the server will automatically use the built-in Offline Mock Data.

### 3. Usage with Claude Desktop

To use this with Claude Desktop, add the following to your `claude_desktop_config.json` file (typically located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "agmarknet": {
      "command": "/absolute/path/to/agmarknet-mcp/.venv/bin/python",
      "args": [
        "-m",
        "agmarknet_mcp.server"
      ],
      "env": {
        "DATA_GOV_IN_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Restart Claude Desktop, and you can immediately start asking:
- *"Compare the price of tomatoes across all markets in Gujarat."*
- *"Give me a statistical summary of Onion prices."*

### Testing with MCP Inspector

You can interactively test the tools without an LLM:
```bash
npx @modelcontextprotocol/inspector python -m agmarknet_mcp.server
```

## Architecture

- **`server.py`**: Handles stdio transport and JSON-RPC lifecycle via FastMCP.
- **`api.py`**: Manages HTTP traffic via `httpx` and handles the graceful fallback mechanism.
- **`models.py`**: Pydantic models for strict type enforcement.

## Data Source
Commodity prices are sourced from the Directorate of Marketing and Inspection (DMI), Ministry of Agriculture and Farmers Welfare, Government of India, via the data.gov.in platform.

## License
MIT License