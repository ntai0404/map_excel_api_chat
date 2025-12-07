import google.generativeai as genai
import os
import requests
import json
from dotenv import load_dotenv

# Load dotenv (still good to have for standalone testing)
load_dotenv()

# Global variable to hold the model, initialized lazily
_model = None

def get_config():
    """Lazy load configuration from environment variables."""
    return {
        "AI_API_KEY": os.environ.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY"),
        "AI_MODEL_NAME": os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        "AI_API_BASE": os.environ.get("AI_API_BASE")
    }

def get_model():
    """Get or initialize the Gemini model."""
    global _model
    config = get_config()
    
    # If using Custom API (Ollama), we don't need a Gemini model object
    if config["AI_API_BASE"]:
        return None
        
    if _model:
        return _model
        
    api_key = config["AI_API_KEY"]
    if not api_key:
        print("WARNING: AI_API_KEY not found. Gemini API calls will likely fail.")
        return None
        
    try:
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(config["AI_MODEL_NAME"])
        print(f"Configured Gemini Provider with model: {config['AI_MODEL_NAME']}")
        return _model
    except Exception as e:
        print(f"Error configuring Gemini: {e}")
        return None

def configure_genai():
    # Trigger model initialization
    get_model()

# --- Helper: Call Custom API (e.g., Ollama) ---
def call_custom_api(prompt, system_instruction=None, json_mode=False):
    config = get_config()
    url = config["AI_API_BASE"]
    model_name = config["AI_MODEL_NAME"]
    
    # Simple heuristic for Ollama URL adjustment
    if "ollama" in str(url).lower() or "localhost" in str(url).lower():
        if not url.endswith("/api/generate") and not url.endswith("/v1/chat/completions"):
             url = f"{url.rstrip('/')}/api/generate"

    full_prompt = prompt
    if system_instruction:
        full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"

    payload = {
        "model": model_name,
        "prompt": full_prompt,
        "stream": False,
        "format": "json" if json_mode else None
    }
    
    try:
        # print(f"DEBUG: POSTing to {url} with model {model_name}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Error calling Custom API: {e}")
        raise e

# --- Main Service Functions ---

async def get_ai_response(user_message: str, stores_info: list[dict] | None, search_intent: dict | None = None, match_type: str | None = None):
    system_instruction = "Bạn là trợ lý ảo bán hàng. Nhiệm vụ của bạn là trả lời câu hỏi của khách hàng một cách thân thiện và mời họ đến cửa hàng gần nhất nếu có thông tin."
    
    prompt = f"{system_instruction}\n\n"

    if stores_info:
        context = "Thông tin các cửa hàng gần nhất:\n"
        for i, store in enumerate(stores_info):
            context += (
                f"Cửa hàng {i+1}:\n"
                f"- Tên: {store['store_name']}\n"
                f"- Khoảng cách: {store['distance_km']:.2f} km\n"
                f"- Sản phẩm: {store['product_info']}\n"
                f"- Khuyến mãi: {store['promotion']}\n"
                f"- Địa chỉ: {store['address']}\n\n"
            )
        prompt += f"Context: {context}\n\nUser Query: {user_message}.\n\n"
        
        if match_type == 'product':
            prompt += "Chỉ dẫn:\n1. Người dùng tìm đúng sản phẩm có trong Context. Hãy báo tin vui và mời họ đến.\n2. Tóm tắt khuyến mãi hấp dẫn nhất."
        elif match_type == 'category':
            product_name = search_intent.get('product')
            category_name = search_intent.get('category') if search_intent else 'danh mục này'
            
            if product_name:
                prompt += f"Chỉ dẫn:\n1. Người dùng tìm '{product_name}' nhưng hiện tại KHÔNG có cửa hàng nào gần đây bán chính xác sản phẩm đó.\n2. Hệ thống tìm thấy các cửa hàng thuộc nhóm '{category_name}' để thay thế.\n3. Hãy nói rõ: 'Tiếc là mình không thấy cửa hàng nào có sẵn {product_name} ở gần bạn. Tuy nhiên, mình tìm thấy các cửa hàng {category_name} này có thể phù hợp...'.\n4. Giới thiệu ngắn gọn."
            else:
                prompt += f"Chỉ dẫn:\n1. Người dùng đang tìm kiếm chung về '{category_name}' (hoặc các sản phẩm thuộc nhóm này).\n2. Hãy nói: 'Mình tìm thấy các cửa hàng {category_name} này phù hợp với nhu cầu của bạn...'.\n3. Giới thiệu ngắn gọn."

    elif search_intent and search_intent.get('is_location_request'):
        prompt += f"User Query: {user_message}.\n\nChỉ dẫn:\nNgười dùng đang hỏi về vị trí. Hãy trả lời ngắn gọn: '...' (Frontend sẽ tự động xử lý phần còn lại)."

    elif search_intent:
        product_name = search_intent.get('product') or search_intent.get('category')
        prompt += f"User Query: {user_message}.\n\nChỉ dẫn:\nNgười dùng muốn tìm '{product_name}' nhưng hiện tại không tìm thấy cửa hàng nào phù hợp trong hệ thống. Hãy xin lỗi khách hàng một cách khéo léo và hỏi họ muốn tìm sản phẩm khác không."
    else:
        prompt += f"User Query: {user_message}.\n\nChỉ dẫn:\nĐây là hội thoại xã giao hoặc câu hỏi chưa rõ ý định.\n1. Tự xưng là 'Trợ lý ảo'.\n2. Nếu người dùng nói muốn mua đồ chung chung, hãy hỏi thẳng: 'Bạn đang tìm kiếm sản phẩm nào cụ thể ạ? (Ví dụ: Điện thoại, Quần áo, Laptop...)' (KHÔNG cần chào 'Chào bạn' ở đầu).\n3. CHỈ chào hỏi ('Chào bạn!...') NẾU người dùng có lời chào trước (như 'hi', 'xin chào').\n4. TUYỆT ĐỐI KHÔNG dùng các từ trong ngoặc vuông như '[...]'."

    try:
        config = get_config()
        
        # Case 1: Custom API (e.g. Ollama)
        if config["AI_API_BASE"]:
            return call_custom_api(prompt)
        
        # Case 2: Standard Gemini
        model = get_model()
        if not model:
            return "Lỗi cấu hình: Gemini chưa được khởi tạo (thiếu API Key?)."
        
        print(f"DEBUG: Sending prompt to Gemini ({config['AI_MODEL_NAME']})...")
        response = model.generate_content(prompt)
        return response.text
            
    except Exception as e:
        print(f"CRITICAL ERROR in get_ai_response: {e}")
        import traceback
        traceback.print_exc()
        return "Xin lỗi, tôi đang gặp vấn đề. Vui lòng thử lại sau."

