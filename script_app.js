console.log("🚀 script_app.js v3.9 - ONCE-ONLY LEAD MODAL...");

// 0. AGGRESSIVE CSS INJECTION FOR GOOGLE MAPS INFOWINDOW (FIX FOR REMOTE CACHING)
(function injectStyles() {
    const styleId = 'google-maps-iw-fix';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
        /* Remove whitespace and padding from Google Maps InfoWindow default bubble */
        .gm-style-iw-c {
            padding: 0 !important;
            max-width: none !important;
            max-height: none !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15) !important;
        }
        .gm-style-iw-d {
            overflow: hidden !important;
            padding: 0 !important;
            margin: 0 !important;
            max-width: none !important;
            max-height: none !important;
        }
        /* Custom content inside the InfoWindow */
        .iw-content-v27 {
            padding: 12px !important;
            margin: 0 !important;
            width: 300px !important;
            box-sizing: border-box !important;
            display: flex !important;
            flex-direction: column !important;
            font-family: 'Inter', sans-serif !important;
        }
        .iw-content-v27.is-mobile { width: 250px !important; }
        .iw-title {
            font-size: 16px !important;
            font-weight: 800 !important;
            color: #1a73e8 !important;
            margin: 0 0 2px 0 !important;
            line-height: 1.2 !important;
            display: block !important;
        }
        .iw-address {
            font-size: 11px !important;
            color: #666 !important;
            line-height: 1.3 !important;
            margin: 0 0 5px 0 !important;
            display: block !important;
        }
        .iw-product {
            margin-top: 8px !important;
            border-top: 1px dashed #eee !important;
            padding-top: 8px !important;
            display: flex !important;
            gap: 10px !important;
            align-items: center !important;
        }
        .iw-product-img {
            width: 50px !important;
            height: 50px !important;
            object-fit: cover !important;
            border-radius: 4px !important;
            flex-shrink: 0 !important;
        }
        .iw-product-info { flex: 1 !important; overflow: hidden !important; }
        .iw-product-name {
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #333 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        .iw-product-price {
            font-size: 14px !important;
            font-weight: 700 !important;
            color: #e53935 !important;
        }
        /* Fix close button position */
        .gm-ui-hover-effect {
            top: 2px !important;
            right: 2px !important;
            background: rgba(255,255,255,0.9) !important;
            border-radius: 50% !important;
        }
    `;
    document.head.appendChild(style);
})();

// DUAL ACTION: Join Group + Chat with Admin/Staff
// Global function to be accessible by onclick handlers
function handleDualZaloAction(groupLink, productName, staffZalo) {
    // 1. Prepare Admin Chat Link (Deep Link)
    // If staffZalo is provided (from Link NV), use it. Otherwise placeholder or skip.
    // If staffZalo is missing or invalid, we prioritize Group Link only.

    let adminChatLink = "";

    if (staffZalo && staffZalo.length > 8) {
        const msg = encodeURIComponent(`Chào bạn, tôi quan tâm sản phẩm: ${productName}. Nhờ hỗ trợ!`);
        adminChatLink = `https://zalo.me/${staffZalo}?text=${msg}`;
    }

    // DEBUG: Log to Console only (User Request)
    console.log("Dual Action Debug:", { groupLink, staffZalo, adminChatLink });

    // SEQUENCING FOR UX (User Verified):
    // 1. Open Group Link (Background Context)
    const win1 = window.open(groupLink, '_blank');

    // 2. Open Staff Chat (Foreground Action)
    if (adminChatLink) {
        // Try opening second tab
        const win2 = window.open(adminChatLink, '_blank');

        if (!win2 || win2.closed || typeof win2.closed == 'undefined') {
            renderMessage('ai', '<i class="material-icons" style="color:#f57f17; vertical-align:bottom;">warning</i> <b>LỖI CHẶN POP-UP!</b><br>Máy tính đã chặn cửa sổ Chat Nhân Viên. Vui lòng bấm vào icon [Pop-up] trên thanh địa chỉ và chọn "Always Allow" (Luôn cho phép).', true);
        } else {
            console.log("Dual Action: Group -> Staff Chat (Success)");
        }
    } else {
        renderMessage('ai', '<i class="material-icons" style="color:#f57f17; vertical-align:bottom;">warning</i> <b>LỖI DỮ LIỆU:</b> Không tìm thấy số Zalo nhân viên (Link NV).', true);
    }
}

let map;
let userMarker;
let storeMarkers = []; // Array of google.maps.Marker
let storeInfoWindows = []; // FIX 2: Track all InfoWindow instances
let currentUserLocation = null;
let googleMapsLoaded = false;
let chatHistory = []; // Global history array
window.lastSearchTime = Date.now(); // Global context timer
window.interestedProducts = JSON.parse(localStorage.getItem('interestedProducts') || '[]'); // Accumulate products user is interested in
function saveInterestedProducts() {
    localStorage.setItem('interestedProducts', JSON.stringify(window.interestedProducts));
}

// Helper to load Google Maps script dynamically
function loadGoogleMaps(apiKey) {
    if (googleMapsLoaded) return Promise.resolve();

    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
        script.async = true;
        script.defer = true;
        script.onload = () => {
            googleMapsLoaded = true;
            console.log("📍 Google Maps API Loaded.");
            resolve();
        };
        script.onerror = reject;
        document.head.appendChild(script);
    });
}


// Configure Markdown renderer safely
if (typeof marked !== 'undefined') {
    const renderer = new marked.Renderer();
    renderer.link = function (href, title, text) {
        // Prevent undefined hrefs if possible, though strictness is good
        if (!href || href === 'undefined' || href === 'null') href = '#';
        return `<a href="${href}" title="${title || ''}" target="_self">${text}</a>`;
    };
    marked.setOptions({ renderer: renderer });
}

// --- Chat History Persistence ---
function getStorage() {
    // We use sessionStorage for all users' chat history to ensure privacy on shared devices.
    // This persists during same-tab navigation but clears when the tab is closed.
    return sessionStorage;
}

function getHistoryKey() {
    const sessionId = localStorage.getItem('session_id') || 'guest';
    return `chat_history_${sessionId}`;
}

function saveHistory() {
    const storage = getStorage();
    storage.setItem(getHistoryKey(), JSON.stringify(chatHistory));
}

function loadHistory() {
    const storage = getStorage();
    const saved = storage.getItem(getHistoryKey());
    if (saved) {
        try {
            chatHistory = JSON.parse(saved);
            chatHistory.forEach(item => {
                if (item.type === 'message') {
                    renderMessage(item.sender, item.text, false);
                } else if (item.type === 'stores') {
                    renderStoreCards(item.data, false);
                }
            });
        } catch (e) {
            console.error("Error loading history:", e);
            chatHistory = [];
        }
    }
}

// Inject CSS for Store Cards
// Styles moved to style.css for cleaner separation and easier maintenance.
// const style = document.createElement('style'); ... (removed)

