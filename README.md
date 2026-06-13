# Agmarknet MCP Server

[![Model Context Protocol](https://img.shields.io/badge/MCP-Ready-blue.svg)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that gives LLMs (like Claude) access to Indian agricultural commodity prices — daily wholesale min/max/modal rates across thousands of mandis (regulated markets) and hundreds of commodities.

Ask a model *"Where were tomatoes cheapest in Pune last month?"* and it answers from real market data.

---

## Pick your implementation

The project lives on two branches with different data sources. They expose the same kind of tools; choose by your data needs.

| | **`main`** | **`feat/ceda-api-migration`** |
|---|---|---|
| **Data source** | [data.gov.in](https://data.gov.in) Agmarknet | [CEDA Agri Market API](https://api.ceda.ashoka.edu.in) (Ashoka University) |
| **API key** | `DATA_GOV_IN_API_KEY` (free) | `CEDA_API_KEY` (free) |
| **Without a key** | Serves a small **sample dataset** so the tools work out of the box — for flavour only, not live prices | Will not run — a key is required |
| **To use real data** | Add the key to `.env` **and** set `use_mock=False` in `server.py` | Add the key to `.env` |
| **Data coverage** | Current day only (when the live API is reachable) | Historical, 2000–present (lags ~a few months) |
| **Price trends** | ✗ | ✅ `get_price_trend` over a date range |
| **Reliability** | data.gov.in is frequently down / WAF-blocked | Stable |
| **Tools** | 5 | 6 |
| **Best for** | Trying the tools instantly on sample data | Real analysis — trends and accurate prices |

> **TL;DR:** Want to see the server work with no live API? Use **`main`** (it ships with sample data). Want real, reliable commodity data and trends? Use **`feat/ceda-api-migration`**.

Switch with `git checkout main` or `git checkout feat/ceda-api-migration`.

---

## Setup

### Install (same for both branches)

```bash
git clone https://github.com/Krishna-Baldwa/agmarket-mcp.git
cd agmarknet-mcp

git checkout feat/ceda-api-migration   # or: git checkout main

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configure the API key

```bash
cp .env.example .env
```

**On `feat/ceda-api-migration` (CEDA):**
1. Get a free key from the [CEDA Data Portal](https://api.ceda.ashoka.edu.in).
2. Set `CEDA_API_KEY=<your key>` in `.env`. Done — the server uses real data.

**On `main` (data.gov.in):**
- Out of the box it serves a small **sample dataset** (no key needed) so you can see the tools respond.
- To switch to **real** data.gov.in data:
  1. Get a free key at [data.gov.in](https://data.gov.in) and set `DATA_GOV_IN_API_KEY=<your key>` in `.env`.
  2. In `src/agmarknet_mcp/server.py`, change the client to live mode:
     ```python
     api_client = AgmarknetClient(use_mock=False)   # was use_mock=True
     ```

### Connect to Claude Desktop

Add this to `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`; The easiest way to get to it is from inside the app rather than hunting through folders: open Claude Desktop → Settings → Developer tab → click Edit Config. That opens the file directly (and creates it if it doesn't exist yet).), using the env var for your branch:

```json
{
  "mcpServers": {
    "agmarknet": {
      "command": "/absolute/path/to/agmarknet-mcp/.venv/bin/python",
      "args": ["-m", "agmarknet_mcp.server"],
      "env": {
        "CEDA_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

*(On `main`, use `"DATA_GOV_IN_API_KEY"` instead — or omit `env` to run on sample data.)*

Restart Claude Desktop and ask:
- *"Compare tomato prices across mandis in Pune district."*
- *"What's the 60-day onion price trend in Maharashtra?"* *(CEDA branch)*

### Test without an LLM

```bash
npx @modelcontextprotocol/inspector python -m agmarknet_mcp.server
```

---

## Tools

### `feat/ceda-api-migration` (CEDA — real historical data)

| Tool | What it does |
|---|---|
| `get_commodity_price(commodity, state, district?, date?)` | Min/max/modal prices — latest available date, or a specific `YYYY-MM-DD`. |
| `compare_markets(commodity, state, district, top_n=10)` | Rank a district's mandis cheapest-first. |
| `get_price_summary(commodity, state, district?)` | Average / cheapest / dearest on the latest date. |
| `get_price_trend(commodity, state, district?, days=30)` | Daily-average price, window average, high/low, and % change over N days. |
| `list_commodities(search?)` | List tracked commodities, optionally filtered. |
| `list_markets(commodity, state, district)` | List the mandis reporting a commodity in a district. |

Tools accept **names**, not numeric ids (see [Design](#design-ceda-branch)). `state` is required; `district` narrows to individual mandis (omit for a state-wide aggregate).

### `main` (data.gov.in + sample fallback)

| Tool | What it does |
|---|---|
| `get_commodity_price(commodity, state?, district?, market?)` | Daily min/max/modal price for a commodity. |
| `compare_markets(commodity, state?, top_n=10)` | Rank markets cheapest-first. |
| `get_price_summary(commodity, state?)` | Average / cheapest / dearest across markets. |
| `list_commodities(search?)` | List commodities in the current dataset. |
| `list_markets(state?, commodity?)` | List reporting mandis. |

---

## Design (CEDA branch)

The CEDA API is **id-based**: commodities, states, districts, and markets are all numeric ids, and `/prices` returns ids, not names. LLMs and humans think in names, so the server's core job is translation:

- **Name → ID resolution.** Tools accept `"Tomato"`, `"Maharashtra"`, `"Pune"`; the client resolves them to ids (case-insensitive, unique-substring matching) before calling the API, and raises a clear error for unknown/ambiguous names so the model can self-correct.
- **ID → name enrichment.** Raw price rows (which carry only `market_id`) are translated back into readable records before reaching the model.
- **Cached reference data.** Commodities, geographies, and markets are fetched once and reused.
- **Tolerant validation.** `pydantic` validates every response. The API changes shape by granularity (state-level queries omit `district_id`/`market_id`), which the models handle explicitly.

### Module layout

- **`server.py`** — FastMCP server: defines the tools and handles the stdio/JSON-RPC lifecycle.
- **`api.py`** — the API client (`CedaClient` on CEDA; `AgmarknetClient` with sample fallback on `main`).
- **`models.py`** — `pydantic` models for the API's raw shapes and the domain objects the tools return.

---

## Data sources

- **`main`:** Directorate of Marketing & Inspection (DMI), Govt. of India, via [data.gov.in](https://data.gov.in).
- **CEDA branch:** [CEDA Agri Market Data](https://api.ceda.ashoka.edu.in), "Centre for Economic Data & Analysis, Ashoka University" — built on the same Agmarknet data, 2000–present. Free to download, display or include the data in other products for non-commercial purposes.

## License

[MIT](LICENSE)