async def extract_search_intent(user_message: str, valid_categories: list[str] | None = None) -> dict | None:
    if not valid_categories:
        valid_categories = ["Công nghệ", "Thời trang", "Ẩm thực"]

    # --- Hard Rules (Regex) ---
    import re
    user_msg_lower = user_message.lower()
    location_keywords = ["vị trí", "tọa độ", "định vị", "ở đâu", "location", "gps"]
    
    if len(user_msg_lower.split()) <= 3 and any(k in user_msg_lower for k in location_keywords):
        print("DEBUG: Detected Location Request via Regex (Short Command)")
        return {"product": None, "generic_term": None, "category": None, "is_location_request": True}
        
    if any(k in user_msg_lower for k in location_keywords) and any(p in user_msg_lower for p in ["tôi", "mình", "user", "hiện tại", "của tớ"]):
        print("DEBUG: Detected Location Request via Regex (Keyword Combination)")
        return {"product": None, "generic_term": None, "category": None, "is_location_request": True}

    generic_keywords = ["mua đồ", "sắm đồ", "mua sắm", "shopping", "mua gì đó"]
    if any(k in user_msg_lower for k in generic_keywords) and len(user_msg_lower.split()) <= 6:
        print("DEBUG: Detected Generic Query (Hardcoded Check) -> Force Return None")
        return None
    # --------------------------

    system_instruction = f"""Bạn là công cụ trích xuất ý định.
Nhiệm vụ: Trích xuất 'product', 'generic_term', 'category' và 'is_location_request'.
Output format: JSON ONLY.
Rules:
1. ƯU TIÊN TUYỆT ĐỐI: Nếu câu hỏi có chứa từ khóa "vị trí", "ở đâu", "tọa độ", "định vị" VÀ ám chỉ người dùng (tôi, mình, user) -> set "is_location_request": true.
2. Nếu tìm sản phẩm:
   - "product": Tên cụ thể (iPhone 16).
   - "generic_term": Từ khóa chung nhất (iPhone, Laptop, Giày).
   - "category": Chọn từ danh sách {valid_categories}.
3. TRƯỜNG HỢP NGOẠI LỆ:
   - Mua đồ chung chung -> Return tất cả null.

Ví dụ:
- "Mua iPhone 16" -> {{"product": "iPhone 16", "generic_term": "iPhone", "category": "Công nghệ", "is_location_request": false}}
"""
    
    prompt = f"{system_instruction}\n\nUser Message: {user_message}"

    try:
        content = ""
        config = get_config()
        
        if config["AI_API_BASE"]:
            content = call_custom_api(prompt, json_mode=True)
        else:
            model = get_model()
            if not model:
                return None
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    response_mime_type="application/json"
                )
            )
            content = response.text.strip()

        print(f"DEBUG: Intent JSON: {content}")
        data = json.loads(content)
        
        if not data.get('product') and not data.get('category') and not data.get('is_location_request'):
            return None
            
        return data
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return None
