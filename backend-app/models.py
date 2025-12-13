from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    latitude: float
    longitude: float

class ProductInfo(BaseModel):
    name: str
    price: str
    image_url: str = ""
    link: str = ""

class StoreInfo(BaseModel):
    name: str
    address: str
    lat: float
    lng: float
    distance_km: float
    zalo_group_link: str | None = None
    products: list[ProductInfo] = []

class ChatResponse(BaseModel):
    reply: str
    nearest_stores: list[StoreInfo] = []
    trigger_location: bool = False
