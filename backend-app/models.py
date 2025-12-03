from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    latitude: float
    longitude: float

class StoreInfo(BaseModel):
    name: str
    address: str
    lat: float
    lng: float
    distance_km: float

class ChatResponse(BaseModel):
    reply: str
    nearest_stores: list[StoreInfo] = []
    trigger_location: bool = False
