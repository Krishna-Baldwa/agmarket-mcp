from typing import Optional
from mcp.server.fastmcp import FastMCP
from .api import AgmarknetClient

# 1. Initialize the FastMCP server
# This automatically handles the MCP protocol, stdio transport, and JSON-RPC
mcp = FastMCP("agmarknet-mcp")

# Initialize our API client (using mock data by default since the govt API is blocked)
api_client = AgmarknetClient(use_mock=True)

@mcp.tool()
def get_commodity_price(
    commodity: str,
    state: Optional[str] = None,
    district: Optional[str] = None,
    market: Optional[str] = None,
) -> str:
    """Get current daily wholesale prices for a specific commodity.
    
    Returns min, max, and modal prices from today's Agmarknet data.
    """
    filters = {"commodity": commodity}
    if state: filters["state"] = state
    if district: filters["district"] = district
    if market: filters["market"] = market
        
    prices = api_client.fetch_prices(filters=filters)
    
    if not prices:
        return f"No price data found for {commodity} with the given filters."
        
    result = [f"Prices for {commodity}:"]
    for p in prices:
        result.append(
            f"- {p.state}, {p.district}, {p.market} | "
            f"Variety: {p.variety} | "
            f"Modal Price: ₹{p.modal_price}/quintal (Min: ₹{p.min_price}, Max: ₹{p.max_price})"
        )
    
    return "\n".join(result)

@mcp.tool()
def compare_markets(commodity: str, state: Optional[str] = None, top_n: int = 10) -> str:
    """Compare prices of a commodity across different markets.
    
    Returns markets sorted by modal price (cheapest first).
    Great for finding the cheapest mandi.
    """
    filters = {"commodity": commodity}
    if state: filters["state"] = state
        
    prices = api_client.fetch_prices(filters=filters)
    
    if not prices:
        return f"No data found to compare for {commodity}."
        
    # Sort prices by modal_price ascending (cheapest first)
    sorted_prices = sorted(prices, key=lambda x: x.modal_price)
    
    result = [f"Top {top_n} cheapest markets for {commodity}:"]
    for i, p in enumerate(sorted_prices[:top_n], 1):
        result.append(f"{i}. ₹{p.modal_price}/qtl - {p.market} ({p.district}, {p.state})")
        
    return "\n".join(result)

@mcp.tool()
def get_price_summary(commodity: str, state: Optional[str] = None) -> str:
    """Get a statistical summary of a commodity's price across all markets.
    
    Returns average, lowest, and highest prices across matching markets.
    """
    filters = {"commodity": commodity}
    if state: filters["state"] = state
        
    prices = api_client.fetch_prices(filters=filters)
    
    if not prices:
        return f"No data available to summarize for {commodity}."
        
    modal_prices = [p.modal_price for p in prices]
    avg_price = sum(modal_prices) / len(modal_prices)
    
    cheapest = min(prices, key=lambda x: x.modal_price)
    expensive = max(prices, key=lambda x: x.modal_price)
    
    return (
        f"Summary for {commodity}:\n"
        f"Total Markets Reporting: {len(prices)}\n"
        f"Average Modal Price: ₹{avg_price:.2f}/quintal\n"
        f"Cheapest Market: ₹{cheapest.modal_price}/qtl at {cheapest.market} ({cheapest.state})\n"
        f"Most Expensive Market: ₹{expensive.modal_price}/qtl at {expensive.market} ({expensive.state})"
    )

@mcp.tool()
def list_commodities(search: Optional[str] = None) -> str:
    """List available commodities in today's Agmarknet data."""
    prices = api_client.fetch_prices()
    
    # Extract unique commodities
    commodities = set(p.commodity for p in prices)
    
    if search:
        search_lower = search.lower()
        commodities = {c for c in commodities if search_lower in c.lower()}
        
    if not commodities:
        return "No commodities found matching your search."
        
    sorted_comms = sorted(list(commodities))
    return "Available Commodities:\n" + "\n".join(f"- {c}" for c in sorted_comms)

@mcp.tool()
def list_markets(state: Optional[str] = None, commodity: Optional[str] = None) -> str:
    """List available markets (mandis) in today's Agmarknet data."""
    filters = {}
    if state: filters["state"] = state
    if commodity: filters["commodity"] = commodity
        
    prices = api_client.fetch_prices(filters=filters)
    
    # Extract unique markets
    markets = set(f"{p.market} ({p.district}, {p.state})" for p in prices)
    
    if not markets:
        return "No markets found with those filters."
        
    sorted_markets = sorted(list(markets))
    return f"Available Markets (Total: {len(markets)}):\n" + "\n".join(f"- {m}" for m in sorted_markets)

def main():
    """Entry point for the MCP server."""
    # Runs the server using standard input/output (stdio)
    mcp.run()

if __name__ == "__main__":
    main()