// 3.1. Khởi tạo Bản đồ (Map Initialization - Google Maps)
async function initializeMap() {
    if (!googleMapsLoaded) {
        console.warn("Map: Library not loaded yet.");
        return;
    }

    const mapOptions = {
        center: { lat: 10.762622, lng: 106.660172 }, // HCMC
        zoom: 13,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        styles: [
            {
                "featureType": "all",
                "elementType": "labels.text.fill",
                "stylers": [{ "color": "#7c93a3" }]
            }
        ]
    };

    map = new google.maps.Map(document.getElementById('map-container'), mapOptions);
}

function updateMap(userLat, userLng, stores) {
    if (!map || !googleMapsLoaded) return;

    // 1. Handle User Marker
    if (userMarker) {
        userMarker.setMap(null);
    }

    const isMobile = window.innerWidth <= 768;

    if (userLat && userLng) {
        const userPos = { lat: parseFloat(userLat), lng: parseFloat(userLng) };

        const userIcon = {
            url: "http://maps.google.com/mapfiles/ms/icons/red-dot.png"
        };

        userMarker = new google.maps.Marker({
            position: userPos,
            map: map,
            title: "Vị trí của bạn",
            icon: userIcon
        });

        const infoWindow = new google.maps.InfoWindow({
            content: "<b>Vị trí của bạn</b>"
        });
        userMarker.addListener("click", () => infoWindow.open(map, userMarker));

        map.panTo(userPos);
    }

    // 2. Handle Store Markers
    if (stores !== null) {
        // Clear old markers and InfoWindows
        storeMarkers.forEach(m => m.setMap(null));
        storeMarkers = [];
        storeInfoWindows = []; // FIX 2: Clear InfoWindow tracking

        if (stores.length > 0) {
            const bounds = new google.maps.LatLngBounds();
            if (userLat && userLng) bounds.extend({ lat: parseFloat(userLat), lng: parseFloat(userLng) });

            stores.forEach((store, index) => {
                const storePos = { lat: parseFloat(store.lat), lng: parseFloat(store.lng) };

                // Get first product if available for the popup
                const firstProduct = (store.products && store.products.length > 0) ? store.products[0] : null;

                // Premium Zalo Button for InfoWindow
                const zaloLink = store.zalo_group_link ?
                    `<a href="${store.zalo_group_link}" target="_blank" class="zalo-btn">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="white" style="flex-shrink:0; margin-right: 6px;"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.59.39 3.09 1.07 4.41L2 22l5.59-1.07C8.91 21.61 10.41 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.47 0-2.84-.4-4.02-1.1l-.29-.17-2.98.57.57-2.98-.17-.29C4.4 14.84 4 13.47 4 12c0-4.41 3.59-8 8-8s8 3.59 8 8-3.59 8-8 8z"/></svg>
                        <span>Tham gia nhóm Zalo</span>
                    </a>` : '';

                if (isMobile) {
                    infoWindowContent = `
                        <div class="iw-content-v27 is-mobile">
                            <b class="iw-title">${store.name}</b>
                            <div class="iw-address">${store.address || ''}</div>
                            ${zaloLink}
                        </div>
                    `;
                } else {
                    let productHtml = '';
                    if (firstProduct) {
                        productHtml = `
                            <div class="iw-product">
                                <img src="${firstProduct.image_url || 'https://via.placeholder.com/60'}" class="iw-product-img">
                                <div class="iw-product-info">
                                    <div class="iw-product-name">${firstProduct.name}</div>
                                    <div class="iw-product-price">${firstProduct.price}</div>
                                </div>
                            </div>
                        `;
                    }

                    infoWindowContent = `
                        <div class="iw-content-v27 is-desktop">
                            <b class="iw-title">${store.name}</b>
                            <div class="iw-address">${store.address || ''}</div>
                            ${productHtml}
                            ${zaloLink}
                        </div>
                    `;
                }

                const storeIcon = {
                    url: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"
                };

                const marker = new google.maps.Marker({
                    position: storePos,
                    map: map,
                    title: store.name,
                    icon: storeIcon
                });

                const infoWindow = new google.maps.InfoWindow({
                    content: infoWindowContent
                });

                // FIX 2: Store InfoWindow instance for later control
                storeInfoWindows.push(infoWindow);

                marker.addListener("click", () => {
                    // FIX 2: Close all other InfoWindows first
                    storeInfoWindows.forEach(iw => {
                        if (iw !== infoWindow) iw.close();
                    });
                    // Then open this one
                    infoWindow.open(map, marker);
                });

                // TỰ ĐỘNG MỞ InfoWindow cho TẤT CẢ các shop ngay khi có kết quả
                setTimeout(() => {
                    infoWindow.open(map, marker);
                }, 500 + (index * 150)); // Stagger slightly for a smoother cascade effect

                storeMarkers.push(marker);
                bounds.extend(storePos);
            });

            // Auto fit bounds
            map.fitBounds(bounds);
            // Limit zoom if only 1 marker
            if (stores.length === 1 && (!userLat || !userLng)) {
                google.maps.event.addListenerOnce(map, 'bounds_changed', () => {
                    if (map.getZoom() > 15) map.setZoom(15);
                });
            }
        }
    }
}

/**
 * Focuses the map on a specific store and opens its info window.
 * Used when clicking on store cards in the chat.
 */
function focusOnStore(lat, lng, name) {
    if (!map || !googleMapsLoaded) return;

    const pos = { lat: parseFloat(lat), lng: parseFloat(lng) };

    // FIX 2: Close all InfoWindows first to ensure clean focus
    storeInfoWindows.forEach(iw => iw.close());

    // Smoothly pan to the location
    map.panTo(pos);
    map.setZoom(17);

    // Find the marker for this store and trigger a click to show InfoWindow
    const marker = storeMarkers.find(m => {
        const mPos = m.getPosition();
        return Math.abs(mPos.lat() - pos.lat) < 0.0001 && Math.abs(mPos.lng() - pos.lng) < 0.0001;
    });

    if (marker) {
        // Trigger click will open only this InfoWindow (others already closed)
        google.maps.event.trigger(marker, 'click');
    }
}



// --- Geolocation Logic ---
let isLocating = false;

function isInVietnam(lat, lng) {
    // Rough coordinates for Vietnam mainland and islands
    return lat >= 8.0 && lat <= 24.0 && lng >= 102.0 && lng <= 110.0;
}

