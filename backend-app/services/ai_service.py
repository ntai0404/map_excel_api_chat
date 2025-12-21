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

def get_model(model_name=None):
    """Get or initialize the Gemini model."""
    global _model
    config = get_config()
    
    # If using Custom API (Ollama), we don't need a Gemini model object
    if config["AI_API_BASE"]:
        return None
        
    # Lazy init or specific model request
    # Note: Global _model stores the *default* configured model.
    # If a specific name is requested, we create a new instance (lightweight).
    target_model = model_name or config["AI_MODEL_NAME"]

    api_key = config["AI_API_KEY"]
    if not api_key:
        print("WARNING: AI_API_KEY not found. Gemini API calls will likely fail.")
        return None
        
    try:
        # Re-configure if key changed (or first run)
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(target_model)
    except Exception as e:
        print(f"Error configuring Gemini ({target_model}): {e}")
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
        context = "Thông tin các cửa hàng phù hợp nhất:\n"
        for i, store in enumerate(stores_info):
            # Compatibility for different keys
            name = store.get('name') or store.get('store_name')
            
            # Format product list
            products_display = ""
            if store.get('products'):
                # Limit to 5 items to save tokens
                p_names = [f"- {p['name']} ({p['price']})" for p in store['products'][:5]]
                products_display = "\n    " + "\n    ".join(p_names)
            else:
                products_display = store.get('product_info', 'Đang cập nhật sản phẩm')

            context += (
                f"Cửa hàng {i+1}: {name}\n"
                f"- Khoảng cách: {store['distance_km']:.2f} km\n"
                f"- Địa chỉ: {store['address']}\n"
                f"- Sản phẩm tiêu biểu:{products_display}\n"
                f"- Khuyến mãi: {store.get('promotion', 'Không')}\n\n"
            )
        prompt += f"Context: {context}\n\nUser Query: {user_message}.\n\n"
        
        # Add explicit instruction for links
        prompt += "QUAN TRỌNG: Khi trả về link sản phẩm hoặc link xem chi tiết, hãy dùng thẻ HTML <a href='...' target='_self'>...</a> thay vì markdown [ ](...) để đảm bảo link mở trong tab hiện tại.\n"
        
        if match_type == 'product':
            prompt += "Chỉ dẫn:\n1. Người dùng tìm đúng sản phẩm có trong Context. Hãy báo tin vui và mời họ đến.\n2. Liệt kê các sản phẩm cụ thể có giá (nếu có)."
        elif match_type == 'category':
            product_name = search_intent.get('product')
            category_name = search_intent.get('category') or 'danh mục này'
            
            if product_name:
                prompt += f"Chỉ dẫn:\n1. Người dùng tìm '{product_name}' nhưng KHÔNG có shop nào gần đây bán chính xác tên đó.\n2. Hệ thống đã tìm thấy các shop thuộc loại '{category_name}' thay thế.\n3. Hãy nói: 'Tiếc là mình không thấy {product_name} ở gần. Nhưng bạn có thể ghé các shop {category_name} này, họ có bán các sản phẩm tương tự như sau...'.\n4. Dựa vào Context, giới thiệu vài sản phẩm tiêu biểu của họ."
            else:
                prompt += f"Chỉ dẫn:\n1. Người dùng tìm chung về '{category_name}'.\n2. Giới thiệu các shop tìm thấy và liệt kê một số sản phẩm tiêu biểu trong Context."

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
        
        # Case 2: Standard Gemini with FALLBACK
        # List of models to try in order of preference (Low Quota -> Higher Capacity)
        candidate_models = [
            config['AI_MODEL_NAME'], # Try user config first
            "gemini-2.0-flash", 
            "gemini-2.0-flash-lite", 
            "gemini-1.5-flash", 
            "gemini-1.5-pro"
        ]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        for m_name in candidate_models:
            try:
                print(f"DEBUG: Sending prompt to Gemini ({m_name})...")
                model = get_model(m_name)
                if not model: continue
                
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "404" in error_str or "quota" in error_str.lower():
                    print(f"WARNING: Model {m_name} failed ({error_str}). Switching to next...")
                    continue
                else:
                    # Non-quota error (e.g. content policy), re-raise or return error
                    print(f"ERROR: Model {m_name} encountered critical error: {e}")
                    raise e
        
        return "Xin lỗi, hệ thống đang quá tải. Vui lòng thử lại sau ít phút."
            
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

    # HARDCODED CHECK REMOVED: Relying on AI for generic vs specific intent.
    # generic_keywords = ["mua đồ", "sắm đồ", "mua sắm", "shopping", "mua gì đó"]
    # ... code removed ...

    system_instruction = f"""Bạn là công cụ trích xuất ý định tìm kiếm sản phẩm.
    Nhiệm vụ: Phân tích và trích xuất thông tin sang định dạng JSON.
    
    DANH SÁCH NGÀNH HÀNG HỢP LỆ (chọn 1 trong các mục này làm ngành hàng cho sản phẩm, copy Y HỆT từng dấu cách):
    [
        "Balo - Túi xách - Vali", "Bàn , ghế", "Bàn chải & Tăm nước", "Bàn phím & Chuột", "Bình nước nóng",
        "Bếp từ , bếp điện", "Chăm sóc nhà cửa", "Củ cáp sạc", "Dịch vụ , phần mềm online…", "Dụng cụ cầm tay , máy khoan , cắt…",
        "Dụng cụ nhà bếp", "Dụng cụ thể thao", "Kính mắt", "Loa", "Ly, cốc, bình giữ nhiệt", "Máy chiếu",
        "Máy chơi game", "Máy hút ẩm , tạo ẩm , phun sương", "Máy lọc không khí", "Máy Massage", "Máy tính & Laptop",
        "Máy xay - Máy ép", "Máy ảnh & Camera", "Mũ nón", "Mẹ và Bé", "Nhà cửa & đời sống", "Nội thất",
        "Phòng ngủ", "Phụ kiện khác", "Phụ tùng", "Pin,Sạc dự phòng , ắc quy", "Quần áo", "Robot & Máy hút bụi , lau nhà",
        "Sức khỏe & làm đẹp", "Tai nghe - Micro", "Thiết bị - Phụ kiện", "Thiết bị khác", "Thiết bị âm thanh",
        "Thiết bị điện gia dụng", "Thùng các tông", "Thời trang", "Thực phẩm & Đồ ăn", "Tivi ; máy chiếu",
        "Trang sức", "Trang trí nhà cửa", "Văn phòng phẩm", "Vỏ ốp lưng & miếng dán", "Vợt muỗi , đèn bắt muỗi",
        "Xốp , bọt , cột khí", "Ô tô - Xe máy - Xe đạp", "Điều hòa - Quạt", "Điện thoại & phụ kiện", "Điện thoại",
        "Đèn & ánh sáng", "Đồ Camping , phượt , cắm trại", "Đồ chơi - Phụ kiện", "Đồ chơi người lớn , phòng the",
        "Đồ chơi", "Đồ dùng khác", "Đồ dùng nhà tắm", "Đồ phong thuỷ , tâm linh", "Đồng hồ"
    ]
    (Bỏ qua valid_categories truyền vào từ code, HÃY DÙNG DANH SÁCH CỐ ĐỊNH NÀY)
    
    Output JSON format:
    {{
        "product": "tên sản phẩm cụ thể hoặc null",
        "generic_term": "tên loại sản phẩm chung hoặc null",
        "category": "TÊN NGÀNH HÀNG CHÍNH XÁC (copy 100% từ danh sách trên) hoặc null",
        "is_location_request": boolean,
        "is_general_inquiry": boolean
    }}

    QUY LUẬT XỬ LÝ:
    1. ƯU TIÊN VỊ TRÍ: Nếu người dùng hỏi "vị trí", "ở đâu", "tọa độ" (ám chỉ bản thân họ) -> "is_location_request": true.
    
    2. NHẬN DIỆN CÂU HỎI CHUNG: Nếu người dùng hỏi chung chung về sản phẩm/danh mục (KHÔNG chỉ định sản phẩm cụ thể):
       - "bạn bán những gì", "shop có gì", "có sản phẩm nào", "danh mục gì", "ngành hàng nào"
       - "xin chào", "hello", "hi", "chào bạn", "chào shop" (lời chào)
       -> "is_general_inquiry": true, product: null, category: null
       
    3. XÁC ĐỊNH NGÀNH HÀNG (QUAN TRỌNG NHẤT):
       - Dựa vào từ khóa sản phẩm, hãy tìm trong Danh Sách Ngành Hàng mục nào sát nghĩa nhất.
       - Ví dụ: "quần áo bơi bé gái" -> category: "Mẹ và Bé"
       - Ví dụ: "Ăn phở" -> category: "Thực phẩm & Đồ ăn".
       - Nếu không tìm thấy ngành hàng phù hợp -> category: null.
       
    4. XÁC ĐỊNH SẢN PHẨM:
       - "product": lọc tên sản phẩm từ khóa chính xác người dùng nhập (VD: "bánh mì chảo", "iphone 15 pro max").
       - "generic_term": Loại sản phẩm (VD: "bánh mì", "điện thoại").
       
    5. TRƯỜNG HỢP KHÓ / CHUNG CHUNG:
       - "mua đồ", "shopping" -> "is_general_inquiry": true
       - "đồ ăn", "ăn uống" -> "category": "Thực phẩm & Đồ ăn" (Chọn từ danh sách), "product": "đồ ăn".
    
    Ví dụ mẫu:
    - User: "xin chào"
      Output: {{"product": null, "generic_term": null, "category": null, "is_location_request": false, "is_general_inquiry": true}}
    
    - User: "bạn bán những gì"
      Output: {{"product": null, "generic_term": null, "category": null, "is_location_request": false, "is_general_inquiry": true}}
    
    - User: "Tìm quán phở bò"
      Output: {{"product": "phở bò", "generic_term": "phở", "category": "Thực phẩm & Đồ ăn", "is_location_request": false, "is_general_inquiry": false}}
      
    - User: "Mua cái bàn làm việc"
      Output: {{"product": "bàn làm việc", "generic_term": "bàn", "category": "Nội thất", "is_location_request": false, "is_general_inquiry": false}}

    - User: "đồ chơi người lớn"
      Output: {{"product": "đồ chơi người lớn", "generic_term": "đồ chơi", "category": "Đồ chơi người lớn , phòng the", "is_location_request": false, "is_general_inquiry": false}}
    """
    
    prompt = f"{system_instruction}\n\nUser Message: {user_message}"

    try:
        content = ""
        config = get_config()
        
        if config["AI_API_BASE"]:
            content = call_custom_api(prompt, json_mode=True)
        else:
            # Fallback loop for Intent Extraction too
            candidate_models = [
                config['AI_MODEL_NAME'],
                "gemini-2.0-flash", 
                "gemini-2.0-flash-lite", 
                "gemini-1.5-flash"
            ]
            candidate_models = list(dict.fromkeys(candidate_models))
            
            content = None
            for m_name in candidate_models:
                try:
                    model = get_model(m_name)
                    if not model: continue
                    
                    response = model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0,
                            response_mime_type="application/json"
                        )
                    )
                    content = response.text.strip()
                    break # Success
                except Exception as e:
                     print(f"WARNING: Intent Extraction failed on {m_name}: {e}. Retrying...")
                     continue
            
            if not content:
                 print("ERROR: All models failed for intent extraction.")
                 return None

        print(f"DEBUG: Intent JSON: {content}")
        data = json.loads(content)
        
        # Logic fix: If any meaningful field exists, it IS a valid search intent.
        if (not data.get('product') and not data.get('category') and 
            not data.get('is_location_request') and not data.get('generic_term') and 
            not data.get('is_general_inquiry')):
            return None
            
        return data
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return None

