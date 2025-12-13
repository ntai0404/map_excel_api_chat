// Override displayUserInfo to show avatar on the RIGHT side
(function () {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        // Override the displayUserInfo function
        window.displayUserInfo = function () {
            const userType = localStorage.getItem('user_type');
            const userName = localStorage.getItem('user_name');
            const userPicture = localStorage.getItem('user_picture');

            const chatHeader = document.querySelector('.p-3.border-bottom.bg-light');
            if (chatHeader && userType) {
                let userInfoHtml;

                if (userType === 'zalo' && userPicture) {
                    // Show avatar for Zalo users
                    userInfoHtml = `
                        <img src="${userPicture}" alt="${userName}" class="rounded-circle" 
                                style="width: 32px; height: 32px; object-fit: cover; border: 2px solid rgba(255,255,255,0.3);">
                        <small style="color: rgba(255,255,255,0.95); font-weight: 500;">${userName || 'User'}</small>
                    `;
                } else if (userType === 'zalo') {
                    // Zalo user without picture
                    userInfoHtml = `
                        <i class="fas fa-user-circle" style="font-size: 32px; color: rgba(255,255,255,0.8);"></i>
                        <small style="color: rgba(255,255,255,0.95); font-weight: 500;">${userName || 'User'}</small>
                    `;
                } else {
                    // Guest user
                    userInfoHtml = `
                        <i class="fas fa-user" style="font-size: 24px; color: rgba(255,255,255,0.8);"></i>
                        <small style="color: rgba(255,255,255,0.95); font-weight: 500;">Khách</small>
                    `;
                }

                let actionBtnHtml = '';

                if (userType === 'zalo') {
                    // Logout button for Zalo users
                    actionBtnHtml = `
                        <button id="logout-btn" class="btn btn-sm ms-2" title="Đăng xuất">
                            <i class="fas fa-sign-out-alt"></i>
                        </button>
                    `;
                } else {
                    // Login button for Guest users
                    actionBtnHtml = `
                        <button id="login-btn" class="btn btn-sm ms-2" title="Đăng nhập">
                            <i class="fas fa-sign-in-alt"></i>
                        </button>
                    `;
                }

                // IMPORTANT: Put "Trợ lý ảo" on LEFT, user info on RIGHT
                // Order: Avatar -> Name -> Action Button
                chatHeader.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center w-100">
                        <h5 class="m-0"><i class="fas fa-robot me-2"></i>Trợ lý ảo</h5>
                        <div class="d-flex align-items-center gap-2">
                            ${userInfoHtml} <!-- Contains Avatar + Name -->
                            ${actionBtnHtml}
                        </div>
                    </div>
                `;

                // Re-attach event listener to the new button
                const logoutBtn = document.getElementById('logout-btn');
                const loginBtn = document.getElementById('login-btn');

                if (logoutBtn) {
                    logoutBtn.addEventListener('click', function () {
                        if (confirm('Bạn có chắc muốn đăng xuất?')) {
                            localStorage.clear();
                            window.location.href = 'login.html?t=' + new Date().getTime();
                        }
                    });
                }

                if (loginBtn) {
                    loginBtn.addEventListener('click', function () {
                        window.location.href = 'login.html?t=' + new Date().getTime();
                    });
                }
            }
        };

        // Also update initializeSession to save user_picture
        const originalInitializeSession = window.initializeSession;
        window.initializeSession = function () {
            const urlParams = new URLSearchParams(window.location.search);
            const sessionId = urlParams.get('session_id');
            const userType = urlParams.get('user_type');
            const userName = urlParams.get('user_name');
            const userPicture = urlParams.get('user_picture');
            const loginTime = urlParams.get('login_time');

            if (sessionId && userType) {
                console.log('New session from URL:', userType);
                localStorage.setItem('session_id', sessionId);
                localStorage.setItem('user_type', userType);
                localStorage.setItem('user_name', decodeURIComponent(userName || ''));
                if (userPicture) {
                    localStorage.setItem('user_picture', decodeURIComponent(userPicture));
                }
                localStorage.setItem('login_time', loginTime || new Date().toISOString());

                // Force refresh of userType variable for subsequent checks
                // window.history.replaceState({}, document.title, window.location.pathname); 
                // Defer history clean up slightly or keep it, but ensure we use the NEW values
            }

            // Call original function if it exists
            if (typeof originalInitializeSession === 'function') {
                originalInitializeSession();
            } else {
                // If original doesn't exist, do the checks here
                const storedUserType = localStorage.getItem('user_type');
                const storedLoginTime = localStorage.getItem('login_time');

                if (!storedUserType || !storedLoginTime) {
                    window.location.href = 'login.html?t=' + new Date().getTime();
                    return false;
                }

                const loginDate = new Date(storedLoginTime);
                const now = new Date();
                const hoursDiff = (now - loginDate) / (1000 * 60 * 60);

                if (hoursDiff >= 24) {
                    localStorage.clear();
                    window.location.href = 'login.html';
                    return false;
                }
            }

            // Display user info
            window.displayUserInfo();

            return true;
        };

        // Call it immediately if we're on index.html
        if (window.location.pathname.includes('index.html') || window.location.pathname === '/') {
            window.initializeSession();
        }
    }
})();