function getUserLocation(isAutoTriggered = false) {
    if (isLocating) {
        console.log("GPS: Request already in progress, returning current state...");
        return Promise.resolve(currentUserLocation);
    }

    return new Promise((resolve) => {
        if (!navigator.geolocation) {
            console.warn("GPS: Geolocation not supported.");
            resolve(null);
            return;
        }

        isLocating = true;
        let watchId = null;
        let bestPosition = null;
        let hasResolved = false;

        const stopWatching = () => {
            if (watchId !== null) {
                navigator.geolocation.clearWatch(watchId);
                watchId = null;
            }
            isLocating = false;
        };

        const currentOptions = {
            enableHighAccuracy: true,
            timeout: 8000,
            maximumAge: 0 // Always check fresh hardware
        };

        // FINAL RESOLVE: Only called once
        const finish = (pos) => {
            if (hasResolved) return;
            hasResolved = true;
            stopWatching();

            if (pos) {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                
                if (!isInVietnam(lat, lng)) {
                    console.warn(`📍 GPS: Detected location [${lat}, ${lng}] is outside Vietnam (likely a browser mockup or VPN error).`);
                    // We don't overwrite it here, but we'll show a warning later in handleLocationCheck
                }

                currentUserLocation = { lat: lat, lng: lng };
                sessionStorage.setItem('last_location', JSON.stringify(currentUserLocation));
                sessionStorage.setItem('last_location_acc', pos.coords.accuracy.toFixed(0));
                updateMap(currentUserLocation.lat, currentUserLocation.lng, null);
                console.log(`GPS: Finalized with Acc: ${pos.coords.accuracy.toFixed(1)}m`);
                resolve(currentUserLocation);
            } else {
                console.warn("GPS: Timeout/No position found.");
                resolve(null);
            }
        };

        // EMERGENCY TIMEOUT: If nothing happens in 4s, just give up
        const timer = setTimeout(() => {
            console.log("GPS: Emergency timeout reached.");
            finish(bestPosition);
        }, isAutoTriggered ? 2000 : 4000);

        watchId = navigator.geolocation.watchPosition(
            (position) => {
                const acc = position.coords.accuracy;
                console.log(`GPS: Reading - Acc: ${acc.toFixed(1)}m`);

                if (!bestPosition || acc < bestPosition.coords.accuracy) {
                    bestPosition = position;
                }

                // SPEED OPTIMIZATION:
                // 1. If we hit high precision (< 35m), finish INSTANTLY.
                if (acc < 35) {
                    console.log("GPS: High precision hit! Resolving instantly.");
                    clearTimeout(timer);
                    finish(position);
                    return;
                }
            },
            (error) => {
                console.warn("GPS: Provider error:", error.code);
                if (error.code === 1) { // Denied
                    clearTimeout(timer);
                    finish(null);
                }
            },
            currentOptions
        );

        // EXTRA SPEED: If we haven't hit <35m but have something decent (<150m) after 1.8s, finish.
        setTimeout(() => {
            if (!hasResolved && bestPosition && bestPosition.coords.accuracy < 150) {
                console.log("GPS: Good enough accuracy found, resolving early.");
                clearTimeout(timer);
                finish(bestPosition);
            }
        }, isAutoTriggered ? 1000 : 1800);
    });
}

function getAddressFromLatLng(lat, lng) {
    if (!googleMapsLoaded) return Promise.resolve(null);
    const geocoder = new google.maps.Geocoder();
    const latlng = { lat: parseFloat(lat), lng: parseFloat(lng) };
    return new Promise((resolve) => {
        geocoder.geocode({ location: latlng }, (results, status) => {
            if (status === "OK") {
                if (results[0]) {
                    resolve(results[0].formatted_address);
                } else {
                    resolve(null);
                }
            } else {
                console.error("Geocoder failed due to: " + status);
                resolve(null);
            }
        });
    });
}

// 3.3. Kết nối Backend (Real API Call)
async function fetchAIResponse(userMessage, userLocation) {
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: userMessage,
                latitude: userLocation ? userLocation.lat : 0.0,
                longitude: userLocation ? userLocation.lng : 0.0
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Map backend response format to frontend format
        // Backend returns: { reply: "...", nearest_stores: [ { ... }, ... ] }
        let stores = [];
        if (data.nearest_stores && data.nearest_stores.length > 0) {
            data.nearest_stores.forEach(store => {
                stores.push({
                    name: store.name,
                    lat: store.lat,
                    lng: store.lng,
                    address: store.address, // Fix: Use 'address' for Map InfoWindows
                    description: store.address, // Maintain 'description' for search list
                    distance_km: store.distance_km,
                    zalo_group_link: store.zalo_group_link,
                    products: store.products || [],
                    staff_zalo: store.staff_zalo || ''
                });
            });
        }

        return {
            text: data.reply,
            map_data: {
                user_marker: userLocation,
                store_markers: stores
            },
            trigger_location: data.trigger_location
        };

    } catch (error) {
        console.error("Error fetching AI response:", error);
        return {
            text: "Xin lỗi, tôi không thể kết nối với máy chủ lúc này. Vui lòng thử lại sau.",
            map_data: null
        };
    }
}

// 3.4. Xử lý Chat (UI Interaction)
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const locationButton = document.getElementById('location-button');

function appendMessage(sender, text) {
    return renderMessage(sender, text, true);
}

function renderMessage(sender, text, save = true) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);

    // Parse Markdown for AI messages, keep plain text for user
    const content = sender === 'ai' ? marked.parse(text) : text;

    messageElement.innerHTML = `<div class="message-bubble">${content}</div>`;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to bottom

    // DON'T save temporary typing indicators to history
    if (save && !text.includes('typing-indicator')) {
        chatHistory.push({ type: 'message', sender, text });
        saveHistory();
    }
    return messageElement;
}

async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (userMessage === '') return;

    appendMessage('user', userMessage);
    chatInput.value = '';

    const typingIndicator = renderMessage('ai', '<div class="typing-indicator"><span></span><span></span><span></span></div>', false); // Don't save this

    // Use cached location if available to prevent repeated prompts
    const location = currentUserLocation || await getUserLocation();

    const aiResponse = await fetchAIResponse(userMessage, location);

    // Remove typing indicator
    if (typingIndicator) {
        typingIndicator.remove();
    }

    if (aiResponse && !aiResponse.trigger_location) {
        appendMessage('ai', aiResponse.text);
    }

    // Render Store Cards
    if (aiResponse.map_data && aiResponse.map_data.store_markers && aiResponse.map_data.store_markers.length > 0) {
        renderStoreCards(aiResponse.map_data.store_markers, true);
    }

    // Auto-trigger location if backend requested it
    if (aiResponse.trigger_location) {
        console.log("Backend requested location trigger.");
        handleLocationCheck(true);
    }
}

function clearHistory() {
    chatHistory = [];
    localStorage.removeItem(getHistoryKey());
    sessionStorage.removeItem(getHistoryKey());
}

