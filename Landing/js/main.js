'use strict';

/* ═══════════════════════════════════════════════
   PosPos Landing Page — main.js
   ═══════════════════════════════════════════════ */

// ── 1. Skeleton Loading ─────────────────────────
const skOverlay = document.getElementById('sk-overlay');
window.addEventListener('load', () => {
  setTimeout(() => {
    skOverlay.classList.add('hidden');
    setTimeout(() => { skOverlay.remove(); }, 500);
  }, 900);
});

// ── 2. Dark Mode ────────────────────────────────
const themeToggle = document.getElementById('theme-toggle');
const html = document.documentElement;
const savedTheme = localStorage.getItem('pospos-theme') || 'light';
html.setAttribute('data-theme', savedTheme);

themeToggle.addEventListener('click', () => {
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('pospos-theme', next);
  trackEvent('theme_toggle', { mode: next });
});

// ── 3. Navbar scroll ────────────────────────────
const navbar = document.getElementById('navbar');
const scrollTopBtn = document.getElementById('scroll-top');

function onScroll() {
  const y = window.scrollY;
  navbar.classList.toggle('scrolled', y > 20);
  scrollTopBtn.classList.toggle('visible', y > 400);
  updateStoryProgress();
  rafParallax();
}
window.addEventListener('scroll', onScroll, { passive: true });

// ── 4. Hamburger menu ───────────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('nav-links');
hamburger.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  hamburger.setAttribute('aria-expanded', open);
});
navLinks.querySelectorAll('a').forEach(a =>
  a.addEventListener('click', () => {
    navLinks.classList.remove('open');
    hamburger.setAttribute('aria-expanded', false);
  })
);

// ── 5. Smooth anchor scroll (offset for fixed nav) ──
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const href = a.getAttribute('href');
    if (!href || href === '#') return; // FIX: '#' is not a valid querySelector selector
    const target = document.querySelector(href);
    if (!target) return;
    e.preventDefault();
    const offset = parseInt(getComputedStyle(html).getPropertyValue('--nav-h'), 10) || 68;
    window.scrollTo({ top: target.offsetTop - offset, behavior: 'smooth' });
  });
});

