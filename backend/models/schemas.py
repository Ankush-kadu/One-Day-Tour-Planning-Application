from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, time

class UserPreference(BaseModel):
    type: str
    value: str

class Location(BaseModel):
    name: str
    address: str
    coordinates: tuple[float, float]

class ItineraryStop(BaseModel):
    location: Location
    start_time: time
    end_time: time
    activity_type: str
    cost: float
    status: str
    travel_time_to_next: Optional[int] = None
    travel_method_to_next: Optional[str] = None

class Itinerary(BaseModel):
    user_id: str
    date: datetime
    city: str
    start_time: time
    end_time: time
    budget: float
    stops: List[ItineraryStop]
    total_cost: float
    weather_forecast: Dict[str, str]
    news_alerts: List[str]