async def smart_product_filter(user_query: str, category_products: list[dict]) -> dict:
    """
    AI Call #2: Smart product filtering with template generation
    
    Args:
        user_query: User's search query
        category_products: List of {"product_name": "...", "shop_name": "..."}
    
    Returns:
        {
            "found": bool,
            "products": [{"product_name": "...", "shop_name": "..."}],
            "ai_message_template": str
        }
    """
    
    # Prepare product list for AI
    products_text = json.dumps(category_products, ensure_ascii=False, indent=2)
    
    system_instruction = f"""Bạn là công cụ tìm kiếm sản phẩm thông minh.

Nhiệm vụ: Tìm sản phẩm khớp với truy vấn "{user_query}" trong danh sách sản phẩm sau.

Danh sách sản phẩm:
{products_text}

Yêu cầu:
1. Trả về JSON với format:
   {{
     "found": true/false,
     "products": [{{"product_name": "...", "shop_name": "..."}}],
     "ai_message_template": "..."
   }}

2. Template có thể dùng các placeholder sau (hệ thống sẽ tự bù giá trị):
   - {{{{product_name}}}}: Tên sản phẩm
   - {{{{shop_name}}}}: Tên shop
   - {{{{distance}}}}: Khoảng cách (km)
   - {{{{address}}}}: Địa chỉ shop
   - {{{{price}}}}: Giá sản phẩm
   - {{{{image_url}}}}: Link ảnh sản phẩm
   - {{{{zalo_link}}}}: Link Zalo shop

3. NẾU tìm thấy sản phẩm khớp:
   - "found": true
   - "products": Danh sách sản phẩm khớp (tối đa 3)
   - "ai_message_template": Câu giới thiệu tự nhiên, thân thiện với placeholder

4. NẾU KHÔNG tìm thấy:
   - "found": false
   - "products": []
   - "ai_message_template": null

5. TUYỆT ĐỐI chỉ dùng tên sản phẩm và shop từ danh sách, KHÔNG tự sáng tạo
6. Template phải tự nhiên, phù hợp ngữ cảnh Việt Nam
7. Sử dụng placeholder đúng format (ví dụ: {{{{product_name}}}})
"""

    prompt = f"User Query: {user_query}"
    
    try:
        config = get_config()
        
        # Case 1: Custom API (e.g. Ollama)
        if config["AI_API_BASE"]:
            content = call_custom_api(prompt, system_instruction, json_mode=True)
        else:
            # Case 2: Standard Gemini with FALLBACK
            candidate_models = [
                config['AI_MODEL_NAME'],
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-1.5-pro"
            ]
            candidate_models = list(dict.fromkeys(candidate_models))
            
            content = None
            for m_name in candidate_models:
                try:
                    print(f"DEBUG: Calling smart_product_filter with {m_name}...")
                    model = get_model(m_name)
                    if not model: continue
                    
                    response = model.generate_content(
                        f"{system_instruction}\n\n{prompt}",
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.3,
                            response_mime_type="application/json"
                        )
                    )
                    content = response.text.strip()
                    break
                except Exception as e:
                    print(f"WARNING: smart_product_filter failed on {m_name}: {e}. Retrying...")
                    continue
            
            if not content:
                print("ERROR: All models failed for smart_product_filter.")
                raise Exception("All AI models failed")
        
        print(f"DEBUG: smart_product_filter JSON: {content}")
        data = json.loads(content)
        
        # Validate response format
        if 'found' not in data or 'products' not in data:
            raise ValueError("Invalid response format from AI")
        
        return data
        
    except Exception as e:
        print(f"Error in smart_product_filter: {e}")
        raise e
