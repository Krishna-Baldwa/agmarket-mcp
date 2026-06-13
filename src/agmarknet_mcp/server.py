from typing import Optional, List, Tuple
# pyrefly: ignore [missing-import]
from mcp.server.fastmcp import FastMCP
from .api import CedaClient
from .models import PriceObservation

# 1. Initialize the FastMCP server.
# This automatically handles the MCP protocol, stdio transport, and JSON-RPC.
mcp = FastMCP("agmarknet-mcp")

# 2. Initialize our API client once, reused by every tool.
# (Reads CEDA_API_KEY from the environment / .env file.)
client = CedaClient()


def _latest_observations(
    observations: List[PriceObservation],
) -> Tuple[Optional[str], List[PriceObservation]]:
    """Reduce a multi-day result to just the most recent date present.

    CEDA data is historical and lags by months, so "the current price" really
    means "the price on the latest date we have data for". This finds that date
    and returns (date, rows_on_that_date).
    """
    if not observations:
        return None, []
    latest = max(o.date for o in observations)
    return latest, [o for o in observations if o.date == latest]


@mcp.tool()
def get_commodity_price(
    commodity: str,
    state: str,
    district: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Get wholesale prices (min/max/modal, Rs/quintal) for a commodity.

    `state` is required. Provide `district` for per-mandi prices, or omit it for
    a state-wide average. `date` is 'YYYY-MM-DD'; if omitted, the latest
    available date is used (the data is historical and updated periodically).
    """
    try:
        if date:
            obs = client.get_prices(commodity, state, district, from_date=date, to_date=date)
            day = date
        else:
            day, obs = _latest_observations(client.get_prices(commodity, state, district))
    except (ValueError, RuntimeError) as e:
        return f"Error: {e}"

    if not obs:
        scope = f"{commodity} in {state}" + (f", {district}" if district else "")
        return f"No price data found for {scope}."

    lines = [f"{commodity} prices in {state} on {day}:"]
    for o in obs:
        lines.append(
            f"- {o.market} ({o.district}): "
            f"modal Rs.{o.modal_price:.0f}/qtl (min {o.min_price:.0f}, max {o.max_price:.0f})"
        )
    return "\n".join(lines)


@mcp.tool()
def compare_markets(commodity: str, state: str, district: str, top_n: int = 10) -> str:
    """Compare a commodity's price across mandis to find the cheapest.

    Returns markets sorted cheapest-first by modal price, for the latest
    available date. `district` is required because per-mandi prices are only
    available at district granularity in the CEDA API.
    """
    try:
        day, rows = _latest_observations(client.get_prices(commodity, state, district))
    except (ValueError, RuntimeError) as e:
        return f"Error: {e}"

    if not rows:
        return f"No data found to compare for {commodity} in {district}, {state}."

    rows.sort(key=lambda o: o.modal_price)  # cheapest first
    lines = [f"Cheapest mandis for {commodity} in {district}, {state} (on {day}):"]
    for i, o in enumerate(rows[:top_n], 1):
        lines.append(f"{i}. Rs.{o.modal_price:.0f}/qtl - {o.market}")
    return "\n".join(lines)


@mcp.tool()
def get_price_summary(commodity: str, state: str, district: Optional[str] = None) -> str:
    """Get a statistical summary (avg / cheapest / dearest) of a commodity's
    price across reporting mandis, for the latest available date."""
    try:
        day, rows = _latest_observations(client.get_prices(commodity, state, district))
    except (ValueError, RuntimeError) as e:
        return f"Error: {e}"

    if not rows:
        scope = f"{commodity} in {state}" + (f", {district}" if district else "")
        return f"No data available to summarize for {scope}."

    modal_prices = [o.modal_price for o in rows]
    avg_price = sum(modal_prices) / len(modal_prices)
    cheapest = min(rows, key=lambda o: o.modal_price)
    dearest = max(rows, key=lambda o: o.modal_price)
    scope = f"{commodity} in {state}" + (f", {district}" if district else "")

    return (
        f"Summary for {scope} (on {day}):\n"
        f"Markets reporting: {len(rows)}\n"
        f"Average modal price: Rs.{avg_price:.0f}/quintal\n"
        f"Cheapest: Rs.{cheapest.modal_price:.0f}/qtl at {cheapest.market}\n"
        f"Dearest:  Rs.{dearest.modal_price:.0f}/qtl at {dearest.market}"
    )


@mcp.tool()
def list_commodities(search: Optional[str] = None) -> str:
    """List commodities tracked by Agmarknet, optionally filtered by a search term."""
    try:
        commodities = client.list_commodities()
    except (ValueError, RuntimeError) as e:
        return f"Error: {e}"

    names = sorted(c.commodity_name for c in commodities)
    if search:
        s = search.lower()
        names = [n for n in names if s in n.lower()]
    if not names:
        return "No commodities found matching your search."

    return f"Available commodities ({len(names)}):\n" + "\n".join(f"- {n}" for n in names)


@mcp.tool()
def list_markets(commodity: str, state: str, district: str) -> str:
    """List the mandis (markets) that report prices for a commodity in a district."""
    try:
        commodity_obj = client.resolve_commodity(commodity)
        state_id = client.resolve_state(state)
        district_id = client.resolve_district(district, state_id)
        markets = client.list_markets(commodity_obj.commodity_id, state_id, district_id)
    except (ValueError, RuntimeError) as e:
        return f"Error: {e}"

    if not markets:
        return f"No mandis found for {commodity} in {district}, {state}."

    names = sorted(m.market_name for m in markets)
    return (
        f"Mandis reporting {commodity} in {district}, {state} ({len(names)}):\n"
        + "\n".join(f"- {n}" for n in names)
    )


def main():
    """Entry point for the MCP server."""
    # Runs the server using standard input/output (stdio) transport.
    mcp.run()


if __name__ == "__main__":
    main()
