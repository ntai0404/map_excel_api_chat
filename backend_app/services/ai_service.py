import os
import json
import logging
import re
from openai import OpenAI
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Logger configuration
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# --- CONFIGURATION ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL_NAME = os.getenv("NVIDIA_MODEL_NAME", "deepseek-ai/deepseek-r1")

# Cache for AI standardization
AI_ADDR_CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'ai_address_cache.json')

def load_ai_cache():
    if os.path.exists(AI_ADDR_CACHE_FILE):
        try:
            with open(AI_ADDR_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_ai_cache(cache):
    try:
        with open(AI_ADDR_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

# Initialize Client
client = None

def log_ai_usage(response, model_name="unknown"):
    """
    Logs token usage from AI response.
    """
    try:
        usage = getattr(response, 'usage', None)
        if usage:
            prompt = getattr(usage, 'prompt_tokens', 0)
            completion = getattr(usage, 'completion_tokens', 0)
            total = getattr(usage, 'total_tokens', 0)
            logger.info(f"📊 [AI-QUOTA-CHECK] Model: {model_name} | Prompt: {prompt} | Completion: {completion} | TOTAL: {total}")
        else:
            logger.warning(f"⚠️ [AI-QUOTA-CHECK] No usage data returned for model {model_name}.")
    except Exception as e:
        logger.error(f"Error logging AI usage: {e}")

def extract_json(content: str) -> Dict[str, Any]:
    """
    Extracts JSON from text, handling markdown blocks.
    """
    if not content:
        return {}
    
    # Try direct parse
    try:
        return json.loads(content)
    except Exception:
        pass
        
    # Try cleaning markdown blocks
    try:
        match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception:
        pass
        
    logger.warning(f"Failed to extract JSON from AI content: {content[:100]}...")
    return {}

def configure_genai():
    """Confirms NVIDIA Client is ready."""
    global client
    if not NVIDIA_API_KEY:
        logger.error("NVIDIA_API_KEY not found in .env")
        return False
    
    try:
        # NVIDIA API is OpenAI-compatible
        client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
        logger.info(f"NVIDIA AI Configured Successfully (Model: {NVIDIA_MODEL_NAME}).")
        return True
    except Exception as e:
        logger.error(f"Failed to configure NVIDIA AI: {e}")
        return False

async def get_ai_response(user_msg: str, context: List[Any], intent: Dict[str, Any], type: str = "chat") -> str:
    """
    Generates a response using DeepSeek Chat (V3).
    """
    if not client:
        configure_genai()
        if not client:
            return "Hệ thống AI đang bảo trì (Missing Key)."

    try:
        # Construct System Prompt based on context
        system_prompt = f"""Bạn là trợ lý ảo mua sắm thông minh của hệ thống 'Beenet.vn' - Nền tảng mua sắm theo vị trí hàng đầu.
        Phong cách: Thân thiện, nhiệt tình, chuyên nghiệp và luôn sử dụng emoji 🐝✨ để tạo cảm giác gần gũi.
        Nhiệm vụ: Tư vấn sản phẩm, gợi ý cửa hàng gần nhất giúp khách hàng mua sắm tiện lợi nhất.
        
        Thông tin khách hàng đang xem:
        {json.dumps(context, ensure_ascii=False, indent=2)}

        Yêu cầu trả lời:
        - Ngắn gọn, thân thiện, dùng emoji.
        - Nếu có sản phẩm phù hợp, hãy mời khách chốt đơn.
        - Nếu không có, gợi ý sản phẩm tương tự.
        """

        response = client.chat.completions.create(
            model=NVIDIA_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7,
            max_tokens=1024, # Increased for DeepSeek-R1
            stream=False
        )
        
        # Log usage
        log_ai_usage(response, NVIDIA_MODEL_NAME)
        
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"DeepSeek Chat Error: {e}")
        return "Xin lỗi, em đang bị quá tải. Anh chị chờ chút nhé!"

async def extract_search_intent(query: str, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Extracts search filters (product name, price, location) using DeepSeek.
    Returns JSON.
    """
    if not client:
        configure_genai()
        if not client: return {}

    try:
        # Include categories in prompt if available to improve accuracy
        cat_str = ", ".join(categories) if categories else "Electronics, General"
        
        prompt = f"""
        Phân tích câu tìm kiếm của khách hàng và trích xuất thông tin JSON.
        
        Query: "{query}"
        Danh mục hợp lệ (ưu tiên khớp chính xác): {cat_str}
        
        Nhiệm vụ:
        1. Nếu khách tìm Loại sản phẩm chung chung (VD: "mua máy tính", "đồ gia dụng") -> Cố gắng khớp với "Danh mục hợp lệ" ở trên và điền vào trường "category".
        2. Nếu khách tìm Tên sản phẩm cụ thể (VD: "Macbook Air M1", "Nồi cơm Sharp") -> Điền vào trường "product".
        
        Quy tắc Boolean (Quan Trọng):
        - Nếu tìm thấy "category" HOẶC "product" -> is_general_inquiry = false.
        - Chỉ khi khách chào hỏi xã giao (hi, hello) hoặc hỏi về chính sách/giờ làm việc -> is_general_inquiry = true.
        - "is_location_request" = true chỉ khi có từ khóa địa điểm ("ở đâu", "gần đây", "tại Hà Nội").

        Output Format (JSON strict):
        {{
            "category": "Tên danh mục chính xác",
            "product": "Tên sản phẩm cụ thể",
            "keyword": "từ khóa tìm kiếm",
            "max_price": 0,
            "location": "",
            "is_location_request": boolean,
            "is_general_inquiry": boolean
        }}
        """

        response = client.chat.completions.create(
            model=NVIDIA_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a JSON extractor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Log content for debugging
        content = response.choices[0].message.content
        logger.info(f"🔍 [AI-INTENT-RAW]: {content}")
        
        # Log usage
        log_ai_usage(response, NVIDIA_MODEL_NAME)
        
        return extract_json(content)
    except Exception as e:
        logger.error(f"Intent Extraction Error: {e}")
        return {}

async def smart_product_filter(query: str, products: List[Any]) -> Dict[str, Any]:
    """
    Optional: Advanced filtering using LLM.
    Returns: {"found": bool, "products": list, "reasoning": str}
    """
    # For now, simplistic pass-through to ensure speed.
    # We can add DeepSeek filtering here later if needed.
    return {
        "found": True,
        "products": products,
        "reasoning": "Pass-through (Optimized)",
        "ai_message_template": "Dạ có {{product_name}} tại {{shop_name}} ạ."
    }

async def standardize_address_ai(ward: str, district: str, city: str) -> str:
    """
    Standardizes address components using DeepSeek AI.
    Uses local cache to minimize API calls.
    """
    cache = load_ai_cache()
    raw_key = f"{ward}|{district}|{city}"
    
    if raw_key in cache:
        return cache[raw_key]
    
    global client
    if not client:
        configure_genai()
    
    if not client:
        return f"{ward}, {district}, {city}"
        
    prompt = f"""Bạn là chuyên gia về địa lý Việt Nam. 
    Hãy chuẩn hóa địa chỉ sau thành định dạng chuẩn nhất để bản đồ có thể xác định được tọa độ.
    Dữ liệu thô: {ward}, {district}, {city}

    Quy tắc:
    1. Giữ nguyên cấp hành chính: Nếu là "Thị trấn" thì ghi "Thị trấn", không được tự ý đổi thành "Xã".
    2. Giải mã viết tắt: "Q." -> "Quận", "P." -> "Phường", "TP." -> "Thành phố", "TP.HCM" -> "Thành phố Hồ Chí Minh".
    3. Định dạng trả về: "Tên Phường/Xã/Thị trấn, Tên Quận/Huyện/Thị xã/Thành phố thuộc tỉnh, Tên Tỉnh/Thành phố trực thuộc trung ương".
    4. Chỉ trả về 1 dòng địa chỉ duy nhất, không giải thích gì thêm.
    """
    
    try:
        response = client.chat.completions.create(
            model=NVIDIA_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        # Log usage
        log_ai_usage(response, NVIDIA_MODEL_NAME)
        
        clean_addr = response.choices[0].message.content.strip()
        cache[raw_key] = clean_addr
        save_ai_cache(cache)
        return clean_addr
    except Exception as e:
        logger.error(f"AI Address Standarization Error: {e}")
        return f"{ward}, {district}, {city}"
