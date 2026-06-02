/**
 * session_manager.js
 *
 * Định nghĩa "hoạt động" (không tính là treo máy):
 *   ✅ Click chuột / bấm nút
 *   ✅ Gõ bàn phím
 *   ✅ Cuộn chuột (scroll)
 *   ✅ Touch (mobile)
 *   ✅ Chuyển trang (navigation)
 *
 * KHÔNG tính là hoạt động:
 *   ❌ Di chuột (mousemove) — chỉ move mà không bấm/cuộn
 *   ❌ Tab không được focus (visibilitychange)
 *
 * Logic chính:
 *   - Token TTL = 30 phút → auto refresh khi còn 5 phút + user đang active
 *   - Idle ≥ 60 phút (không click/gõ/scroll) → tự động logout
 */

(function () {
    'use strict';

    const IDLE_LOGOUT_MS    = 60 * 60 * 1000;  // 60 phút không tương tác → logout
    const REFRESH_BEFORE_MS =  5 * 60 * 1000;  // Refresh khi token còn < 5 phút
    const CHECK_INTERVAL_MS = 60 * 1000;        // Kiểm tra mỗi 60 giây
    const TOKEN_TTL_MS      = 30 * 60 * 1000;  // Token TTL 30 phút (khớp server)

    let lastActivityTime = Date.now();
    let tokenIssuedTime  = Date.now();
    let checkTimer       = null;
    let isRefreshing     = false;

    // ── Các sự kiện tính là "hoạt động thực sự" ────────────────────────────
    // mousemove bị loại bỏ — di chuột đơn thuần không phải tương tác có ý nghĩa
    const ACTIVITY_EVENTS = [
        'mousedown',    // bấm nút chuột
        'click',        // click element
        'keydown',      // gõ bàn phím
        'scroll',       // cuộn trang / cuộn trong element
        'touchstart',   // chạm màn hình (mobile)
        'touchend',     // nhả chạm (mobile)
        'wheel',        // cuộn bằng wheel chuột
    ];

    function resetActivity() {
        lastActivityTime = Date.now();
    }

    // Đăng ký trên document (bắt cả bubble từ mọi element)
    ACTIVITY_EVENTS.forEach(function (evt) {
        document.addEventListener(evt, resetActivity, { passive: true, capture: true });
    });

    // ── Chuyển trang cũng tính là hoạt động ───────────────────────────────
    // Khi Flask navigate sang trang mới, DOMContentLoaded sẽ fire
    // → reset lastActivityTime
    document.addEventListener('DOMContentLoaded', function () {
        resetActivity();
    });

    // History navigation (nếu dùng SPA hoặc pushState)
    window.addEventListener('popstate', resetActivity);

    // ── Helpers ────────────────────────────────────────────────────────────
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

    // ── Force logout với overlay thông báo ─────────────────────────────────
    function forceLogout(reason) {
        if (document.getElementById('_session_logout_overlay')) return; // tránh gọi 2 lần
        sessionStorage.clear();

        var overlay = document.createElement('div');
        overlay.id  = '_session_logout_overlay';
        overlay.style.cssText = [
            'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.75)',
            'display:flex', 'align-items:center', 'justify-content:center',
            'z-index:999999', 'font-family:sans-serif'
        ].join(';');
        overlay.innerHTML = '<div style="background:white;border-radius:14px;padding:36px 40px;'
            + 'max-width:380px;text-align:center;box-shadow:0 12px 48px rgba(0,0,0,0.35);">'
            + '<i class="fas fa-clock" style="font-size:3em;color:#e53e3e;display:block;margin-bottom:14px;"></i>'
            + '<h3 style="margin:0 0 10px;color:#1a202c;font-size:1.2em;">Phiên làm việc kết thúc</h3>'
            + '<p style="color:#718096;margin:0 0 22px;line-height:1.5;">' + (reason || 'Phiên đăng nhập đã hết hạn.') + '</p>'
            + '<button onclick="window.location.href=\'/login\'" '
            + 'style="background:#3b82f6;color:white;border:none;padding:11px 28px;'
            + 'border-radius:8px;font-size:1em;cursor:pointer;font-weight:600;">'
            + 'Đăng nhập lại</button>'
            + '</div>';
        document.body.appendChild(overlay);
        setTimeout(function () { window.location.href = '/login'; }, 4000);
    }

    // ── Refresh token ───────────────────────────────────────────────────────
    async function refreshToken() {
        if (isRefreshing) return;
        var token = getToken();
        if (!token) return;

        isRefreshing = true;
        try {
            var res = await fetch(window.BACKEND_URL + '/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type':  'application/json',
                    'Authorization': 'Bearer ' + token,
                },
            });
            if (res.ok) {
                var data = await res.json();
                sessionStorage.setItem('access_token', data.access_token);
                tokenIssuedTime = Date.now();
                sessionStorage.setItem('token_issued_at', String(tokenIssuedTime));
                console.info('[Session] Token refreshed OK, TTL reset 30 phút');
            } else if (res.status === 401) {
                forceLogout('Token đã hết hạn. Vui lòng đăng nhập lại.');
            }
        } catch (e) {
            console.warn('[Session] Không thể refresh token (lỗi mạng):', e);
        } finally {
            isRefreshing = false;
        }
    }

    // ── Vòng kiểm tra chính ─────────────────────────────────────────────────
    function checkSession() {
        if (!isLoggedIn()) return;

        var idleMs   = getIdleMs();
        var tokenAge = getTokenAgeMs();
        var timeLeft = TOKEN_TTL_MS - tokenAge;

        // Debug log (bỏ comment để debug)
        // console.debug('[Session] idle=' + Math.round(idleMs/1000) + 's, tokenLeft=' + Math.round(timeLeft/1000) + 's');

        // 1. Idle ≥ 60 phút → logout
        if (idleMs >= IDLE_LOGOUT_MS) {
            forceLogout('Bạn đã không bấm, gõ hoặc cuộn trong 60 phút.\nVui lòng đăng nhập lại.');
            return;
        }

        // 2. Token sắp hết hạn VÀ user đang active → refresh
        if (timeLeft < REFRESH_BEFORE_MS && timeLeft > 0) {
            console.info('[Session] Token còn ' + Math.round(timeLeft / 1000) + 's → refresh');
            refreshToken();
        }

        // 3. Token đã hết hạn hoàn toàn → logout
        if (timeLeft <= 0) {
            forceLogout('Token đã hết hạn. Vui lòng đăng nhập lại.');
        }
    }

    // ── Khởi động ───────────────────────────────────────────────────────────
    function start() {
        var stored = sessionStorage.getItem('token_issued_at');
        tokenIssuedTime = stored ? parseInt(stored, 10) : Date.now();
        if (!stored) {
            sessionStorage.setItem('token_issued_at', String(tokenIssuedTime));
        }
        // Đặt lastActivityTime = now khi trang vừa load (chuyển trang = active)
        lastActivityTime = Date.now();

        checkTimer = setInterval(checkSession, CHECK_INTERVAL_MS);
        checkSession(); // kiểm tra ngay lập tức
    }

    // ── Tab được focus lại → kiểm tra ngay ────────────────────────────────
    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible' && isLoggedIn()) {
            checkSession();
        }
    });

    // ── Public API ──────────────────────────────────────────────────────────
    // Gọi sau khi lưu token mới (login / switch account)
    window.resetTokenIssuedTime = function () {
        tokenIssuedTime  = Date.now();
        lastActivityTime = Date.now();
        sessionStorage.setItem('token_issued_at', String(tokenIssuedTime));
    };

    // Gọi thủ công nếu muốn reset idle (vd: sau khi hoàn tất form dài)
    window.resetIdleTimer = function () {
        lastActivityTime = Date.now();
    };

    // ── Start ───────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            if (isLoggedIn()) start();
        });
    } else {
        if (isLoggedIn()) start();
    }

})();