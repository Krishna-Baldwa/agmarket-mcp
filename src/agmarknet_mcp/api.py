# pyrefly: ignore [missing-import]
import httpx
import os
from typing import List, Dict, Optional
from .models import CommodityPrice, ApiResponse

# Mock data to use while data.gov.in is unresponsive
MOCK_DATA = [
    {
        "state": "Maharashtra",
        "district": "Pune",
        "market": "Pune",
        "commodity": "Tomato",
        "variety": "Local",
        "arrival_date": "13/06/2026",
        "min_price": 2000.0,
        "max_price": 3000.0,
        "modal_price": 2500.0
    },
    {
        "state": "Maharashtra",
        "district": "Nashik",
        "market": "Lasalgaon",
        "commodity": "Onion",
        "variety": "Red",
        "arrival_date": "13/06/2026",
        "min_price": 1500.0,
        "max_price": 2000.0,
        "modal_price": 1800.0
    },
    {
        "state": "Gujarat",
        "district": "Surat",
        "market": "Surat",
        "commodity": "Tomato",
        "variety": "Local",
        "arrival_date": "13/06/2026",
        "min_price": 1800.0,
        "max_price": 2800.0,
        "modal_price": 2200.0
    }
]

class AgmarknetClient:
    """Client for the data.gov.in Agmarknet API."""
    
    # This is the specific Resource ID for the daily commodity prices dataset on data.gov.in
    BASE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    
    def __init__(self, api_key: str = None, use_mock: bool = True):
        """
        Initialize the client. By default, it uses Mock data since the API goes down often.
        """
        self.api_key = api_key or os.getenv("DATA_GOV_IN_API_KEY")
        self.use_mock = use_mock
        
    def fetch_prices(self, limit: int = 100, filters: Optional[Dict[str, str]] = None) -> List[CommodityPrice]:
        """Fetch commodity prices from the API or return mock data."""
        
        # 1. Mock Path (when API is down or in testing)
        if self.use_mock:
            results = MOCK_DATA
            
            # Apply filters manually to mock data
            if filters:
                for key, value in filters.items():
                    results = [r for r in results if r.get(key, "").lower() == value.lower()]
                    
            return [CommodityPrice(**r) for r in results]

        # 2. Real API Path
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError("API key is required to use the real data.gov.in API.")

        # Construct the query parameters
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit
        }
        
        # Add dynamic filters (e.g. state="Maharashtra")
        if filters:
            for key, value in filters.items():
                params[f"filters[{key}]"] = value
                
        try:
            # Using httpx to make a synchronous GET request
            response = httpx.get(self.BASE_URL, params=params, timeout=10.0)
            
            # Raise exception for bad status codes (like 404 Not Found, 500 Server Error)
            response.raise_for_status() 
            
            data = response.json()
            
            # Validate the JSON data against our Pydantic model
            api_response = ApiResponse(**data)
            return api_response.records
            
        except httpx.RequestError as e:
            print(f"Network error while calling data.gov.in: {e}")
            return []
        except Exception as e:
            print(f"Error parsing API response: {e}")
            return []