// ── 6. Reveal on scroll ─────────────────────────
const revealObs = new IntersectionObserver(entries => {
  entries.forEach(({ target, isIntersecting }) => {
    if (isIntersecting) { target.classList.add('visible'); revealObs.unobserve(target); }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));

// ── 7. Counter animation ────────────────────────
const counterObs = new IntersectionObserver(entries => {
  entries.forEach(({ target, isIntersecting }) => {
    if (!isIntersecting) return;
    counterObs.unobserve(target);
    const end = parseInt(target.dataset.target, 10);
    const dur = 1600;
    const start = performance.now();
    const tick = now => {
      const ease = 1 - Math.pow(1 - Math.min((now - start) / dur, 1), 3);
      target.textContent = Math.round(ease * end);
      if (ease < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}, { threshold: 0.5 });
document.querySelectorAll('.stat-num').forEach(c => counterObs.observe(c));

// ── 8. Parallax (hero shapes + mockup) ─────────
const parallaxShapes = document.querySelectorAll('[data-parallax]');
const parallaxEl = document.querySelector('[data-parallax-el]');
let ticking = false;

function rafParallax() {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    const y = window.scrollY;
    parallaxShapes.forEach(el => {
      const speed = parseFloat(el.dataset.parallax) || 0.2;
      el.style.transform = `translateY(${y * speed}px)`;
    });
    if (parallaxEl) {
      const speed = parseFloat(parallaxEl.dataset.parallaxEl) || 0.08;
      parallaxEl.style.transform = `translateY(${y * speed}px)`;
    }
    ticking = false;
  });
}

// ── 9. Scrollytelling ───────────────────────────
const storyItems = document.querySelectorAll('.story-item');
const storyFill = document.getElementById('story-fill');
const storySection = document.getElementById('story');

function updateStoryProgress() {
  if (!storySection) return;
  const rect = storySection.getBoundingClientRect();
  const sectionH = storySection.offsetHeight;
  const progress = Math.min(Math.max(-rect.top / (sectionH - window.innerHeight), 0), 1);
  if (storyFill) storyFill.style.height = `${progress * 100}%`;
}

const storyObs = new IntersectionObserver(entries => {
  entries.forEach(({ target, isIntersecting }) => {
    if (isIntersecting) target.classList.add('visible');
  });
}, { threshold: 0.25 });
storyItems.forEach(el => storyObs.observe(el));

// ── 10. Scroll top ──────────────────────────────
scrollTopBtn.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
  trackEvent('scroll_top_click');
});

// ── 11. Mockup bar animation ────────────────────
(function animateBars() {
  const bars = document.querySelectorAll('.mockup-chart .bar');
  if (!bars.length) return;
  setInterval(() => {
    bars.forEach(b => { b.style.height = `${28 + Math.random() * 62}%`; });
  }, 2200);
})();

// ── 12. Behavior Tracking ───────────────────────
const tracked = { scrollDepths: new Set(), clicks: 0 };
// FIX CORS: Set to your real webhook after deploy. Empty = log only (no CORS error).
const WEBHOOK = '';

function trackEvent(name, data = {}) {
  const payload = {
    event: name,
    timestamp: new Date().toISOString(),
    url: location.href,
    referrer: document.referrer,
    ...data,
  };
  console.debug('[PosPos Track]', name, payload);
  if (!WEBHOOK) return;
  // FIX CORS: sendBeacon with Blob text/plain avoids CORS preflight
  try {
    const blob = new Blob([JSON.stringify(payload)], { type: 'text/plain' });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(WEBHOOK, blob);
    } else {
      fetch(WEBHOOK, { method: 'POST', body: blob, keepalive: true }).catch(() => {});
    }
  } catch {}
}

document.addEventListener('click', e => {
  tracked.clicks++;
  const el = e.target.closest('a, button, .feature-card, .testimonial-card, .story-card');
  if (el) {
    const label = (el.textContent?.trim().slice(0, 40)) || el.getAttribute('href') || el.id || 'unknown';
    trackEvent('click', { element: label, total: tracked.clicks });
  }
});

window.addEventListener('scroll', () => {
  const max = document.body.scrollHeight - window.innerHeight;
  if (!max) return;
  const depth = Math.round((window.scrollY / max) * 100);
  const milestone = [25, 50, 75, 100].find(m => depth >= m && !tracked.scrollDepths.has(m));
  if (milestone) {
    tracked.scrollDepths.add(milestone);
    trackEvent('scroll_depth', { percent: milestone });
  }
}, { passive: true });

// ── 13. Subscribe Form ──────────────────────────
const form = document.getElementById('subscribe-form');
const submitBtn = document.getElementById('submit-btn');
const toast = document.getElementById('toast');

const RULES = {
  name:  { validate: v => v.trim().length >= 2, msg: 'Họ và tên phải có ít nhất 2 ký tự.' },
  email: { validate: v => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()), msg: 'Email không hợp lệ.' },
  phone: { validate: v => v === '' || /^(0|\+84)[3-9]\d{8}$/.test(v.replace(/\s/g, '')), msg: 'Số điện thoại không hợp lệ (VD: 0912345678).' },
};

['name', 'email', 'phone'].forEach(f => {
  document.getElementById(`f-${f}`).addEventListener('input', () => {
    const val = document.getElementById(`f-${f}`).value;
    if (RULES[f].validate(val) || (f === 'phone' && val === '')) clearError(f);
  });
});

function showError(f, msg) {
  document.getElementById(`f-${f}`)?.classList.add('error');
  const el = document.getElementById(`err-${f}`);
  if (el) el.textContent = msg;
}
function clearError(f) {
  document.getElementById(`f-${f}`)?.classList.remove('error');
  const el = document.getElementById(`err-${f}`);
  if (el) el.textContent = '';
}
function setLoading(on) {
  submitBtn.disabled = on;
  submitBtn.querySelector('.btn-text').hidden = on;
  submitBtn.querySelector('.btn-loading').hidden = !on;
}
function showToast() {
  toast.hidden = false;
  setTimeout(() => { toast.hidden = true; }, 6000);
}
document.querySelector('.toast-close').addEventListener('click', () => { toast.hidden = true; });

