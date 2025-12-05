import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load dotenv at module level is fine for local dev, but explicit config is better
load_dotenv()

model = genai.GenerativeModel('gemini-2.0-flash')

def configure_genai():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: GEMINI_API_KEY not found in environment variables!")
    else:
        print(f"SUCCESS: Found GEMINI_API_KEY (Length: {len(api_key)}). Configuring GenAI...")
    genai.configure(api_key=api_key)

async def get_ai_response(user_message: str, stores_info: list[dict] | None, search_intent: dict | None = None, match_type: str | None = None):
    messages = []
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
                # Case: Specific product sought but not found, falling back to category
                prompt += f"Chỉ dẫn:\n1. Người dùng tìm '{product_name}' nhưng hiện tại KHÔNG có cửa hàng nào gần đây bán chính xác sản phẩm đó.\n2. Hệ thống tìm thấy các cửa hàng thuộc nhóm '{category_name}' để thay thế.\n3. Hãy nói rõ: 'Tiếc là mình không thấy cửa hàng nào có sẵn {product_name} ở gần bạn. Tuy nhiên, mình tìm thấy các cửa hàng {category_name} này có thể phù hợp...'.\n4. Giới thiệu ngắn gọn."
            else:
                # Case: Generic search (e.g. "Mua điện thoại", "Mua máy tính")
                prompt += f"Chỉ dẫn:\n1. Người dùng đang tìm kiếm chung về '{category_name}' (hoặc các sản phẩm thuộc nhóm này).\n2. Hãy nói: 'Mình tìm thấy các cửa hàng {category_name} này phù hợp với nhu cầu của bạn...'.\n3. Giới thiệu ngắn gọn."

    elif search_intent and search_intent.get('is_location_request'):
        # User asked for location
        prompt += f"User Query: {user_message}.\n\nChỉ dẫn:\nNgười dùng đang hỏi về vị trí. Hãy trả lời ngắn gọn: '...' (Frontend sẽ tự động xử lý phần còn lại)."

    elif search_intent:
        # Intent found but no store found (neither product nor category)
        product_name = search_intent.get('product') or search_intent.get('category')
        prompt += f"User Query: {user_message}.\n\nChỉ dẫn:\nNgười dùng muốn tìm '{product_name}' nhưng hiện tại không tìm thấy cửa hàng nào phù hợp trong hệ thống. Hãy xin lỗi khách hàng một cách khéo léo và hỏi họ muốn tìm sản phẩm khác không."
    else:
        # No intent found -> Social chat
        prompt += f"User Query: {user_message}.\n\nChỉ dẫn:\nĐây là hội thoại xã giao hoặc câu hỏi chưa rõ ý định.\n1. Tự xưng là 'Trợ lý ảo'.\n2. Nếu người dùng nói muốn mua đồ chung chung, hãy hỏi thẳng: 'Bạn đang tìm kiếm sản phẩm nào cụ thể ạ? (Ví dụ: Điện thoại, Quần áo, Laptop...)' (KHÔNG cần chào 'Chào bạn' ở đầu).\n3. CHỈ chào hỏi ('Chào bạn!...') NẾU người dùng có lời chào trước (như 'hi', 'xin chào').\n4. TUYỆT ĐỐI KHÔNG dùng các từ trong ngoặc vuông như '[...]'."

    try:
        print(f"DEBUG: Sending prompt to Gemini:\n{prompt}")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"CRITICAL ERROR in get_ai_response: {e}")
        import traceback
        traceback.print_exc()
        return "Xin lỗi, tôi đang gặp vấn đề. Vui lòng thử lại sau."

