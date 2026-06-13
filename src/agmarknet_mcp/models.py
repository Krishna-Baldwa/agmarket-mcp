# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import List, Optional

class CommodityPrice(BaseModel):
    """
    Represents a single commodity price record from Agmarknet.
    """
    state: str
    district: str
    market: str
    commodity: str
    variety: str
    arrival_date: str
    min_price: float = Field(alias="min_price")
    max_price: float = Field(alias="max_price")
    modal_price: float = Field(alias="modal_price")

class ApiResponse(BaseModel):
    """
    Represents the top-level response envelope from data.gov.in.
    """
    index_name: str
    title: str
    desc: str
    created: int
    updated: int
    created_date: str
    updated_date: str
    active: str
    visualizable: str
    catalog_uuid: str
    source: str
    org_type: str
    org: list[str]
    sector: list[str]
    field: list[dict]
    target_bucket: dict
    message: str
    version: str
    status: str
    total: int
    count: int
    limit: str
    offset: str
    records: List[CommodityPrice]


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

    Note it carries *ids*, not names, and no variety field.
    """
    date: str
    commodity_id: int
    census_state_id: int
    census_district_id: int
    market_id: int
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
