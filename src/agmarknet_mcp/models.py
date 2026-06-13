# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import Optional

# ---------------------------------------------------------------------------
# CEDA Agri Market API models
# ---------------------------------------------------------------------------
# The CEDA API is "ID-based": every commodity, state, district and market is
# referenced by a numeric id rather than a name. These models mirror the raw
# JSON each endpoint returns, so pydantic validates the shape for us before we
# start working with the data.


class Commodity(BaseModel):
    """One row from GET /agmarknet/commodities."""
    commodity_id: int
    commodity_name: str


class Geography(BaseModel):
    """One row from GET /agmarknet/geographies (a state+district pairing)."""
    census_state_id: int
    census_state_name: str
    census_district_id: int
    census_district_name: str


class Market(BaseModel):
    """One row from POST /agmarknet/markets (a mandi within a district)."""
    market_id: int
    market_name: str
    census_state_id: Optional[int] = None
    census_district_id: Optional[int] = None


class PriceRecord(BaseModel):
    """A raw price row exactly as POST /agmarknet/prices returns it.

    Note it carries *ids*, not names, and no variety field. The response shape
    depends on granularity: a state-level query returns aggregated rows that
    omit district_id/market_id, so both are optional.
    """
    date: str
    commodity_id: int
    census_state_id: int
    census_district_id: Optional[int] = None
    market_id: Optional[int] = None
    min_price: float
    max_price: float
    modal_price: float


class PriceObservation(BaseModel):
    """A price row enriched with human-readable names.

    This is the "domain" object our MCP tools actually speak — we translate the
    id-based PriceRecord into this before returning it, so callers never deal
    with raw numeric ids.
    """
    date: str
    commodity: str
    state: str
    district: str
    market: str
    min_price: float
    max_price: float
    modal_price: float
