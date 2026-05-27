/**
 * session_manager.js
 *
 * Logic:
 *  - Token TTL = 30 phút (server config)
 *  - Mỗi khi user có activity → reset idle timer
 *  - Khi còn 5 phút hết hạn token + user đang active → gọi /api/auth/refresh
 *  - Khi idle >= 60 phút → logout tự động
 *  - Khi tab/window focus lại → kiểm tra token còn hạn không
 */

(function() {
    'use strict';

    const IDLE_LOGOUT_MS    = 60 * 60 * 1000;   // 60 phút idle → logout
    const REFRESH_BEFORE_MS = 5  * 60 * 1000;   // Refresh khi còn 5 phút hết hạn
    const CHECK_INTERVAL_MS = 60 * 1000;          // Kiểm tra mỗi 60 giây
    const TOKEN_TTL_MS      = 30 * 60 * 1000;    // Token TTL 30 phút (khớp server)

    let lastActivityTime = Date.now();
    let tokenIssuedTime  = Date.now();
    let checkTimer       = null;
    let isRefreshing     = false;

    // ── Track activity ──────────────────────────────────────────────────────
    const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];

    function resetActivity() {
        lastActivityTime = Date.now();
    }

    ACTIVITY_EVENTS.forEach(evt => {
        document.addEventListener(evt, resetActivity, { passive: true });
    });

    // ── Helpers ─────────────────────────────────────────────────────────────
    function getToken() {
        return sessionStorage.getItem('access_token');
    }

    function getIdleMs() {
        return Date.now() - lastActivityTime;
    }

    function getTokenAgeMs() {
        return Date.now() - tokenIssuedTime;
    }

    function isLoggedIn() {
        return !!getToken() && !window.location.pathname.includes('/login');
    }

    function forceLogout(reason) {
        sessionStorage.clear();
        const msg = reason || 'Phiên làm việc đã hết hạn.';
        // Hiện thông báo trước khi redirect
        const overlay = document.createElement('div');
        overlay.style.cssText = [
            'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.7)',
            'display:flex', 'align-items:center', 'justify-content:center',
            'z-index:999999', 'font-family:sans-serif'
        ].join(';');
        overlay.innerHTML = `
            <div style="background:white;border-radius:12px;padding:32px;max-width:360px;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,0.3);">
                <i class="fas fa-clock" style="font-size:3em;color:#e53e3e;margin-bottom:12px;display:block;"></i>
                <h3 style="margin:0 0 8px;color:#1a202c;">Phiên làm việc kết thúc</h3>
                <p style="color:#718096;margin:0 0 20px;">${msg}</p>
                <button onclick="window.location.href='/login'"
                        style="background:#3b82f6;color:white;border:none;padding:10px 24px;
                               border-radius:8px;font-size:1em;cursor:pointer;font-weight:600;">
                    Đăng nhập lại
                </button>
            </div>`;
        document.body.appendChild(overlay);
        setTimeout(() => { window.location.href = '/login'; }, 4000);
    }

    // ── Refresh token ────────────────────────────────────────────────────────
    async function refreshToken() {
        if (isRefreshing) return;
        const token = getToken();
        if (!token) return;

        isRefreshing = true;
        try {
            const res = await fetch(window.BACKEND_URL + '/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type':  'application/json',
                    'Authorization': 'Bearer ' + token,
                },
            });

            if (res.ok) {
                const data = await res.json();
                sessionStorage.setItem('access_token', data.access_token);
                tokenIssuedTime = Date.now();
                console.info('[Session] Token refreshed thành công');
            } else if (res.status === 401) {
                forceLogout('Token đã hết hạn. Vui lòng đăng nhập lại.');
            }
        } catch (e) {
            console.warn('[Session] Refresh thất bại (mạng):', e);
        } finally {
            isRefreshing = false;
        }
    }

    // ── Main check loop ──────────────────────────────────────────────────────
    function checkSession() {
        if (!isLoggedIn()) return;

        const idleMs    = getIdleMs();
        const tokenAge  = getTokenAgeMs();
        const timeLeft  = TOKEN_TTL_MS - tokenAge;

        // 1. Idle quá 60 phút → logout
        if (idleMs >= IDLE_LOGOUT_MS) {
            console.info('[Session] Idle 60 phút → tự động đăng xuất');
            forceLogout('Bạn đã không hoạt động trong 60 phút. Vui lòng đăng nhập lại.');
            return;
        }

        // 2. Token sắp hết hạn (còn < 5 phút) + user đang active → refresh
        if (timeLeft < REFRESH_BEFORE_MS && timeLeft > 0 && idleMs < IDLE_LOGOUT_MS) {
            console.info(`[Session] Token còn ${Math.round(timeLeft/1000)}s → refresh`);
            refreshToken();
        }

        // 3. Token đã hết hạn hoàn toàn → logout
        if (timeLeft <= 0) {
            forceLogout('Token đã hết hạn. Vui lòng đăng nhập lại.');
        }
    }

    // ── Khởi động ────────────────────────────────────────────────────────────
    function start() {
        // Đặt tokenIssuedTime từ sessionStorage nếu có lưu
        const storedIssued = sessionStorage.getItem('token_issued_at');
        if (storedIssued) {
            tokenIssuedTime = parseInt(storedIssued, 10);
        } else {
            tokenIssuedTime = Date.now();
            sessionStorage.setItem('token_issued_at', tokenIssuedTime);
        }

        // Chạy check ngay và mỗi 60s
        checkTimer = setInterval(checkSession, CHECK_INTERVAL_MS);
        checkSession();
    }

    // ── Khi tab focus lại → kiểm tra ngay ────────────────────────────────────
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible' && isLoggedIn()) {
            checkSession();
        }
    });

    // ── Reset token time khi login/switch account ─────────────────────────────
    // Gọi hàm này sau khi lưu access_token mới
    window.resetTokenIssuedTime = function() {
        tokenIssuedTime = Date.now();
        sessionStorage.setItem('token_issued_at', tokenIssuedTime);
        lastActivityTime = Date.now();
    };

    // ── Start khi trang load ─────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            if (isLoggedIn()) start();
        });
    } else {
        if (isLoggedIn()) start();
    }

})();