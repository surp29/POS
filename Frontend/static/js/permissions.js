/**
 * permissions.js — Permission guard + Page redirect
 *
 * Sau khi chuyển tài khoản sang tk không có quyền vào trang hiện tại
 * → tự động redirect tới trang đầu tiên mà tk đó có quyền
 * → nếu không có trang nào → về trang thông báo không có quyền
 */

const PERM_KEY  = 'user_permissions';
const ADMIN_KEY = 'user_is_admin';

// ── Map URL path → permission cần có ─────────────────────────────────────────
const PAGE_PERMISSION_MAP = {
    '/pos':                 'pos',
    '/discount-codes':      'discount_codes',
    '/products':            'products',
    '/product-groups':      'products',       // chung nhóm products
    '/prices':              'prices',
    '/warehouse':           'warehouse',
    '/orders':              'orders',
    '/invoices':            'invoices',
    '/shipping':            'shipping',
    '/general-diary':       'general_diary',
    '/reports':             'reports',
    '/areas-management':    'areas',
    '/shops-management':    'shops',
    // Admin-only pages
    '/customers':           '__admin__',
    '/customers/debts':     '__admin__',
    '/customers/leaderboard':'__admin__',
    '/employees':           '__admin__',
    '/permissions':         '__admin__',
    // Nhân viên + admin
    '/employees/schedules': 'schedules',
};