form.addEventListener('submit', async e => {
  e.preventDefault();
  let valid = true;
  ['name', 'email', 'phone'].forEach(f => {
    const val = document.getElementById(`f-${f}`).value;
    if (!RULES[f].validate(val)) { showError(f, RULES[f].msg); valid = false; }
    else clearError(f);
  });
  if (!valid) return;

  setLoading(true);
  const data = {
    name: document.getElementById('f-name').value.trim(),
    email: document.getElementById('f-email').value.trim(),
    phone: document.getElementById('f-phone').value.trim(),
    store_type: document.getElementById('f-store').value,
    timestamp: new Date().toISOString(),
    source: 'pospos_landing',
  };
  trackEvent('form_submit', { store_type: data.store_type });

  try {
    // FIX CORS: send as text/plain Blob (no preflight), fallback to simulate if no webhook
    if (WEBHOOK) {
      const blob = new Blob([JSON.stringify(data)], { type: 'text/plain' });
      navigator.sendBeacon ? navigator.sendBeacon(WEBHOOK, blob) : await fetch(WEBHOOK, { method: 'POST', body: blob, keepalive: true }).catch(() => {});
    }
    await new Promise(r => setTimeout(r, 800));
    form.reset();
    showToast();
    trackEvent('form_success', { email: data.email });
  } catch {
    showError('email', 'Có lỗi xảy ra. Vui lòng thử lại.');
  } finally {
    setLoading(false);
  }
});