function renderStoreCards(stores, save = true) {
    const storeListHtml = document.createElement('div');
    storeListHtml.className = 'store-list';

    // UPDATE CONTEXT TIMER
    window.lastSearchTime = Date.now();

    stores.forEach(store => {
        const card = document.createElement('div');
        card.className = 'store-card';
        card.onclick = () => focusOnStore(store.lat, store.lng, store.name);
        card.style.cursor = 'pointer';

        // Use first product name from filtered results
        const interestName = (store.products && store.products.length > 0) ? store.products[0].name : store.name;

        card.innerHTML = `
            <div class="store-name"><i class="material-icons" style="font-size:18px; vertical-align:text-bottom; margin-right:4px;">store_mall_directory</i>${store.name}</div>
            <div class="store-address"><i class="material-icons" style="font-size:14px; vertical-align:text-bottom; margin-right:4px;">place</i>${store.description || store.address || ''}</div>
            <div class="store-distance"><i class="material-icons" style="font-size:14px; vertical-align:text-bottom; margin-right:4px;">straighten</i>Cách bạn: ${store.distance_km ? store.distance_km.toFixed(1) : '?'} km</div>
            
            ${store.products && store.products.length > 0 ? `
                <div class="product-list">
                    ${store.products.map((p, index) => {
            let finalLink = p.link || '#';
            if (store.zalo_group_link && finalLink !== '#') {
                const separator = finalLink.includes('?') ? '&' : '?';
                finalLink += `${separator}zalo=${encodeURIComponent(store.zalo_group_link)}&product_name=${encodeURIComponent(p.name)}`;
                // FIX: Add staff_zalo if available
                if (p.staff_zalo) {
                    finalLink += `&staff_zalo=${encodeURIComponent(p.staff_zalo)}`;
                }
            } else if (finalLink !== '#') {
                const separator = finalLink.includes('?') ? '&' : '?';
                finalLink += `${separator}product_name=${encodeURIComponent(p.name)}`;
            }

            const isHidden = index >= 3 ? 'display:none;' : '';
            const hiddenClass = index >= 3 ? 'hidden-product' : '';

            return `
                        <div class="product-item ${hiddenClass}" style="${isHidden}">
                            <img src="${p.image_url || 'https://via.placeholder.com/120'}" class="product-img" onerror="this.src='https://via.placeholder.com/120?text=No+Image'">
                            <div class="product-info">
                                <div class="product-name" title="${p.name}">${p.name}</div>
                                <div class="product-price">${p.price}</div>
                                <a href="${finalLink}" target="_self" class="product-link-btn" onclick="event.stopPropagation()"><i class="material-icons" style="font-size:12px; vertical-align:middle; margin-right:2px;">open_in_new</i> Xem sản phẩm</a>
                            </div>
                        </div>`;
        }).join('')}
                    
                    ${store.products.length > 3 ?
                    `<button class="see-more-btn" style="width:100%; margin-top:5px; padding:5px; background:#f0f0f0; border:1px solid #ddd; cursor:pointer;" onclick="revealNextBatch(this)">Xem thêm (${store.products.length - 3} sản phẩm)</button>`
                    : ''}
                </div>
            ` : ''}

            ${store.zalo_group_link ?
                `<br><a href="${store.zalo_group_link}" target="_blank" class="zalo-btn" style="display:inline-block; text-decoration:none; text-align:center;" onclick="trackInterest(event, '${safeEncode(store.name)}', '${safeEncode(store.zalo_group_link)}', '${safeEncode(interestName)}')"><i class="material-icons" style="font-size:16px; vertical-align:middle; margin-right:4px;">group_add</i> Tham gia nhóm săn sale</a>`
                : ''}
        `;
        storeListHtml.appendChild(card);
    });
    chatMessages.appendChild(storeListHtml);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Update map markers (Keep user marker if exists)
    const lat = currentUserLocation ? currentUserLocation.lat : null;
    const lng = currentUserLocation ? currentUserLocation.lng : null;
    updateMap(lat, lng, stores);

    if (save) {
        chatHistory.push({ type: 'stores', data: stores });
        saveHistory();
    }
}




sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// --- 3.5. Xử lý logic lấy vị trí (Refactored - Silent UI) ---
async function handleLocationCheck(isAutoTriggered = false) {
    if (isLocating) return;

    // UI Feedback on button
    const locBtnIcon = locationButton.querySelector('i');
    if (locBtnIcon) {
        locBtnIcon.className = 'material-icons spin-icon';
        locBtnIcon.textContent = 'autorenew';
    }
    locationButton.disabled = true;

    try {
        // If manual click, clear current cached location to force a fresh scan
        if (!isAutoTriggered) {
            currentUserLocation = null;
            sessionStorage.removeItem('last_location');
        }

        const location = await getUserLocation(isAutoTriggered);

        if (location) {
            const acc = parseInt(sessionStorage.getItem('last_location_acc') || '0');
            // Get detailed address for more friendly response
            const address = await getAddressFromLatLng(location.lat, location.lng);
            let addressText = address ? ` tại **${address}**` : '';

            // If accuracy is poor, add a qualifier
            if (acc > 200) {
                addressText += " (vị trí tương đối)";
            }

            // Updated logic: ALWAYS silent for auto-trigger (as requested by user)
            // Manual click (!isAutoTriggered) still shows feedback
            if (!isAutoTriggered) {
                if (!isInVietnam(location.lat, location.lng)) {
                    renderMessage('ai', `<i class="material-icons" style="color:#fbc02d; vertical-align:bottom;">warning</i> **CẢNH BÁO VỊ TRÍ:** Beenet phát hiện bạn đang ở nước ngoài hoặc trình duyệt định vị sai (Vĩ độ: ${location.lat.toFixed(2)}). 
                    Hãy thử tắt/bật lại định vị hoặc nhập tên tỉnh/thành phố để mình tìm chính xác hơn nhé! 🐝`, true);
                } else {
                    const prefix = acc <= 200 ? "Tuyệt vời! 🐝" : "Dạ,";
                    renderMessage('ai', `${prefix} Beenet đã nhận được vị trí của bạn${addressText}. Hãy nói cho mình biết bạn cần tìm gì nhé!`, true);
                }
            }
            // Still mark resolved so we don't nag
            sessionStorage.setItem('locationResolved', 'true');
        } else if (!isAutoTriggered) {
            renderMessage('ai', 'Oops! 😅 Beenet chưa thể lấy được vị trí của bạn. Bạn hãy kiểm tra lại cài đặt trình duyệt giúp mình nhé!', true);
        }
    } catch (err) {
        console.error("Location error:", err);
    } finally {
        if (locBtnIcon) {
            locBtnIcon.className = 'material-icons';
            locBtnIcon.textContent = 'my_location';
        }
        locationButton.disabled = false;
    }
}

locationButton.addEventListener('click', () => {
    renderMessage('user', 'Vị trí của tôi', true);
    handleLocationCheck(false);
});

function removeAllLoadingIndicators() {
    try {
        const indicators = document.querySelectorAll('.typing-indicator');
        indicators.forEach(ind => {
            const msg = ind.closest('.message');
            if (msg) msg.remove();
        });
    } catch (e) {
        console.error("Error cleaning indicators:", e);
    }
}

