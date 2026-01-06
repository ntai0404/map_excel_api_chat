import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Logger configuration
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Initialize Client
client = None

def configure_genai():
    """Confirms DeepSeek Client is ready."""
    global client
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY not found in .env")
        return False
    
    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        logger.info("DeepSeek AI Configured Successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to configure DeepSeek: {e}")
        return False

async def get_ai_response(user_msg: str, context: list, intent: dict, type="chat") -> str:
    """
    Generates a response using DeepSeek Chat (V3).
    """
    if not client:
        configure_genai()
        if not client:
            return "Hệ thống AI đang bảo trì (Missing Key)."

    try:
        # Construct System Prompt based on context
        system_prompt = f"""Bạn là trợ lý ảo bán hàng chuyên nghiệp của cửa hàng 'Map Excel API Chat'.
        Nhiệm vụ: Tư vấn sản phẩm, gợi ý cửa hàng gần nhất và chốt đơn.
        
        Thông tin khách hàng đang xem:
        {json.dumps(context, ensure_ascii=False, indent=2)}

        Yêu cầu trả lời:
        - Ngắn gọn, thân thiện, dùng emoji.
        - Nếu có sản phẩm phù hợp, hãy mời khách chốt đơn.
        - Nếu không có, gợi ý sản phẩm tương tự.
        """

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7,
            max_tokens=500,
            stream=False
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"DeepSeek Chat Error: {e}")
        return "Xin lỗi, em đang bị quá tải. Anh chị chờ chút nhé!"

async def extract_search_intent(query: str, categories: list = None) -> dict:
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
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a JSON extractor."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Intent Extraction Error: {e}")
        return {}

async def smart_product_filter(query: str, products: list) -> dict:
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