// ── 14. Chatbot Widget ──────────────────────────
const KB = [
  {
    keys: ['xin chào', 'hello', 'hi', 'chào', 'alo', 'hey'],
    answer: '👋 Xin chào! Tôi là trợ lý AI của PosPos.\n\nTôi có thể giúp bạn tìm hiểu về:\n• Tính năng hệ thống\n• Cách bắt đầu dùng thử\n• Thông tin kỹ thuật\n• Bảng giá',
    quick: ['Tính năng nổi bật', 'Cách dùng thử', 'Giá cả?', 'Hỗ trợ kỹ thuật'],
  },
  {
    keys: ['tính năng', 'feature', 'có gì', 'làm được gì', 'chức năng'],
    answer: '✨ PosPos có các tính năng chính:\n\n🛒 Bán hàng POS — giao diện cảm ứng, tìm kiếm realtime\n📦 Kho hàng — cảnh báo tồn kho, đề xuất nhập hàng\n🤖 AI Chatbot — phân tích kho, doanh thu tự động\n📊 Báo cáo — doanh thu 7/30/90 ngày\n🏪 Đa chi nhánh — quản lý nhiều shop\n🔒 Bảo mật JWT — rate limiting, audit log',
    quick: ['Chatbot AI hoạt động thế nào?', 'Quản lý kho ra sao?', 'Dùng thử ngay'],
  },
  {
    keys: ['chatbot', 'ai', 'trí tuệ nhân tạo', 'thư ký ảo', 'tự động'],
    answer: '🤖 Chatbot AI của PosPos là "Thư ký ảo" tích hợp sẵn:\n\n• Phân tích tồn kho — cảnh báo hàng < 1/3 ban đầu\n• Đề xuất đặt hàng — dựa trên tốc độ bán 7/30 ngày\n• Báo cáo doanh thu — tổng hợp ngay lập tức\n• Top bán chạy — ranking sản phẩm 30 ngày\n• Tạo đơn nhập hàng tự động qua chat',
    quick: ['Quản lý kho thế nào?', 'Xem demo', 'Dùng thử miễn phí'],
  },
  {
    keys: ['kho', 'tồn kho', 'warehouse', 'inventory', 'nhập hàng', 'hàng hóa'],
    answer: '📦 Quản lý kho với PosPos:\n\n• Theo dõi tồn kho real-time qua WebSocket\n• Cảnh báo tự động khi hàng < 1/3 lượng nhập ban đầu\n• Phân tích tốc độ bán theo tuần/tháng\n• Đề xuất số lượng cần đặt (nhập theo AI)\n• Lịch sử nhập/xuất chi tiết\n• Dự báo ngày hết hàng',
    quick: ['Chatbot AI', 'Báo cáo doanh thu', 'Dùng thử ngay'],
  },
  {
    keys: ['báo cáo', 'report', 'doanh thu', 'revenue', 'thống kê', 'analytics'],
    answer: '📊 Hệ thống báo cáo của PosPos:\n\n• Doanh thu 7/30/90 ngày — cập nhật realtime\n• Số hóa đơn đã thanh toán\n• Công nợ khách hàng tổng hợp\n• Xếp hạng khách hàng VIP\n• Biểu đồ xu hướng bán hàng\n• Celery tự động gửi báo cáo qua email',
    quick: ['Tính năng khác', 'Dùng thử ngay'],
  },
  {
    keys: ['giá', 'price', 'bao nhiêu', 'chi phí', 'phí', 'bảng giá', 'cost'],
    answer: '💰 PosPos cung cấp gói dùng thử:\n\n🎁 30 ngày miễn phí — không cần thẻ tín dụng\n✅ Hỗ trợ thiết lập hoàn toàn miễn phí\n✅ Không cam kết dài hạn\n\nĐể nhận báo giá chính xác theo nhu cầu, vui lòng điền form đăng ký và đội ngũ sẽ liên hệ trong 24 giờ.',
    quick: ['Đăng ký dùng thử', 'Tính năng nổi bật'],
  },
  {
    keys: ['dùng thử', 'trial', 'đăng ký', 'bắt đầu', 'start', 'demo', 'miễn phí'],
    answer: '🚀 Bắt đầu dùng thử PosPos miễn phí:\n\n1️⃣ Điền form đăng ký bên dưới trang\n2️⃣ Đội ngũ liên hệ trong vòng 24 giờ\n3️⃣ Thiết lập hệ thống cho cửa hàng của bạn\n4️⃣ Trải nghiệm 30 ngày không mất phí\n\nBấm nút bên dưới để đến form đăng ký!',
    quick: ['Đến form đăng ký ↓'],
    action: () => { closeChatbot(); setTimeout(() => document.getElementById('subscribe')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300); },
  },
  {
    keys: ['bảo mật', 'security', 'jwt', 'an toàn', 'mã hóa', 'encrypt'],
    answer: '🔒 PosPos áp dụng bảo mật cấp doanh nghiệp:\n\n• JWT Authentication + bcrypt password hashing\n• Rate limiting — chặn brute force tự động\n• Audit log — ghi lại MỌI thao tác với timestamp\n• Prometheus metrics — giám sát 24/7\n• HTTPS only khi deploy production\n• Middleware kiểm tra mọi request',
    quick: ['Thông số kỹ thuật', 'Tính năng khác'],
  },
  {
    keys: ['công nghệ', 'tech', 'stack', 'fastapi', 'python', 'postgresql', 'redis', 'kỹ thuật'],
    answer: '⚙️ Công nghệ xây dựng PosPos:\n\n• Backend: FastAPI 0.119 + Python (async)\n• Database: PostgreSQL + SQLAlchemy 2.0\n• Cache: Redis 5.2\n• Real-time: WebSocket native\n• Auth: JWT (PyJWT 2.10) + bcrypt\n• Tasks: Celery 5.4\n• Monitor: Prometheus\n• Deploy: Docker + Gunicorn + Uvicorn',
    quick: ['Xem bảng thông số ↑', 'Tính năng nổi bật'],
  },
  {
    keys: ['hỗ trợ', 'support', 'liên hệ', 'contact', 'giúp đỡ', 'help'],
    answer: '📞 Liên hệ hỗ trợ PosPos:\n\n📧 Email: hoangthanh29042003@gmail.com\n💻 GitHub: github.com/surp29\n⏰ Phản hồi trong vòng 24 giờ\n\nHoặc điền form đăng ký dùng thử, đội ngũ sẽ chủ động liên hệ và hỗ trợ thiết lập hệ thống cho bạn.',
    quick: ['Đăng ký dùng thử', 'Tính năng nổi bật'],
  },
];

const DEFAULT_ANSWER = {
  answer: '🤔 Tôi chưa hiểu câu hỏi của bạn.\n\nBạn có thể hỏi tôi về:\n• Tính năng của PosPos\n• Cách dùng thử miễn phí\n• Thông tin bảo mật & kỹ thuật\n• Liên hệ hỗ trợ',
  quick: ['Tính năng nổi bật', 'Cách dùng thử', 'Giá cả?'],
};