async def extract_search_intent(user_message: str, valid_categories: list[str] | None = None) -> dict | None:
    """
    Extracts product and category in JSON format.
    Returns None if no specific intent is found.
    Example return: {"product": "iPhone 15", "category": "Điện thoại"}
    """
    if not valid_categories:
        valid_categories = ["Công nghệ", "Thời trang", "Ẩm thực"] # Fallback if empty

    # --- ƯU TIÊN TUYỆT ĐỐI (Hard Rule) ---
    # Kiểm tra nhanh bằng Regex để đảm bảo không bao giờ sai sót với các câu lệnh vị trí
    import re
    # Các từ khóa: "vị trí", "tọa độ", "ở đâu" + "tôi", "mình", "user", "hiện tại"
    # Hoặc các câu ngắn cụt lủn: "vị trí", "tọa độ", "location"
    user_msg_lower = user_message.lower()
    location_keywords = ["vị trí", "tọa độ", "định vị", "ở đâu", "location", "gps"]
    
    # Check 1: Câu lệnh ngắn chứa từ khóa (ví dụ: "vị trí", "xem tọa độ")
    if len(user_msg_lower.split()) <= 3 and any(k in user_msg_lower for k in location_keywords):
        print("DEBUG: Detected Location Request via Regex (Short Command)")
        return {"product": None, "generic_term": None, "category": None, "is_location_request": True}
        
    # Check 2: Câu có ngữ nghĩa vị trí + đối tượng (tôi/mình/hiện tại)
    if any(k in user_msg_lower for k in location_keywords) and any(p in user_msg_lower for p in ["tôi", "mình", "user", "hiện tại", "của tớ"]):
        print("DEBUG: Detected Location Request via Regex (Keyword Combination)")
        return {"product": None, "generic_term": None, "category": None, "is_location_request": True}

    # Check 3: Generic "buy stuff" queries that confuse the AI (Hardcoded Override)
    # Các từ khóa chung chung không rõ ý định
    generic_keywords = ["mua đồ", "sắm đồ", "mua sắm", "shopping", "mua gì đó"]
    # Nếu câu chứa từ khóa chung chung VÀ ngắn (dưới 6 từ) -> Return None để Bot hỏi lại
    if any(k in user_msg_lower for k in generic_keywords) and len(user_msg_lower.split()) <= 6:
        print("DEBUG: Detected Generic Query (Hardcoded Python Check) -> Force Return None")
        return None
    # -------------------------------------
    #old rule:1. Nếu người dùng hỏi về vị trí của họ (ví dụ: "vị trí của tôi", "tôi đang ở đâu", "tìm vị trí user"), set "is_location_request": true. Các trường khác null.
    system_instruction = f"""Bạn là công cụ trích xuất ý định.
Nhiệm vụ: Trích xuất 'product', 'generic_term', 'category' và 'is_location_request'.
Output format: JSON ONLY.
Rules:
1. ƯU TIÊN TUYỆT ĐỐI: Nếu câu hỏi có chứa từ khóa "vị trí", "ở đâu", "tọa độ", "định vị" VÀ ám chỉ người dùng (tôi, mình, user) -> set "is_location_request": true. (Bất kể câu hỏi dài hay ngắn, lịch sự hay cộc lốc).
   * Ví dụ: "Xin hỏi vị trí hiện tại của tôi là ở đâu vậy" -> true.
   * Ví dụ: "Tôi đang ở chỗ nào" -> true.
2. Nếu tìm sản phẩm:
   - "product": Tên cụ thể (iPhone 16).
   - "generic_term": Từ khóa chung nhất (iPhone, Laptop, Giày).
     * ĐẶC BIỆT: "máy tính" -> generic_term: "Laptop".
     * "điện thoại" -> generic_term: "Điện thoại".
     * "áo", "quần" -> generic_term: "Quần áo".
   - "category": Chọn từ danh sách {valid_categories}. Ưu tiên "Thời trang" nếu tìm áo/quần.

3. TRƯỜNG HỢP NGOẠI LỆ (QUAN TRỌNG):
   - Nếu người dùng nói chung chung như "mua đồ", "đi shopping", "muốn mua gì đó" mà KHÔNG có tên sản phẩm cụ thể -> Return tất cả là null.

Ví dụ:
- "Mua iPhone 16" -> {{"product": "iPhone 16", "generic_term": "iPhone", "category": "Công nghệ", "is_location_request": false}}
- "Tôi muốn mua đồ" -> {{"product": null, "generic_term": null, "category": null, "is_location_request": false}}
- "Vị trí của tôi ở đâu" -> {{"product": null, "generic_term": null, "category": null, "is_location_request": true}}
"""
    
    prompt = f"{system_instruction}\n\nUser Message: {user_message}"

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                response_mime_type="application/json"
            )
        )
        import json
        content = response.text.strip()
        print(f"DEBUG: Intent JSON: {content}")
        data = json.loads(content)
        
        if not data.get('product') and not data.get('category'):
            return None
            
        return data
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return None

if __name__ == '__main__':
    # Example usage (for testing purposes)
    import asyncio

    async def test_ai_service():
        # Test with store info
        store = {
            "store_name": "Shop Demo",
            "distance_km": 0.5,
            "product_info": "Running shoes size 42, color blue",
            "promotion": "Flash sale 20% off",
            "address": "123 Test Street, Test City"
        }
        print("Testing AI Response with store info...")
        response_with_store = await get_ai_response("Tôi muốn tìm giày chạy bộ size 42.", store)
        print(f"AI Response: {response_with_store}\n")

        # Test intent extraction
        print("Testing Intent Extraction...")
        intent = await extract_search_intent("Tôi muốn mua một chiếc iPhone 15")
        print(f"Extracted Intent: {intent}")

    asyncio.run(test_ai_service())
