"""
Product View Service - Proxy Dropbuy product pages
Adapted from test/server_v2.py for production use
"""

import requests
import os
from fastapi.responses import HTMLResponse

# Configuration
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Origin": "https://dropbuy.vn",
    "Referer": "https://dropbuy.vn/"
}

def get_product_html(product_id: str, product_url: str = None) -> str:
    """
    Get product HTML from cache or scrape from Dropbuy
    """
    cache_path = os.path.join(CACHE_DIR, f"{product_id}.html")
    
    # Check cache first
    if os.path.exists(cache_path):
        print(f"✅ Cache hit for product {product_id}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # Scrape if not cached
    if not product_url:
        raise ValueError("Product URL required for scraping")
    
    print(f"🌐 Scraping product {product_id} from {product_url}")
    try:
        resp = requests.get(product_url, headers=HEADERS)
        
        if resp.status_code != 200:
            return f"<h1>Failed to scrape</h1><p>Status: {resp.status_code}</p><p>URL: {product_url}</p>"
        
        # Clean and process HTML
        cleaned_html = clean_html_for_chatbox_redirect(resp.text, product_id)
        
        # Save to cache
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(cleaned_html)
        
        print(f"💾 Cached product {product_id}")
        return cleaned_html
        
    except Exception as e:
        print(f"❌ Error scraping: {e}")
        return f"<h1>Error: {e}</h1>"

def clean_html_for_chatbox_redirect(html_content: str, product_id: str) -> str:
    """
    Process HTML to:
    1. Keep original Dropbuy UI/UX
    2. Hijack buy buttons to redirect to chatbox
    3. Disable navigation features
    """
    # 1. Base Tag for Assets
    if "<head>" in html_content:
        html_content = html_content.replace("<head>", '<head>\n<base href="https://dropbuy.vn/">')
    
    # 2. Surgical Button Hijacking Script
    # NOTE: Using raw string to avoid f-string syntax issues with JS code
    hijack_script = """
    <script>
    (function() {
        'use strict';
        
        var PRODUCT_ID = "PLACEHOLDER_PRODUCT_ID";
        console.log('🎯 Product View Script Loaded - Product ID:', PRODUCT_ID);
        
        // Extract product info
        function getProductInfo() {
            var title = document.title ? document.title.split('|')[0].trim() : "Sản phẩm";
            return { name: title, id: PRODUCT_ID };
        }
        
        // Robust redirect mechanism
        function redirectToChatbox() {
            var val = getProductInfo();
            // PERSISTENCE: Check for Zalo link and product name passed from previous screen
            const currentParams = new URLSearchParams(window.location.search);
            const zaloLink = currentParams.get('zalo');
            const passedName = currentParams.get('product_name');
            
            // Priority: URL Name > document.title
            const finalName = passedName || val.name;
            
            let chatboxUrl = window.location.origin + `/index.html?product_interest=${val.id}&product_name=${encodeURIComponent(finalName)}`;
            
            if (zaloLink) {
                 chatboxUrl += `&zalo=${encodeURIComponent(zaloLink)}`;
            }
            
            window.location.href = chatboxUrl;
        }

        // BLOCKER: Prevent navigation to Dropbuy pages
        function blockNavigationLinks() {
            document.body.addEventListener('click', function(e) {
                // Traverse up to find <a> tag
                let target = e.target;
                while (target && target.tagName !== 'A') {
                    target = target.parentNode;
                }
                
                if (target && target.tagName === 'A') {
                    // Allowed: Anchors (#), JavaScript links, or our Hijacked buttons
                    if (target.dataset.hijacked === 'true') return;
                    if (target.getAttribute('href').startsWith('#')) return;
                    if (target.getAttribute('href').startsWith('javascript:')) return;
                    
                    // Allow image lightbox/gallery if it uses <a> tags (common in e-commerce)
                    // Heuristic: if href ends in image extension
                    const href = target.getAttribute('href').toLowerCase();
                    if (href.match(/\.(jpeg|jpg|gif|png)$/)) return;

                    // Block everything else
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Optional: Show Toast
                    showToast("⚠️ Chức năng chuyển trang đã bị tắt trong chế độ Xem Nhanh.");
                }
            }, true); // Capture phase to beat other listeners
        }

        // Simple Toast UI
        function showToast(message) {
            let toast = document.createElement('div');
            toast.innerText = message;
            toast.style.position = 'fixed';
            toast.style.bottom = '20px';
            toast.style.left = '50%';
            toast.style.transform = 'translateX(-50%)';
            toast.style.backgroundColor = 'rgba(0,0,0,0.8)';
            toast.style.color = 'white';
            toast.style.padding = '10px 20px';
            toast.style.borderRadius = '20px';
            toast.style.zIndex = '99999';
            toast.style.transition = 'opacity 0.5s';
            document.body.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 500);
            }, 2000);
        }

        // HIJACK LOGIC: Find existing buttons and override them
        function hijackBuyButtons() {
            // Selectors for common buy buttons
            var selectors = [
                'button.btn-add-to-cart', '#btn-add-to-cart',
                'button.btn-buy-now', '#btn-buy-now',
                'button[class*="buy"]', 'a[class*="buy"]',
                'button[class*="cart"]', 'a[class*="cart"]',
                '.product-form__submit', '.btn-checkout',
                'button' // Fallback to all buttons if specific ones aren't found immediately
            ];
            
            selectors.forEach(function(sel) {
                var buttons = document.querySelectorAll(sel);
                buttons.forEach(function(btn) {
                    // Check if button text looks like a buy action
                    var txt = btn.innerText ? btn.innerText.toLowerCase() : "";
                    if (txt.includes('mua') || txt.includes('đặt') || txt.includes('giỏ') || txt.includes('thêm')) {
                        
                        if (btn.dataset.hijacked === 'true') return;
                        
                        // CLONE to strip existing event listeners (The "Seal")
                        var newBtn = btn.cloneNode(true);
                        newBtn.dataset.hijacked = 'true';
                        
                        newBtn.disabled = false;
                        newBtn.style.cursor = 'pointer';
                        
                        newBtn.onclick = function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log("🛒 Hijacked Buy Button Clicked");
                            redirectToChatbox();
                            return false; 
                        };
                        
                        if (btn.parentNode) {
                            btn.parentNode.replaceChild(newBtn, btn);
                            console.log('✅ Button Hijacked:', txt);
                        }
                    }
                });
            });
        }
        
        // Execute hijacking continuously to catch dynamic elements
        window.addEventListener('load', function() {
            blockNavigationLinks(); // Activate global blocker
            setInterval(hijackBuyButtons, 1000);
        });
        document.addEventListener('DOMContentLoaded', hijackBuyButtons);
        
        // FIX: Handle bfcache (Back button issue)
        window.addEventListener('pageshow', function(event) {
            if (event.persisted) {
                 hijackBuyButtons();
                 blockNavigationLinks();
            }
        });

    })();
    </script>
    
    <style>
    /* LOCK BUTTONS UNTIL READY (Functional only) */
    button:not([data-hijacked]), 
    a[class*="buy"]:not([data-hijacked]), 
    a[class*="cart"]:not([data-hijacked]) { 
        pointer-events: none !important; 
    }

    /* PRIORITY: Hide Dropbuy Logo */
    img[src*="logo"], img[alt="Logo"], .logo-wrapper img {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        width: 0 !important;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.95); }
        to { opacity: 1; transform: scale(1); }
    }
    body::after {
        content: "🎯 PROXY";
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(40, 167, 69, 0.9);
        color: white;
        padding: 6px 12px;
        border-radius: 15px;
        font-weight: bold;
        z-index: 999998;
        font-size: 11px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    </style>
    """
    
    # Inject Product ID into script
    hijack_script = hijack_script.replace("PLACEHOLDER_PRODUCT_ID", product_id)
    
    # 3. Custom Header (Restored from server_v2.py)
    custom_header = '<div id="my-custom-header" style="background: #e3f2fd; color: #0d47a1; padding: 10px; text-align: center; border-bottom: 1px solid #90caf9; font-family: sans-serif; font-weight: bold; position: relative; z-index: 999999;">✅ PROXY VIEW - Chất lượng cao</div>'
    
    # Inject script before </head>
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{hijack_script}\n</head>")
    
    # Inject header after <body>
    if "<body" in html_content:
         body_start = html_content.find("<body")
         body_tag_end = html_content.find(">", body_start)
         if body_tag_end != -1:
             html_content = html_content[:body_tag_end+1] + custom_header + html_content[body_tag_end+1:]
    
    return html_content
