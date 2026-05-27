/**
 * permissions.js — Frontend permission guard (Fixed)
 * Fix: applySidebarVisibility xử lý đúng Ca làm việc standalone cho admin
 */

const PERM_KEY  = 'user_permissions';
const ADMIN_KEY = 'user_is_admin';

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

        applySidebarVisibility();
    } catch(e) {
        console.warn('initPermissions error:', e);
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function getPermissions() {
    try { return JSON.parse(sessionStorage.getItem(PERM_KEY) || '[]'); } catch { return []; }
}
function isAdmin()              { return sessionStorage.getItem(ADMIN_KEY) === '1'; }
function hasPermission(perm)    { return isAdmin() || getPermissions().includes(perm); }
function hasAnyPermission(perm) {
    // Cho phép nếu có bất kỳ sub-permission nào của module
    const perms = getPermissions();
    return isAdmin() || perms.some(p => p === perm || p.startsWith(perm + '.'));
}

// ── Áp dụng sidebar visibility ────────────────────────────────────────────────
function applySidebarVisibility() {
    const admin = isAdmin();

    document.querySelectorAll('[data-perm]').forEach(el => {
        const perm = el.getAttribute('data-perm');

        if (perm === '__admin__') {
            // Menu chỉ dành cho admin
            el.style.display = admin ? '' : 'none';
        } else if (el.id === 'menu-schedules-standalone') {
            // Ca làm việc standalone: chỉ hiện với nhân viên có quyền schedules
            // Admin không thấy (đã có trong dropdown Quản lý nhân viên)
            el.style.display = !admin && hasAnyPermission('schedules') ? '' : 'none';
        } else {
            // Menu thường: admin luôn thấy, nhân viên cần có quyền
            el.style.display = admin || hasAnyPermission(perm) ? '' : 'none';
        }
    });
}

// ── Check quyền real-time trước action quan trọng ─────────────────────────────
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
        return true; // fail-open nếu mất kết nối
    }
}

// ── Force logout ──────────────────────────────────────────────────────────────
function handleForceLogout(message) {
    sessionStorage.clear();
    alert('⚠️ ' + message + '\n\nBạn sẽ được chuyển về trang đăng nhập.');
    window.location.href = '/login';
}

// ── Toast thông báo từ chối ───────────────────────────────────────────────────
function showPermissionDenied(message) {
    const toast = document.createElement('div');
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

// ── Polling 30s: phát hiện tk bị vô hiệu hóa hoặc quyền bị thu hồi ──────────
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
            }
        } catch(e) { /* bỏ qua lỗi mạng */ }
    }, 30000);
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await initPermissions();
    startPermissionPolling();
});