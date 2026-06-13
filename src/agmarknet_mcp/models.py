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
