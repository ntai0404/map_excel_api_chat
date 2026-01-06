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
    staff_zalo: str | None = None

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

class LeadRequest(BaseModel):
    user_name: str | None = "Khách"
    user_id: str | None = None
    product_name: str
    shop_name: str | None = None
    chat_context: str
    zalo_contact: str = "" # Now used for Phone Number
    avatar_url: str = "" # New field
    phone: str = "" # Explicit field (map to zalo_contact logic)
    zalo_group_link: str = "" # New field for precise tracking
    timestamp: str = ""