// Thứ tự ưu tiên redirect khi trang hiện tại không được phép
const REDIRECT_PRIORITY = [
    { path: '/pos',             perm: 'pos'           },
    { path: '/invoices',        perm: 'invoices'      },
    { path: '/orders',          perm: 'orders'        },
    { path: '/general-diary',   perm: 'general_diary' },
    { path: '/products',        perm: 'products'      },
    { path: '/warehouse',       perm: 'warehouse'     },
    { path: '/shipping',        perm: 'shipping'      },
    { path: '/reports',         perm: 'reports'       },
    { path: '/prices',          perm: 'prices'        },
    { path: '/discount-codes',  perm: 'discount_codes'},
    { path: '/areas-management',perm: 'areas'         },
    { path: '/shops-management',perm: 'shops'         },
    { path: '/employees/schedules', perm: 'schedules' },
    { path: '/product-groups',  perm: 'products'      },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
function getPermissions() {
    try { return JSON.parse(sessionStorage.getItem(PERM_KEY) || '[]'); } catch { return []; }
}
function isAdmin()  { return sessionStorage.getItem(ADMIN_KEY) === '1'; }

function hasAnyPermission(perm) {
    if (isAdmin()) return true;
    if (perm === '__admin__') return false;
    const perms = getPermissions();
    return perms.some(p => p === perm || p.startsWith(perm + '.'));
}

function canAccessPage(path) {
    // Normalize path (bỏ trailing slash)
    const p = path.replace(/\/$/, '') || '/';

    // Các trang không cần kiểm tra
    if (p === '/' || p === '/login' || p === '/logout') return true;

    const requiredPerm = PAGE_PERMISSION_MAP[p];
    if (!requiredPerm) return true; // Không có trong map → cho phép

    if (requiredPerm === '__admin__') return isAdmin();
    return hasAnyPermission(requiredPerm);
}

function findFirstAllowedPage() {
    if (isAdmin()) return null; // Admin không cần redirect

    for (const { path, perm } of REDIRECT_PRIORITY) {
        if (hasAnyPermission(perm)) return path;
    }
    return null; // Không có trang nào có quyền
}

// ── Redirect nếu không có quyền vào trang hiện tại ───────────────────────────
function checkCurrentPageAccess() {
    const currentPath = window.location.pathname;

    // Bỏ qua login/logout
    if (currentPath === '/login' || currentPath === '/logout') return;

    if (canAccessPage(currentPath)) return; // Có quyền → OK

    // Không có quyền → tìm trang phù hợp để redirect
    const redirectTo = findFirstAllowedPage();

    if (redirectTo) {
        showRedirectNotice(currentPath, redirectTo);
    } else {
        // Không có trang nào có quyền → hiện thông báo
        showNoPermissionPage();
    }
}

// ── Hiện thông báo redirect với countdown ────────────────────────────────────
function showRedirectNotice(fromPath, toPath) {
    // Tạo overlay
    const overlay = document.createElement('div');
    overlay.id = 'perm-redirect-overlay';
    overlay.style.cssText = [
        'position:fixed', 'inset:0',
        'background:rgba(15,23,42,0.85)',
        'display:flex', 'align-items:center', 'justify-content:center',
        'z-index:99998', 'font-family:var(--font-family,sans-serif)'
    ].join(';');

    overlay.innerHTML = `
        <div style="background:white;border-radius:16px;padding:36px 40px;max-width:420px;
                    text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.4);">
            <div style="width:64px;height:64px;background:#fff3cd;border-radius:50%;
                        display:flex;align-items:center;justify-content:center;
                        margin:0 auto 16px;font-size:28px;">
                🔀
            </div>
            <h3 style="margin:0 0 8px;color:#1e293b;font-size:1.2em;">Chuyển trang tự động</h3>
            <p style="color:#64748b;margin:0 0 6px;font-size:0.95em;">
                Tài khoản hiện tại không có quyền truy cập trang này.
            </p>
            <p style="color:#3b82f6;font-weight:600;margin:0 0 20px;font-size:0.9em;">
                Đang chuyển tới trang phù hợp...
            </p>
            <div style="background:#f1f5f9;border-radius:8px;padding:10px 16px;
                        color:#475569;font-size:0.85em;margin-bottom:20px;">
                → <strong>${toPath}</strong>
            </div>
            <div style="display:flex;gap:10px;justify-content:center;">
                <button id="perm-redirect-now"
                        style="background:#3b82f6;color:white;border:none;padding:10px 20px;
                               border-radius:8px;cursor:pointer;font-size:0.95em;font-weight:600;">
                    Chuyển ngay
                </button>
                <button id="perm-redirect-cancel"
                        style="background:#f1f5f9;color:#475569;border:none;padding:10px 20px;
                               border-radius:8px;cursor:pointer;font-size:0.95em;">
                    Ở lại (<span id="perm-countdown">3</span>s)
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Countdown 3s rồi tự redirect
    let count = 3;
    const timer = setInterval(() => {
        count--;
        const el = document.getElementById('perm-countdown');
        if (el) el.textContent = count;
        if (count <= 0) {
            clearInterval(timer);
            window.location.href = toPath;
        }
    }, 1000);

    // Nút chuyển ngay
    document.getElementById('perm-redirect-now').onclick = () => {
        clearInterval(timer);
        window.location.href = toPath;
    };

    // Nút ở lại (hủy countdown nhưng vẫn hiện overlay)
    document.getElementById('perm-redirect-cancel').onclick = () => {
        clearInterval(timer);
        overlay.remove();
        // Vẫn redirect về trang được phép sau khi user xem xong
        showPermDeniedBanner(toPath);
    };
}

// ── Banner nhỏ thông báo không có quyền (sau khi bấm "Ở lại") ────────────────
function showPermDeniedBanner(redirectTo) {
    const banner = document.createElement('div');
    banner.style.cssText = [
        'position:fixed', 'top:0', 'left:0', 'right:0',
        'background:#fef3c7', 'color:#92400e',
        'padding:12px 20px',
        'display:flex', 'align-items:center', 'justify-content:space-between',
        'z-index:9999', 'font-size:0.9em', 'box-shadow:0 2px 8px rgba(0,0,0,0.15)'
    ].join(';');
    banner.innerHTML = `
        <span>⚠️ Tài khoản hiện tại không có quyền truy cập trang này.
              Vui lòng chuyển sang trang được phép.</span>
        <button onclick="window.location.href='${redirectTo}'"
                style="background:#92400e;color:white;border:none;padding:6px 14px;
                       border-radius:6px;cursor:pointer;font-weight:600;margin-left:12px;">
            Đi tới ${redirectTo}
        </button>
    `;
    document.body.insertBefore(banner, document.body.firstChild);
}

// ── Trang không có quyền nào ──────────────────────────────────────────────────
function showNoPermissionPage() {
    document.body.innerHTML = `
        <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;
                    background:#f8fafc;font-family:sans-serif;">
            <div style="text-align:center;padding:40px;">
                <div style="font-size:4em;margin-bottom:16px;">🔒</div>
                <h2 style="color:#1e293b;margin:0 0 8px;">Tài khoản chưa được phân quyền</h2>
                <p style="color:#64748b;margin:0 0 24px;">
                    Tài khoản của bạn chưa được cấp quyền truy cập bất kỳ chức năng nào.<br>
                    Vui lòng liên hệ quản trị viên để được phân quyền.
                </p>
                <button onclick="window.location.href='/login'"
                        style="background:#3b82f6;color:white;border:none;padding:12px 28px;
                               border-radius:8px;cursor:pointer;font-size:1em;font-weight:600;">
                    Đăng xuất & Đăng nhập lại
                </button>
            </div>
        </div>`;
}

// ── Load permissions từ server ────────────────────────────────────────────────
async function initPermissions() {
    try {
        const token = sessionStorage.getItem('access_token');
        if (!token) return;

        const res = await fetch(window.BACKEND_URL + '/api/permissions/my', {
            headers: { Authorization: 'Bearer ' + token }
        });

        if (res.status === 401) {
            handleForceLogout('Tài khoản đã bị vô hiệu hóa hoặc phiên đăng nhập hết hạn.');
            return;
        }
        if (!res.ok) return;

        const data = await res.json();
        sessionStorage.setItem(PERM_KEY,  JSON.stringify(data.permissions || []));
        sessionStorage.setItem(ADMIN_KEY, data.is_admin ? '1' : '0');

        // Áp dụng sidebar
        applySidebarVisibility();

        // Kiểm tra trang hiện tại có được phép không
        checkCurrentPageAccess();

    } catch(e) {
        console.warn('initPermissions error:', e);
    }
}

// ── Sidebar visibility ────────────────────────────────────────────────────────
function applySidebarVisibility() {
    const admin = isAdmin();
    document.querySelectorAll('[data-perm]').forEach(el => {
        const perm = el.getAttribute('data-perm');
        if (perm === '__admin__') {
            el.style.display = admin ? '' : 'none';
        } else if (el.id === 'menu-schedules-standalone') {
            el.style.display = !admin && hasAnyPermission('schedules') ? '' : 'none';
        } else {
            el.style.display = admin || hasAnyPermission(perm) ? '' : 'none';
        }
    });
}

// ── Check quyền real-time trước action ───────────────────────────────────────
async function checkPermissionOrAlert(permission) {
    try {
        const token = sessionStorage.getItem('access_token');
        const res = await fetch(`${window.BACKEND_URL}/api/permissions/check/${permission}`, {
            headers: { Authorization: 'Bearer ' + token }
        });
        if (res.status === 401) {
            handleForceLogout('Tài khoản của bạn đã bị vô hiệu hóa.');
            return false;
        }
        const data = await res.json();
        if (!data.allowed) {
            showPermissionDenied(data.message || 'Bạn không có quyền thực hiện chức năng này.');
            return false;
        }
        return true;
    } catch(e) {
        console.warn('checkPermission error:', e);
        return true;
    }
}

// ── Force logout ──────────────────────────────────────────────────────────────
function handleForceLogout(message) {
    sessionStorage.clear();
    // Nếu đang ở trang login thì không cần hiện overlay
    if (window.location.pathname === '/login') return;

    const overlay = document.createElement('div');
    overlay.style.cssText = [
        'position:fixed','inset:0','z-index:999999',
        'background:rgba(15,23,42,0.92)',
        'display:flex','align-items:center','justify-content:center',
        'font-family:var(--font-family,sans-serif)'
    ].join(';');
    overlay.innerHTML = `
        <div style="background:#fff;border-radius:16px;padding:40px 36px;max-width:400px;
                    width:90%;text-align:center;box-shadow:0 24px 64px rgba(0,0,0,0.5);">
            <div style="width:72px;height:72px;background:#fef2f2;border-radius:50%;
                        display:flex;align-items:center;justify-content:center;
                        margin:0 auto 20px;font-size:32px;">🔒</div>
            <h3 style="margin:0 0 10px;color:#1e293b;font-size:1.15em;">Phiên đăng nhập kết thúc</h3>
            <p style="color:#64748b;margin:0 0 24px;font-size:0.92em;line-height:1.6;">${message}</p>
            <div style="width:100%;height:4px;background:#f1f5f9;border-radius:4px;overflow:hidden;margin-bottom:16px;">
                <div id="_fl_bar" style="height:100%;background:#ef4444;border-radius:4px;
                                         width:100%;transition:width 3s linear;"></div>
            </div>
            <p style="color:#94a3b8;font-size:0.82em;margin:0 0 20px;">
                Tự động chuyển về trang đăng nhập...
            </p>
            <button onclick="window.location.href='/login'"
                    style="background:#3b82f6;color:#fff;border:none;padding:11px 28px;
                           border-radius:8px;cursor:pointer;font-size:0.95em;font-weight:600;">
                Đăng nhập lại ngay
            </button>
        </div>`;
    document.body.appendChild(overlay);
    // Kích hoạt animation thanh đếm ngược
    requestAnimationFrame(() => {
        const bar = document.getElementById('_fl_bar');
        if (bar) bar.style.width = '0%';
    });
    setTimeout(() => { window.location.href = '/login'; }, 3000);
}

// ── Toast permission denied ───────────────────────────────────────────────────
function showPermissionDenied(message) {
    const existing = document.getElementById('perm-toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.id = 'perm-toast';
    toast.style.cssText = [
        'position:fixed', 'top:20px', 'left:50%', 'transform:translateX(-50%)',
        'background:#e53e3e', 'color:white', 'padding:14px 24px', 'border-radius:8px',
        'box-shadow:0 4px 20px rgba(0,0,0,0.3)', 'z-index:99999',
        'font-weight:600', 'font-size:0.95em', 'max-width:480px', 'text-align:center'
    ].join(';');
    toast.textContent = '🚫 ' + message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── Polling 30s ───────────────────────────────────────────────────────────────
let _pollInterval = null;
function startPermissionPolling() {
    if (_pollInterval) return;
    _pollInterval = setInterval(async () => {
        try {
            const token = sessionStorage.getItem('access_token');
            if (!token) return;
            const res = await fetch(window.BACKEND_URL + '/api/permissions/my', {
                headers: { Authorization: 'Bearer ' + token }
            });
            if (res.status === 401) {
                clearInterval(_pollInterval);
                handleForceLogout('Tài khoản của bạn đã bị vô hiệu hóa bởi quản trị viên.');
            } else if (res.ok) {
                const data = await res.json();
                sessionStorage.setItem(PERM_KEY,  JSON.stringify(data.permissions || []));
                sessionStorage.setItem(ADMIN_KEY, data.is_admin ? '1' : '0');
                applySidebarVisibility();
                // Kiểm tra lại trang hiện tại sau mỗi lần poll
                // (Trường hợp admin thu hồi quyền của trang đang mở)
                checkCurrentPageAccess();
            }
        } catch(e) { /* bỏ qua lỗi mạng */ }
    }, 30000);
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await initPermissions();
    startPermissionPolling();
});