// --- Initialization & Simple Permission Logic ---
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Fetch Config and Load Google Maps
    try {
        const configRes = await fetch('/api/config');
        const config = await configRes.json();

        if (config.google_maps_api_key) {
            await loadGoogleMaps(config.google_maps_api_key);
            initializeMap();

            // Try to restore cached location
            const cachedLocation = sessionStorage.getItem('last_location');
            if (cachedLocation) {
                currentUserLocation = JSON.parse(cachedLocation);
                updateMap(currentUserLocation.lat, currentUserLocation.lng, null);
            }
        }
    } catch (e) {
        console.error("Initialization error:", e);
    }

    // 2. Process parameters FIRST to determine mode
    const urlParams = new URLSearchParams(window.location.search);
    let shareId = urlParams.get('share');

    // FIX: Check for pending share params (returned from Zalo Login)
    const pendingShareParams = localStorage.getItem('pending_share_params');
    if (pendingShareParams && !shareId) {
        console.log("Found pending share params:", pendingShareParams);
        const pendingParams = new URLSearchParams(pendingShareParams);
        const pendingShareId = pendingParams.get('share');

        if (pendingShareId) {
            shareId = pendingShareId;
            // Restore URL visually
            const newUrl = window.location.pathname + pendingShareParams;
            window.history.replaceState({}, '', newUrl);
            console.log("Restored Share ID from login flow:", shareId);
        }
        localStorage.removeItem('pending_share_params');
    }

    // MODE DECISION: Shared Chat vs Normal Session
    // Robust Check: URL param > sessionStorage fallback (ONLY IF NO LOCAL HISTORY)
    const storage = getStorage();
    const savedHistory = storage.getItem(getHistoryKey());
    const shareIdFallback = sessionStorage.getItem('pending_share_id');

    if (shareIdFallback && !shareId && !savedHistory) {
        console.log("Restoring missing Share ID from fallback:", shareIdFallback);
        shareId = shareIdFallback;
        // Restore URL visually
        const newUrl = new URL(window.location);
        newUrl.searchParams.set('share', shareId);
        window.history.replaceState({}, '', newUrl);
    }

    if (shareId) {
        console.log("🚀 Mode: Shared Chat detected. ID:", shareId);
        // Shared Mode: Directly load shared content
        handleSharedChat(shareId);

        // Safety: Remove any indicators
        removeAllLoadingIndicators();
    } else {
        console.log("👤 Mode: Normal Session. Loading local history.");
        loadHistory(); // Reload local history

        // Safety: Remove any indicators
        removeAllLoadingIndicators();

        // Send welcome message (Only in Normal Mode and if no existing history)
        if (chatHistory.length === 0 && !sessionStorage.getItem('welcomeShown')) {
            setTimeout(() => {
                appendMessage('ai', 'Xin chào! Chào mừng bạn đến với <b>Beenet.vn</b> 🐝✨<br>Hệ thống mua sắm sắm theo vị trí tiện lợi nhất. Mình có thể giúp gì cho bạn hôm nay?');
                sessionStorage.setItem('welcomeShown', 'true');

                // Proactively ask for permission
                if (!currentUserLocation) {
                    setTimeout(() => {
                        const ask = window.confirm("Beenet.vn muốn biết vị trí của bạn để tìm cửa hàng gần nhất nhé?");
                        if (ask) {
                            handleLocationCheck(true);
                        }
                    }, 1500);
                }
            }, 500);
        } else {
            // Already have history or welcome shown, just ensure flag is set
            sessionStorage.setItem('welcomeShown', 'true');
        }
    }




    // --- Share Button Logic ---
    const shareBtn = document.getElementById('share-btn');
    if (shareBtn) {
        shareBtn.addEventListener('click', handleShare);
    }

    const copyShareBtn = document.getElementById('copy-share-link');
    if (copyShareBtn) {
        copyShareBtn.addEventListener('click', () => {
            const input = document.getElementById('share-link-input');
            input.select();
            document.execCommand('copy');
            alert('Đã copy link chia sẻ vào bộ nhớ tạm! 📋');
        });
    }

    const forkChatBtn = document.getElementById('fork-chat-btn');
    if (forkChatBtn) {
        forkChatBtn.addEventListener('click', forkChat);
    }

    // OTHER PARAMS (Proxies, Deep links)
    const productId = urlParams.get('product_interest');
    const productName = urlParams.get('product_name');
    const zaloFromUrl = urlParams.get('zalo');
    const staffZaloFromUrl = urlParams.get('staff_zalo');

    console.log("DEBUG: Init Params - ID:", productId, "Name:", productName, "Zalo:", zaloFromUrl, "Staff Zalo:", staffZaloFromUrl);

    // FIX: Clean corrupted avatar from localStorage if present
    const userPic = localStorage.getItem('user_picture');
    if (userPic && (userPic === '[object Object]' || userPic.includes('object'))) {
        console.warn("Found corrupted user_picture, clearing.");
        localStorage.removeItem('user_picture');
    }
    // FIX: Clean corrupted zalo_code_verifier from localStorage if present
    const zaloCodeVerifier = localStorage.getItem('zalo_code_verifier');
    if (zaloCodeVerifier && (zaloCodeVerifier === '[object Object]' || zaloCodeVerifier.includes('object'))) {
        console.warn("Found corrupted zalo_code_verifier, clearing.");
        localStorage.removeItem('zalo_code_verifier');
    }

    if (productId && productName && !sessionStorage.getItem('productProcessed_' + productId)) {
        // Prevent re-processing on refresh
        sessionStorage.setItem('productProcessed_' + productId, 'true');

        const decodedName = decodeURIComponent(productName);

        // Store in global for Lead Form to use
        window.currentProductContext = decodedName;

        const userName = localStorage.getItem('user_name') || 'Khách';

        // Restore format: [Hệ thống ghi nhận user **Nguyễn Xuân Tài** đang quan tâm sản phẩm: **Tên SP**]
        const systemMessage = `[Hệ thống ghi nhận user ** ${userName} ** đang quan tâm sản phẩm: ** ${decodedName} **]`;
        appendMessage('ai', systemMessage);

        // ADD TO ACCUMULATION ARRAY (when user views product)
        window.interestedProducts.push({
            shopName: '', // Will be filled from API call below
            groupLink: zaloFromUrl || '',
            productName: decodedName,
            timestamp: new Date().toLocaleString(),
            sent: false // Tracking flag
        });
        saveInterestedProducts();
        console.log(`✅ Added to interest list: ${decodedName} (Total: ${window.interestedProducts.length})`);

        // Note: Global function handleDualZaloAction defined at top of file

        // OPTIMIZATION: Use URL params ONLY if we have BOTH Link Group AND Link Staff
        // This prevents the "NULL" Staff ID issue if the URL is old/incomplete
        if (zaloFromUrl && zaloFromUrl.includes('http') && staffZaloFromUrl && staffZaloFromUrl.length > 5) {
            const safeLink = zaloFromUrl.trim();
            const safeStaffZalo = staffZaloFromUrl.trim();
            const productContext = decodedName || "Sản phẩm";

            const msg = encodeURIComponent(`Chào bạn, tôi quan tâm sản phẩm: ${productContext}.Nhờ hỗ trợ!`);
            const staffLink = safeStaffZalo ? `https://zalo.me/${safeStaffZalo}?text=${msg}` : "";

            let buttonsHtml = `<div>Bấm vào link bên dưới để kết nối:</div>`;

            // Button 1: Chat with Staff (REMOVED per user request)


            // Button 2: Join Group (Secondary)
            if (safeLink) {
                buttonsHtml += `<a href="${safeLink}" target="_blank" style="display: block; text-align: center; margin-top: 5px; padding: 8px 16px; background: #e0e0e0; color: #333; text-decoration: none; border-radius: 4px; font-weight: bold;">📢 Vào Nhóm Săn Sale</a>`;
            }

            appendMessage('ai', buttonsHtml);
            return;
        }

        const statusMsg = renderMessage('ai', '<div class="typing-indicator">Đang lấy thông tin shop...</div>', false);
        setTimeout(async () => {
            try {
                // Use standard API path
                const response = await fetch(`${window.location.origin}/api/product-info/${productId}`);
                const data = await response.json();
                console.log("DEBUG: Product Info Data:", data);

                if (data && !data.error) {
                    const shopDisplay = data.shop_name || "Cửa hàng";

                    // UPDATE shop name in accumulated products (match by product name)
                    if (window.interestedProducts.length > 0) {
                        // Find the product that matches this API call's product name
                        const matchingProduct = window.interestedProducts.find(p =>
                            p.productName === decodedName && p.shopName === ''
                        );

                        if (matchingProduct) {
                            matchingProduct.shopName = shopDisplay;
                            saveInterestedProducts();
                            console.log(`📝 Updated shop name for "${decodedName}": ${shopDisplay}`);
                        }
                    }

                    // UPDATE CONTEXT TIMER
                    window.lastSearchTime = Date.now();

                    // FIX: Strict type coercion to prevent [object Object]
                    let finalZalo = "";
                    if (data.zalo_link) {
                        if (typeof data.zalo_link === 'string') {
                            finalZalo = data.zalo_link.trim();
                        } else {
                            // Defensive: try to stringify or fallback
                            try {
                                finalZalo = String(data.zalo_link);
                                if (finalZalo === '[object Object]') finalZalo = "";
                            } catch (e) { finalZalo = ""; }
                        }
                    }

                    console.log("DEBUG: finalZalo =", finalZalo, "| Type:", typeof finalZalo);

                    // CRITICAL FIX: Build message HTML FIRST
                    let buttonsHtml = `<div>Kết nối với shop <b>${shopDisplay}</b>:</div>`;

                    if (finalZalo) {
                        // Use Dual Action Button instead of Markdown Link
                        const safeStaff = data.staff_zalo || '';
                        const pName = data.product_name || data.name || "Sản phẩm";

                        const msg = encodeURIComponent(`Chào bạn, tôi quan tâm sản phẩm: ${pName}. Nhờ hỗ trợ!`);
                        const staffLink = safeStaff ? `https://zalo.me/${safeStaff}?text=${msg}` : "";

                        // Button 1: Chat with Staff (REMOVED per user request)

                        // Button 2: Join Group
                        buttonsHtml += `<a href="${finalZalo}" target="_blank" style="display: block; text-align: center; margin-top: 5px; padding: 8px 16px; background: #e0e0e0; color: #333; text-decoration: none; border-radius: 4px; font-weight: bold;" onclick="trackInterest(event, '${safeEncode(shopDisplay)}', '${safeEncode(finalZalo)}', '${safeEncode(pName)}')">📢 Vào Nhóm Săn Sale</a>`;
                    }

                    // CRITICAL: appendMessage MUST be OUTSIDE if(finalZalo) to always show message
                    appendMessage('ai', buttonsHtml);

                } else {
                    console.error("API Error or Empty Data:", data);
                    appendMessage('ai', "Không tìm thấy thông tin shop cho sản phẩm này.");
                }
            } catch (err) {
                console.error("Error fetching product info:", err);
            } finally {
                if (statusMsg) statusMsg.remove();
            }
        }, 500);

        // CLEARING URL REDIRECT removed as per user request to keep full path/params
        // window.history.replaceState({}, document.title, window.location.pathname);

        // Suppress welcome message for this mission-specific landing
        sessionStorage.setItem('welcomeShown', 'true');
    }

    console.log("Chat initialized V3.5");
});

