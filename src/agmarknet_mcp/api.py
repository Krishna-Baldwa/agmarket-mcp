# pyrefly: ignore [missing-import]
import httpx
import os
from datetime import date, timedelta
from typing import List, Dict, Optional, Callable
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from .models import Commodity, Geography, Market, PriceRecord, PriceObservation

# Load variables from a local .env file (e.g. CEDA_API_KEY) into the
# environment as soon as this module is imported, so os.getenv() can find them.
load_dotenv()


class CedaClient:
    """Client for the CEDA (Ashoka University) Agri Market API.

    The API is *id-based*: you query with numeric ids (commodity_id, state_id,
    district_id, market_id), not names. Humans and LLMs think in names, so this
    client adds a *resolution layer* that:
      1. turns names into ids before calling the API, and
      2. turns the id-based price rows back into name-based records on the way out.
    """

    BASE_URL = "https://api.ceda.ashoka.edu.in/v1"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        # The key comes from the CEDA_API_KEY env var (loaded from .env above)
        # unless one is passed in explicitly.
        self.api_key = api_key or os.getenv("CEDA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "CEDA_API_KEY is not set. Add it to your .env file. "
                "Get a free key at https://api.ceda.ashoka.edu.in"
            )
        # A single reusable HTTP client. Setting the Authorization header here
        # means every request automatically carries the Bearer token, and
        # connections are pooled/reused across calls.
        self._http = httpx.Client(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=timeout,
        )
        # Reference data (commodities, geographies, markets) rarely changes, so
        # we fetch each once and cache it for the lifetime of the client.
        self._commodities: Optional[List[Commodity]] = None
        self._geographies: Optional[List[Geography]] = None
        self._market_cache: Dict[tuple, List[Market]] = {}

    # -- low-level helper ---------------------------------------------------

    def _unwrap(self, response: httpx.Response) -> list:
        """Validate the HTTP response and return its `output.data` payload.

        Every CEDA endpoint wraps results in the same envelope:
            {"output": {"type": "success", "message": "...", "data": [...]}}
        so we check the status code, confirm success, and hand back `data`.
        """
        response.raise_for_status()  # raise on any 4xx/5xx (e.g. 401 bad key)
        output = response.json().get("output", {})
        if output.get("type") != "success":
            raise RuntimeError(
                f"CEDA API error: {output.get('message', 'unknown error')}"
            )
        return output.get("data", [])

    # -- reference data (fetched once, then cached) -------------------------

    def list_commodities(self) -> List[Commodity]:
        """All commodities the platform tracks (id + name)."""
        if self._commodities is None:
            data = self._unwrap(self._http.get("/agmarknet/commodities"))
            self._commodities = [Commodity(**c) for c in data]
        return self._commodities

    def list_geographies(self) -> List[Geography]:
        """All state+district pairings (ids + names)."""
        if self._geographies is None:
            data = self._unwrap(self._http.get("/agmarknet/geographies"))
            self._geographies = [Geography(**g) for g in data]
        return self._geographies

    def list_markets(
        self, commodity_id: int, state_id: int, district_id: int,
        indicator: str = "price",
    ) -> List[Market]:
        """Markets (mandis) reporting a commodity in one district, cached per query."""
        key = (commodity_id, state_id, district_id, indicator)
        if key not in self._market_cache:
            data = self._unwrap(self._http.post("/agmarknet/markets", json={
                "commodity_id": commodity_id,
                "state_id": state_id,
                "district_id": district_id,
                "indicator": indicator,
            }))
            self._market_cache[key] = [Market(**m) for m in data]
        return self._market_cache[key]

    # -- name -> id resolution ----------------------------------------------

    def resolve_commodity(self, name: str) -> Commodity:
        return self._match(
            self.list_commodities(), name, lambda c: c.commodity_name, "commodity"
        )

    def resolve_state(self, name: str) -> int:
        match = self._match(
            self.list_geographies(), name, lambda g: g.census_state_name, "state"
        )
        return match.census_state_id

    def resolve_district(self, name: str, state_id: int) -> int:
        # Only consider districts within the already-resolved state, so that a
        # district name that exists in several states isn't ambiguous.
        in_state = [g for g in self.list_geographies() if g.census_state_id == state_id]
        match = self._match(in_state, name, lambda g: g.census_district_name, "district")
        return match.census_district_id

    @staticmethod
    def _match(items: list, name: str, key_fn: Callable, kind: str):
        """Case-insensitive name lookup: exact match wins, else a *unique*
        substring match. Anything ambiguous or missing raises a clear error
        (which the MCP tool surfaces to the LLM so it can correct itself)."""
        name_l = name.strip().lower()
        exact = [it for it in items if key_fn(it).lower() == name_l]
        if exact:
            return exact[0]
        partial = [it for it in items if name_l in key_fn(it).lower()]
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            sample = ", ".join(sorted({key_fn(it) for it in partial})[:6])
            raise ValueError(f"Ambiguous {kind} '{name}'. Did you mean: {sample}?")
        raise ValueError(f"Unknown {kind} '{name}'.")

    # -- high-level: prices, with names instead of ids ----------------------

    def get_prices(
        self, commodity: str, state: str, district: Optional[str] = None,
        from_date: Optional[str] = None, to_date: Optional[str] = None,
        default_lookback_days: int = 365,
    ) -> List[PriceObservation]:
        """Fetch daily prices for a commodity, returned as name-enriched records.

        Dates are 'YYYY-MM-DD' strings. If omitted, defaults to the trailing
        `default_lookback_days` (CEDA data is historical and lags by months, so
        callers typically pick the latest date present in the result).
        `state` is required by the API; `district` is optional (omit it for a
        state-wide aggregated series).
        """
        # 1. Default the date window to the trailing lookback period.
        if to_date is None:
            to_date = date.today().isoformat()
        if from_date is None:
            from_date = (date.today() - timedelta(days=default_lookback_days)).isoformat()

        # 2. Resolve the names the caller gave us into the ids the API needs.
        commodity_obj = self.resolve_commodity(commodity)
        state_id = self.resolve_state(state)
        body: Dict = {
            "commodity_id": commodity_obj.commodity_id,
            "state_id": state_id,
            "from_date": from_date,
            "to_date": to_date,
        }
        if district:
            body["district_id"] = [self.resolve_district(district, state_id)]

        # 3. Call the API and validate every row against PriceRecord.
        rows = [PriceRecord(**r)
                for r in self._unwrap(self._http.post("/agmarknet/prices", json=body))]
        if not rows:
            return []

        # 4. Build id -> name lookup maps so we can translate ids back to names.
        district_name = {
            g.census_district_id: g.census_district_name for g in self.list_geographies()
        }
        state_name = {
            g.census_state_id: g.census_state_name for g in self.list_geographies()
        }
        # The /prices response gives market_id but not market_name, so we fetch
        # markets once per district that actually appears in the results (this
        # is self-limiting: 1 call if a district was specified, a handful for a
        # state-wide query) and the cache prevents repeat lookups. State-level
        # aggregate rows have no district/market, so we skip those here.
        market_name: Dict[int, str] = {}
        for dist_id in {r.census_district_id for r in rows if r.census_district_id}:
            for m in self.list_markets(commodity_obj.commodity_id, state_id, dist_id):
                market_name[m.market_id] = m.market_name

        # 5. Enrich each raw id-based row into a named observation. When a field
        # is absent (state-level aggregate), fall back to a descriptive label.
        return [
            PriceObservation(
                date=r.date[:10],  # trim the ISO timestamp down to YYYY-MM-DD
                commodity=commodity_obj.commodity_name,
                state=state_name.get(r.census_state_id, str(r.census_state_id)),
                district=(district_name.get(r.census_district_id, str(r.census_district_id))
                          if r.census_district_id else "(all districts)"),
                market=(market_name.get(r.market_id, f"Market #{r.market_id}")
                        if r.market_id else "(state average)"),
                min_price=r.min_price,
                max_price=r.max_price,
                modal_price=r.modal_price,
            )
            for r in rows
        ]