function findAnswer(msg) {
  const m = msg.toLowerCase().trim();
  return KB.find(item => item.keys.some(k => m.includes(k))) || DEFAULT_ANSWER;
}

// Chatbot state
let chatbotOpen = false;
const cwToggle = document.getElementById('chatbot-toggle');
const cwWindow = document.getElementById('chatbot-window');
const cwMessages = document.getElementById('cw-messages');
const cwQuick = document.getElementById('cw-quick');
const cwInput = document.getElementById('cw-input');
const cwSend = document.getElementById('cw-send');
const cwClose = document.getElementById('cw-close');
const ctBadge = document.getElementById('ct-badge');
const ctOpen = cwToggle.querySelector('.ct-open');
const ctClose = cwToggle.querySelector('.ct-close');

let chatGreeted = false;

function openChatbot() {
  chatbotOpen = true;
  cwWindow.hidden = false;
  cwToggle.setAttribute('aria-expanded', true);
  ctOpen.hidden = true;
  ctClose.hidden = false;
  ctBadge.hidden = true;
  if (!chatGreeted) {
    chatGreeted = true;
    setTimeout(() => addBotMessage('👋 Xin chào! Tôi là trợ lý AI của PosPos.\nTôi có thể tư vấn về tính năng, cách dùng thử và hỗ trợ kỹ thuật.', ['Tính năng nổi bật', 'Cách dùng thử', 'Giá cả?', 'Liên hệ hỗ trợ']), 300);
  }
  trackEvent('chatbot_open');
}

function closeChatbot() {
  chatbotOpen = false;
  cwWindow.hidden = true;
  cwToggle.setAttribute('aria-expanded', false);
  ctOpen.hidden = false;
  ctClose.hidden = true;
}

cwToggle.addEventListener('click', () => { chatbotOpen ? closeChatbot() : openChatbot(); });
cwClose.addEventListener('click', closeChatbot);

function getTime() {
  return new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function addMessage(text, type, time = getTime()) {
  const wrap = document.createElement('div');
  wrap.className = `cw-msg ${type}`;
  wrap.innerHTML = `<div class="cw-bubble">${escHtml(text)}</div><span class="cw-time">${time}</span>`;
  cwMessages.appendChild(wrap);
  cwMessages.scrollTop = cwMessages.scrollHeight;
  return wrap;
}

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

function showTyping() {
  const wrap = document.createElement('div');
  wrap.className = 'cw-msg bot cw-typing';
  wrap.innerHTML = '<div class="cw-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
  cwMessages.appendChild(wrap);
  cwMessages.scrollTop = cwMessages.scrollHeight;
  return wrap;
}

function renderQuick(items, actionFn) {
  cwQuick.innerHTML = '';
  if (!items?.length) return;
  items.forEach(label => {
    const btn = document.createElement('button');
    btn.className = 'cw-qbtn';
    btn.textContent = label;
    btn.addEventListener('click', () => {
      if (label === 'Đến form đăng ký ↓' && actionFn) { actionFn(); return; }
      if (label === 'Xem bảng thông số ↑') { closeChatbot(); document.getElementById('specs')?.scrollIntoView({ behavior: 'smooth' }); return; }
      handleUserMessage(label);
    });
    cwQuick.appendChild(btn);
  });
}

function addBotMessage(text, quickReplies = [], actionFn = null) {
  const typing = showTyping();
  setTimeout(() => {
    typing.remove();
    addMessage(text, 'bot');
    renderQuick(quickReplies, actionFn);
  }, 800 + Math.random() * 400);
}

function handleUserMessage(text) {
  if (!text.trim()) return;
  cwQuick.innerHTML = '';
  addMessage(text, 'user');
  const result = findAnswer(text);
  addBotMessage(result.answer, result.quick, result.action);
  trackEvent('chatbot_message', { query: text.slice(0, 60) });
}

cwSend.addEventListener('click', () => {
  const v = cwInput.value.trim();
  if (!v) return;
  cwInput.value = '';
  handleUserMessage(v);
});
cwInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); cwSend.click(); }
});

// Auto-open chatbot after 8 seconds with a teaser
setTimeout(() => {
  if (!chatbotOpen) {
    ctBadge.hidden = false;
  }
}, 8000);