// Reset persistence only on logout if needed (optional, keeping current localStorage behavior)
window.addEventListener('beforeunload', () => {
    // We NO LONGER clear interestedProducts here to allow navigation persistence
    // Data is stored in localStorage to survive tab closure/crashes
    console.log("💾 Maximum Persistence active: interestedProducts preserved in localStorage.");
});

// --- Helper for Product Pagination ---
function revealNextBatch(btn) {
    const productList = btn.parentElement;
    const hiddenItems = productList.querySelectorAll('.product-item.hidden-product');

    // Convert to array to slice
    const itemsToReveal = Array.from(hiddenItems).slice(0, 3);

    itemsToReveal.forEach(item => {
        item.style.display = ''; // Reset display to default (block/flex)
        item.classList.remove('hidden-product');
    });

    // Check remaining hidden items
    const remaining = hiddenItems.length - itemsToReveal.length;

    if (remaining > 0) {
        btn.innerText = `Xem thêm (${remaining} sản phẩm)`;
    } else {
        btn.style.display = 'none'; // Hide button if no more items
    }
}

// --- LEAD GENERATION TRACKING WITH POPUP ---
let pendingLeadData = null; // Store data while waiting for phone input

// 1. Inject Modal HTML into DOM
function injectPhoneModal() {
    const modalHtml = `
    <!-- Bootstrap Modal for Phone Input -->
    <div class="modal fade" id="phoneInputModal" tabindex="-1" aria-labelledby="phoneModalLabel" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content" style="border-radius: 16px; border: none; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
                <div class="modal-header" style="background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color: white; border-top-left-radius: 16px; border-top-right-radius: 16px;">
                    <h5 class="modal-title" id="phoneModalLabel">🎁 Tham gia nhóm săn sale</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close" onclick="confirmLead('exit')"></button>
                </div>
                <div class="modal-body text-center p-4">
                    <div class="mb-3">
                        <i class="fas fa-gift fa-3x text-warning mb-3"></i>
                        <p class="fs-5 fw-bold" style="color: #333;">Để lại SĐT để được Admins hỗ trợ riêng nhé!</p>
                        <p class="text-muted small">Chúng tôi sẽ add bạn vào nhóm Zalo VIP & Gửi mã giảm giá.</p>
                    </div>
                    <div class="form-floating mb-3">
                        <input type="tel" class="form-control" id="userPhoneInput" placeholder="Số điện thoại của bạn" style="border-radius: 10px;">
                        <label for="userPhoneInput">Nhập số điện thoại (Zalo)</label>
                    </div>
                </div>
                <div class="modal-footer justify-content-between border-0 pb-4">
                    <button type="button" class="btn btn-outline-secondary px-3" style="border-radius: 20px;" onclick="confirmLead('exit')">
                        ❌ Thoát
                    </button>
                    <button type="button" class="btn btn-outline-primary px-3" style="border-radius: 20px;" onclick="confirmLead('skip')">
                        ⏩ Không cần
                    </button>
                    <button type="button" class="btn btn-primary px-4 fw-bold" style="border-radius: 20px; background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); border: none;" onclick="confirmLead('submit')">
                        Xác nhận & Vào nhóm 🚀
                    </button>
                </div>
            </div>
        </div>
    </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Ensure Modal is injected on load
document.addEventListener('DOMContentLoaded', () => {
    injectPhoneModal();
});

// 2. Main Entry Point: Triggered by Button Click
function trackInterest(event, shopNameEncoded, groupLinkEncoded, productNameEncoded) {
    if (event) event.preventDefault(); // Stop immediate navigation

    // Decode Data
    const shopName = decodeURIComponent(shopNameEncoded);
    const groupLink = decodeURIComponent(groupLinkEncoded);
    let productName = decodeURIComponent(productNameEncoded);

    // FIX: If productName is generic "Sản phẩm", try to find real name from array
    if (productName === "Sản phẩm" || productName === shopName) {
        // Search from newest to oldest, prioritizing NOT SENT items
        const candidate = [...window.interestedProducts].reverse().find(p =>
            p.shopName === shopName && !p.sent
        ) || [...window.interestedProducts].reverse().find(p => p.shopName === shopName);

        if (candidate && candidate.productName !== "Sản phẩm") {
            productName = candidate.productName;
            console.log(`🔄 Resolved "${shopName}" -> "${productName}" (Recent Priority)`);
        }
    }

    // ADD TO ACCUMULATION (for direct "Join Group" clicks without viewing product detail)
    // Check if already exists
    const existingIndex = window.interestedProducts.findIndex(p =>
        p.productName === productName
    );

    if (existingIndex === -1) {
        // New product
        window.interestedProducts.push({
            shopName,
            groupLink,
            productName,
            timestamp: new Date().toLocaleString(),
            sent: false // Tracking flag
        });
        saveInterestedProducts();
        console.log(`✅ Added to interest list: ${productName} (Total: ${window.interestedProducts.length})`);
    } else {
        const product = window.interestedProducts[existingIndex];
        if (product.sent) {
            // User wants to interest again - Re-activate!
            product.sent = false;
            product.timestamp = new Date().toLocaleString();
            saveInterestedProducts();
            console.log(`🔄 Re-activated interest for: ${productName}`);
        } else {
            console.log(`⚠️ Product already in queue: ${productName}`);
        }
    }

    // Save to global for Modal callback
    pendingLeadData = {
        shopName,
        groupLink,
        productName
    };

    // FIX 3: CHECK IF MODAL WAS ALREADY SHOWN OR PHONE EXISTS
    const storedPhone = localStorage.getItem('user_phone');
    const modalShown = localStorage.getItem('lead_modal_shown');

    if ((storedPhone && storedPhone !== "None" && storedPhone !== "null") || modalShown === 'true') {
        console.log("📱 Skipping form (Phone exists or Modal already shown once).");
        submitLeadPayload(storedPhone || "None");
        return;
    }

    // Mark as shown immediately so even if they refresh or skip, it won't show again
    localStorage.setItem('lead_modal_shown', 'true');

    // Show Modal (only if no phone stored)
    const modalEl = document.getElementById('phoneInputModal');
    if (typeof bootstrap !== 'undefined' && modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } else {
        // Fallback if Bootstrap not loaded: proceed without phone
        console.warn("Bootstrap Modal not found, skipping phone input.");
        submitLeadPayload(null);
    }
}

// 3. User Decision Handler (Submit or Skip or Exit)
function confirmLead(action) {
    const modalEl = document.getElementById('phoneInputModal');
    const modal = bootstrap.Modal.getInstance(modalEl);

    // ACTION 1: Exit - Close modal and do nothing
    if (action === 'exit') {
        if (modal) modal.hide();
        console.log("❌ User exited modal");
        return;
    }

    // ACTION 2 & 3: Skip or Submit
    let phone = "None"; // Default

    if (action === 'submit') {
        const input = document.getElementById('userPhoneInput');
        if (input && input.value.trim().length > 0) {
            phone = input.value.trim();
            localStorage.setItem('user_phone', phone); // PERSIST
        } else {
            // User clicked Submit but empty? Alert
            alert("Vui lòng nhập số điện thoại hoặc chọn 'Không cần'");
            return; // Stay in modal
        }
    }

    // Hide Modal
    if (modal) modal.hide();

    // Proceed to send data
    submitLeadPayload(phone);
}

// 4. Submit Data & Navigate
async function submitLeadPayload(phone) {
    if (!pendingLeadData) return;

    const { groupLink, shopName, productName } = pendingLeadData;

    // B. Send ALL accumulated products as separate rows
    if (window.interestedProducts.length === 0) {
        console.warn("⚠️ No products in interest list!");
        return;
    }

    try {
        // Collect Context (shared for all products)
        const contextMsgs = chatHistory.filter(item => {
            return item.sender === 'user' || item.type === 'trigger';
        }).slice(-10); // Increase to 10 for better context
        const contextStr = contextMsgs.map(m => m.text).join(" - ");

        // Only send products that haven't been submitted yet
        const unsentProducts = window.interestedProducts.filter(p => !p.sent);

        if (unsentProducts.length === 0) {
            console.log(`ℹ️ All ${window.interestedProducts.length} products already sent previously.`);
        } else {
            console.log(`📤 Submitting ${unsentProducts.length} new products to sheet...`);

            // Send each product as a separate row
            for (const product of unsentProducts) {
                const payload = {
                    user_name: localStorage.getItem('user_name') || "Khách",
                    user_id: localStorage.getItem('session_id') || "guest",
                    product_name: product.productName,
                    shop_name: product.shopName,
                    chat_context: contextStr || "User clicked Interest",
                    phone: phone, // Actual Phone or "None"
                    zalo_contact: phone, // Backward compatibility
                    avatar_url: localStorage.getItem('user_picture') || "",
                    zalo_group_link: product.groupLink,
                    timestamp: product.timestamp
                };

                // Send API (fire and forget)
                fetch('/api/submit-lead', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                }).then(() => {
                    console.log(`✅ Sent: ${product.productName}`);
                    product.sent = true; // Mark as sent in memory
                    saveInterestedProducts(); // Persist the 'sent' state
                }).catch(e => {
                    console.error(`❌ Failed: ${product.productName}`, e);
                });
            }
        }

        console.log(`✅ Submission process complete. Array preserved (Total: ${window.interestedProducts.length}).`);

        // A. ADD AI MESSAGE WITH ZALO LINK (REMOVED per user request as it is redundant)
        /*
        const phoneDisplay = phone && phone !== "None" ? phone : "chưa cung cấp SĐT";
        const aiMessage = `Tuyệt vời! 🐝✨ Beenet đã ghi nhận bạn quan tâm đến **${productName}** tại **${shopName}**.\n\n` +
            `📱 SĐT của bạn: **${phoneDisplay}**\n\n` +
            `🔗 **[Tham gia nhóm Zalo săn sale ngay!](${groupLink})**\n\n` +
            `_Nhóm sẽ tự động mở trong giây lát..._`;

        renderMessage('ai', aiMessage, true);
        */

        // B. OPEN ZALO LINK AFTER DELAY (FIX 1: Ensure message is rendered first)
        setTimeout(() => {
            window.open(groupLink, '_blank');
        }, 800); // 800ms delay to ensure message is visible

    } catch (e) {
        console.error("Tracking Error:", e);
    }

    // Reset
    pendingLeadData = null;
    const phoneInput = document.getElementById('userPhoneInput');
    if (phoneInput) phoneInput.value = ''; // Clear input
}

// --- Sharing & Forking Functions ---

async function handleShare() {
    if (chatHistory.length === 0) {
        alert("Chưa có nội dung gì để chia sẻ bạn ơi! 🐝");
        return;
    }

    const shareBtn = document.getElementById('share-btn');
    const originalContent = shareBtn.innerHTML;
    shareBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';
    shareBtn.disabled = true;

    try {
        const payload = {
            messages: chatHistory,
            user_info: {
                name: localStorage.getItem('user_name') || "Khách",
                avatar: localStorage.getItem('user_picture') || ""
            },
            owner_id: localStorage.getItem('session_id')
        };

        const response = await fetch('/api/share', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("API Share failed");

        const data = await response.json();
        const shareUrl = `${window.location.origin}${window.location.pathname}?share=${data.share_id}`;

        // Show Modal
        const input = document.getElementById('share-link-input');
        input.value = shareUrl;

        const modalEl = document.getElementById('shareModal');
        const modal = new bootstrap.Modal(modalEl);
        modal.show();

    } catch (e) {
        console.error("Sharing error:", e);
        alert("Lỗi khi tạo link chia sẻ. Vui lòng thử lại sau.");
    } finally {
        shareBtn.innerHTML = originalContent;
        shareBtn.disabled = false;
    }
}
// Expose for avatar-display.js
window.handleShare = handleShare;

let sharedChatData = null;

async function handleSharedChat(shareId) {
    console.log("🔗 Loading shared chat:", shareId);

    // Show loading state in chat (DO NOT SAVE TO HISTORY)
    const loadingMsg = renderMessage('ai', '<i>Đang nạp cuộc hội thoại được chia sẻ...</i>', false);

    try {
        const response = await fetch(`/api/share/${shareId}`);
        if (!response.ok) throw new Error("Failed to load shared chat");

        const data = await response.json();
        sharedChatData = data;

        // Clear current view and history placeholder
        chatMessages.innerHTML = '';

        // Render shared messages
        const messages = data.messages || [];
        messages.forEach(item => {
            if (item.type === 'message') {
                // FIX: Auto-heal corrupted history (remove saved loading messages)
                if (item.text.includes('Đang nạp cuộc hội thoại được chia sẻ')) return;
                renderMessage(item.sender, item.text, false);
            } else if (item.type === 'stores') {
                renderStoreCards(item.data, false);
            }
        });

        // Detect Ownership
        const currentSessionId = localStorage.getItem('session_id');
        const isOwner = (data.owner_id && data.owner_id === currentSessionId);

        // Show Shared Mode Banner with original user's info
        const banner = document.getElementById('shared-mode-banner');
        const bannerText = document.getElementById('shared-banner-text');
        const forkBtn = document.getElementById('fork-chat-btn');

        const originalName = data.user_info ? data.user_info.name : 'một người dùng';
        const originalAvatar = data.user_info ? data.user_info.avatar : '';

        let avatarHtml = originalAvatar
            ? `<img src="${originalAvatar}" class="sharer-avatar" alt="Avatar">`
            : `<i class="fas fa-user-circle sharer-avatar" style="font-size: 20px; color: #17a2b8; background: white; border-radius: 50%;"></i>`;

        if (isOwner) {
            bannerText.innerHTML = `⭐ <b>Đây là đoạn chat bạn đã chia sẻ.</b>`;
            if (forkBtn) forkBtn.style.display = 'none'; // No need to fork own chat
        } else {
            bannerText.innerHTML = `Bạn đang xem đoạn chat được chia sẻ từ ${avatarHtml} <b>${originalName}</b>.`;
            if (forkBtn) forkBtn.style.display = 'inline-block';
        }

        banner.style.setProperty('display', 'flex', 'important');

        // Disable Input until "Fork"
        chatInput.disabled = true;
        sendButton.disabled = true;
        locationButton.disabled = true;
        chatInput.placeholder = "Bấm 'Chat tiếp' để tiếp tục cuộc hội thoại này";

    } catch (e) {
        console.error("Load shared chat error:", e);
        loadingMsg.innerHTML = '<div class="message-bubble text-danger">Không thể tải cuộc hội thoại này hoặc link đã hết hạn.</div>';
    }
}

function forkChat() {
    if (!sharedChatData) return;

    // Import messages into current session history
    chatHistory = [...sharedChatData.messages];
    saveHistory();

    // Enable UI
    chatInput.disabled = false;
    sendButton.disabled = false;
    locationButton.disabled = false;
    chatInput.placeholder = "Nhập tin nhắn...";

    // Hide Banner
    const banner = document.getElementById('shared-mode-banner');
    banner.style.setProperty('display', 'none', 'important');

    const originalName = sharedChatData.user_info ? sharedChatData.user_info.name : 'một người dùng';
    appendMessage('ai', `<b>✅ Đã nạp thành công!</b> Bạn có thể tiếp tục cuộc hội thoại của <b>${originalName}</b> từ đây. 🚀`);

    // Clean URL and Session Fallback
    sessionStorage.removeItem('pending_share_id');
    const url = new URL(window.location);
    url.searchParams.delete('share');
    window.history.replaceState({}, '', url);
}

function safeEncode(str) {
    if (!str) return '';
    return encodeURIComponent(str).replace(/'/g, "%27");
}
