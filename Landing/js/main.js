'use strict';

/* ═══════════════════════════════════════════════
   PosPos Landing — main.js
   ═══════════════════════════════════════════════ */

// Feature detection
const hasIO = typeof IntersectionObserver !== 'undefined';

// ── 1. Skeleton Loading ─────────────────────────
const skOverlay = document.getElementById('sk-overlay');
window.addEventListener('load', () => {
  setTimeout(() => {
    const mainEl = document.querySelector('main');
    const footerEl = document.querySelector('footer');
    if (mainEl) mainEl.style.visibility = 'visible';
    if (footerEl) footerEl.style.visibility = 'visible';
    skOverlay.classList.add('out');
    setTimeout(() => skOverlay.remove(), 600);
  }, 300);
});

// ── 2. Dark Mode ────────────────────────────────
const html = document.documentElement;
const themeToggle = document.getElementById('theme-toggle');
let saved = 'light';
try { saved = localStorage.getItem('pospos-theme') || 'light'; } catch {}
html.setAttribute('data-theme', saved);

themeToggle.addEventListener('click', () => {
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  try { localStorage.setItem('pospos-theme', next); } catch {}
  trackEvent('theme_toggle', { mode: next });
});

// ── 3. Navbar + scroll top ───────────────────────
const scrollTopBtn = document.getElementById('scroll-top');
const storySection = document.getElementById('story');
const storyFill = document.getElementById('story-fill');

// Cache story height; reset on resize to avoid stale value
let storySectionH = 0;
window.addEventListener('resize', () => { storySectionH = 0; }, { passive: true });

// rAF throttle: updateStoryProgress runs at most once per animation frame
let scrollRafId = 0;
function onScroll() {
  scrollTopBtn.classList.toggle('visible', window.scrollY > 400);
  if (!scrollRafId) {
    scrollRafId = requestAnimationFrame(() => {
      scrollRafId = 0;
      updateStoryProgress();
    });
  }
}
window.addEventListener('scroll', onScroll, { passive: true });

scrollTopBtn.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
  trackEvent('scroll_top_click');
});

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
    hamburger.setAttribute('aria-expanded', 'false');
  })
);

// ── 5. Smooth anchor scroll ──────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const href = a.getAttribute('href');
    if (!href || href === '#') return;
    const target = document.querySelector(href);
    if (!target) return;
    e.preventDefault();
    const navH = parseInt(getComputedStyle(html).getPropertyValue('--nav-h'), 10) || 52;
    const targetTop = window.scrollY + target.getBoundingClientRect().top;
    window.scrollTo({ top: targetTop - navH, behavior: 'smooth' });
  });
});

// ── 6. Scroll Reveal ────────────────────────────
if (!hasIO) {
  document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
} else {
  const revealObs = new IntersectionObserver(entries => {
    entries.forEach(({ target, isIntersecting }) => {
      if (isIntersecting) {
        target.classList.add('visible');
        revealObs.unobserve(target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));
}

// ── 7. Hero counter animation ───────────────────
if (hasIO) {
  const counterObs = new IntersectionObserver(entries => {
    entries.forEach(({ target, isIntersecting }) => {
      if (!isIntersecting) return;
      counterObs.unobserve(target);
      const end = parseInt(target.dataset.target, 10);
      const dur = 1800;
      const start = performance.now();
      const tick = now => {
        const t = Math.min((now - start) / dur, 1);
        const ease = 1 - Math.pow(1 - t, 3);
        target.textContent = Math.round(ease * end);
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('.hstat-n[data-target]').forEach(el => counterObs.observe(el));
}

// ── 8. Scrollytelling ───────────────────────────
const storyItems = document.querySelectorAll('.story-item');

function updateStoryProgress() {
  if (!storySection) return;
  // Batch ALL reads before any writes to avoid forced reflow
  if (!storySectionH) storySectionH = storySection.offsetHeight;
  const rect = storySection.getBoundingClientRect();
  const vh = window.innerHeight;
  const itemRects = [...storyItems].map(item => item.getBoundingClientRect());

  // Writes only after all reads are done
  const progress = Math.min(Math.max(-rect.top / (storySectionH - vh), 0), 1);
  if (storyFill) storyFill.style.height = `${progress * 100}%`;
  const mid = vh / 2;
  storyItems.forEach((item, i) => {
    const r = itemRects[i];
    item.classList.toggle('active', r.top < mid && r.bottom > 0);
  });
}

if (hasIO) {
  const storyObs = new IntersectionObserver(entries => {
    entries.forEach(({ target, isIntersecting }) => {
      if (isIntersecting) target.classList.add('active');
      else target.classList.remove('active');
    });
  }, { threshold: 0.3 });
  storyItems.forEach(el => storyObs.observe(el));
}

// ── 9. AI Section Demo Chat ─────────────────────
(function initDemoChat() {
  if (!hasIO) return;
  const msgs = document.querySelectorAll('#demo-chat .chat-hidden');
  if (!msgs.length) return;

  const demoObs = new IntersectionObserver(entries => {
    entries.forEach(({ isIntersecting }) => {
      if (!isIntersecting) return;
      demoObs.disconnect();
      msgs.forEach(msg => {
        const delay = parseInt(msg.dataset.delay, 10) || 1000;
        setTimeout(() => msg.classList.add('shown'), delay);
      });
    });
  }, { threshold: 0.4 });

  const aiSection = document.getElementById('ai-section');
  if (aiSection) demoObs.observe(aiSection);
})();

// ── 10. Behavior Tracking ──────────────────────
const tracked = { scrollDepths: new Set(), clicks: 0 };
// Thay YOUR_ACCESS_KEY bằng key từ web3forms.com
const WEB3FORMS_KEY = '8ba2fa3f-0d38-458a-9f23-8b97b15a11dc';
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
  try {
    const blob = new Blob([JSON.stringify(payload)], { type: 'text/plain' });
    if (navigator.sendBeacon) navigator.sendBeacon(WEBHOOK, blob);
    else fetch(WEBHOOK, { method: 'POST', body: blob, keepalive: true }).catch(() => {});
  } catch {}
}

document.addEventListener('click', e => {
  tracked.clicks++;
  const el = e.target.closest('a, button, .feat-card, .story-card');
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

// ── 11. Subscribe Form ──────────────────────────
const form = document.getElementById('subscribe-form');
const submitBtn = document.getElementById('submit-btn');
const toast = document.getElementById('toast');

const RULES = {
  name:  { validate: v => v.trim().length >= 2, msg: 'Họ và tên phải có ít nhất 2 ký tự.' },
  email: { validate: v => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()), msg: 'Email không hợp lệ.' },
  phone: { validate: v => v === '' || /^(0|\+84)[3-9]\d{8}$/.test(v.replace(/\s/g, '')), msg: 'Số điện thoại không hợp lệ (VD: 0912345678).' },
};

['name', 'email', 'phone'].forEach(f => {
  const inp = document.getElementById(`f-${f}`);
  if (inp) inp.addEventListener('input', () => {
    if (RULES[f].validate(inp.value) || (f === 'phone' && inp.value === '')) clearError(f);
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

document.querySelector('.toast-x')?.addEventListener('click', () => { toast.hidden = true; });

form?.addEventListener('submit', async e => {
  e.preventDefault();
  let valid = true;
  ['name', 'email', 'phone'].forEach(f => {
    const val = document.getElementById(`f-${f}`)?.value || '';
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
    if (WEB3FORMS_KEY && WEB3FORMS_KEY !== 'YOUR_ACCESS_KEY') {
      const resp = await fetch('https://api.web3forms.com/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          access_key: WEB3FORMS_KEY,
          subject: `[PosPos] Đăng ký dùng thử — ${data.name}`,
          from_name: 'PosPos Landing',
          name: data.name,
          email: data.email,
          phone: data.phone || '(không điền)',
          store_type: data.store_type || '(không chọn)',
          timestamp: data.timestamp,
          source: data.source,
        }),
      });
      const json = await resp.json();
      if (!json.success) throw new Error(json.message || 'Submit failed');
    } else {
      // Chưa cấu hình — simulate để test UI
      await new Promise(r => setTimeout(r, 900));
    }
    form.reset();
    showToast();
    trackEvent('form_success', { email: data.email });
  } catch (e) {
    console.error('[PosPos Form]', e);
    showError('email', 'Có lỗi xảy ra. Vui lòng thử lại.');
  } finally {
    setLoading(false);
  }
});

// ── 12. Chatbot Widget ──────────────────────────
const KB = [
  {
    keys: ['xin chào','hello','hi','chào','alo','hey'],
    answer: '👋 Xin chào! Tôi là trợ lý AI của PosPos.\n\nTôi có thể giúp bạn tìm hiểu về:\n• Tính năng hệ thống\n• Cách bắt đầu dùng thử\n• Thông tin kỹ thuật\n• Bảng giá',
    quick: ['Tính năng nổi bật','Cách dùng thử','Giá cả?','Hỗ trợ'],
  },
  {
    keys: ['tính năng','feature','có gì','làm được gì','chức năng'],
    answer: '✨ PosPos có các tính năng chính:\n\n🛒 Bán hàng POS — giao diện cảm ứng, tìm kiếm realtime\n📦 Kho hàng — cảnh báo tồn kho, đề xuất nhập hàng\n🤖 AI Chatbot — phân tích kho, doanh thu tự động\n📊 Báo cáo — doanh thu 7/30/90 ngày\n🏪 Đa chi nhánh — nhiều shop cùng lúc\n🔒 Bảo mật JWT — rate limiting, audit log',
    quick: ['Chatbot AI hoạt động thế nào?','Quản lý kho ra sao?','Dùng thử ngay'],
  },
  {
    keys: ['chatbot','ai','thư ký','tự động','trí tuệ'],
    answer: '🤖 Chatbot AI PosPos — Thư ký ảo hoạt động 24/7:\n\n• Cảnh báo hàng < 1/3 lượng ban đầu\n• Đề xuất đặt hàng dựa trên tốc độ bán 7/30 ngày\n• Báo cáo doanh thu tức thì\n• Ranking sản phẩm bán chạy nhất\n• Tạo đơn nhập hàng tự động qua chat',
    quick: ['Quản lý kho thế nào?','Dùng thử miễn phí'],
  },
  {
    keys: ['kho','tồn kho','inventory','nhập hàng','hàng hóa'],
    answer: '📦 Quản lý kho với PosPos:\n\n• Theo dõi tồn kho real-time qua WebSocket\n• Cảnh báo tự động khi hàng < 1/3 ban đầu\n• Phân tích tốc độ bán theo tuần/tháng\n• Đề xuất số lượng cần nhập theo AI\n• Lịch sử nhập/xuất chi tiết đầy đủ',
    quick: ['Chatbot AI','Báo cáo doanh thu','Dùng thử ngay'],
  },
  {
    keys: ['báo cáo','report','doanh thu','revenue','thống kê'],
    answer: '📊 Báo cáo & Analytics của PosPos:\n\n• Doanh thu 7/30/90 ngày — cập nhật realtime\n• Số hóa đơn, giá trị trung bình mỗi đơn\n• Công nợ khách hàng tổng hợp\n• Xếp hạng khách hàng VIP\n• Celery tự gửi báo cáo tổng kết qua email',
    quick: ['Tính năng khác','Dùng thử ngay'],
  },
  {
    keys: ['giá','price','bao nhiêu','chi phí','phí','bảng giá','cost'],
    answer: '💰 PosPos cung cấp gói dùng thử:\n\n🎁 30 ngày miễn phí — không cần thẻ tín dụng\n✅ Hỗ trợ thiết lập hoàn toàn miễn phí\n✅ Không cam kết dài hạn\n\nĐiền form đăng ký, đội ngũ liên hệ trong 24 giờ!',
    quick: ['Đăng ký dùng thử →','Tính năng nổi bật'],
  },
  {
    keys: ['dùng thử','trial','đăng ký','bắt đầu','start','demo','miễn phí'],
    answer: '🚀 Bắt đầu dùng thử PosPos miễn phí:\n\n1️⃣ Điền form đăng ký bên dưới trang\n2️⃣ Đội ngũ liên hệ trong vòng 24 giờ\n3️⃣ Thiết lập hệ thống cho cửa hàng bạn\n4️⃣ Trải nghiệm 30 ngày không mất phí',
    quick: ['Đến form đăng ký ↓'],
    action: () => { closeCbot(); setTimeout(() => document.getElementById('subscribe')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300); },
  },
  {
    keys: ['bảo mật','security','jwt','an toàn','mã hóa'],
    answer: '🔒 Bảo mật cấp doanh nghiệp:\n\n• JWT + bcrypt — mã hóa chuẩn industry\n• Rate limiting — chặn brute force tự động\n• Audit log — ghi MỌI thao tác với timestamp\n• Prometheus metrics — giám sát 24/7\n• HTTPS only trên production',
    quick: ['Thông số kỹ thuật','Tính năng khác'],
  },
  {
    keys: ['công nghệ','tech','stack','fastapi','python','postgresql','redis'],
    answer: '⚙️ Tech stack của PosPos:\n\n• Backend: FastAPI 0.119 + Python (async)\n• Database: PostgreSQL + SQLAlchemy 2.0\n• Cache: Redis 5.2\n• Real-time: WebSocket native\n• Auth: JWT + bcrypt\n• Tasks: Celery 5.4\n• Monitor: Prometheus\n• Deploy: Docker + Uvicorn',
    quick: ['Tính năng nổi bật','Dùng thử ngay'],
  },
  {
    keys: ['hỗ trợ','support','liên hệ','contact','giúp'],
    answer: '📞 Liên hệ hỗ trợ PosPos:\n\n📧 Email: hoangthanh29042003@gmail.com\n💻 GitHub: github.com/surp29\n⏰ Phản hồi trong vòng 24 giờ\n\nHoặc điền form đăng ký — đội ngũ sẽ chủ động liên hệ!',
    quick: ['Đăng ký dùng thử →','Tính năng nổi bật'],
  },
];

const DEFAULT_ANS = {
  answer: '🤔 Tôi chưa hiểu câu hỏi của bạn.\n\nBạn có thể hỏi về:\n• Tính năng của PosPos\n• Cách dùng thử miễn phí\n• Thông tin kỹ thuật\n• Liên hệ hỗ trợ',
  quick: ['Tính năng nổi bật','Cách dùng thử','Giá cả?'],
};

function findAnswer(msg) {
  const m = msg.toLowerCase().trim();
  return KB.find(item => item.keys.some(k => m.includes(k))) || DEFAULT_ANS;
}

let cbotOpen = false;
let cbotGreeted = false;

const cbotToggle = document.getElementById('cbot-toggle');
const cbotWin = document.getElementById('cbot-win');
const cbotMsgs = document.getElementById('cbot-msgs');
const cbotQuick = document.getElementById('cbot-quick');
const cbotInp = document.getElementById('cbot-inp');
const cbotSend = document.getElementById('cbot-send');
const cbotX = document.getElementById('cbot-x');
const cbotBadge = document.getElementById('cbot-badge');
const cbotOpenEl = cbotToggle.querySelector('.cbot-open');
const cbotCloseEl = cbotToggle.querySelector('.cbot-close');

function openCbot() {
  cbotOpen = true;
  cbotWin.hidden = false;
  cbotToggle.setAttribute('aria-expanded', 'true');
  cbotOpenEl.hidden = true;
  cbotCloseEl.hidden = false;
  cbotBadge.hidden = true;
  if (!cbotGreeted) {
    cbotGreeted = true;
    setTimeout(() => addBotMsg('👋 Xin chào! Tôi là trợ lý AI của PosPos.\nTôi có thể tư vấn về tính năng, cách dùng thử và hỗ trợ kỹ thuật.', ['Tính năng nổi bật','Cách dùng thử','Giá cả?','Liên hệ hỗ trợ']), 350);
  }
  trackEvent('chatbot_open');
}

function closeCbot() {
  cbotOpen = false;
  cbotWin.hidden = true;
  cbotToggle.setAttribute('aria-expanded', 'false');
  cbotOpenEl.hidden = false;
  cbotCloseEl.hidden = true;
}

cbotToggle.addEventListener('click', () => cbotOpen ? closeCbot() : openCbot());
cbotX.addEventListener('click', closeCbot);

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

function addMsg(text, type) {
  const d = document.createElement('div');
  d.className = `cbot-msg ${type}`;
  d.innerHTML = `<div class="cbot-bubble">${escHtml(text)}</div>`;
  cbotMsgs.appendChild(d);
  cbotMsgs.scrollTop = cbotMsgs.scrollHeight;
}

function showTyping() {
  const d = document.createElement('div');
  d.className = 'cbot-msg bot';
  d.innerHTML = `<div class="cbot-typing"><span></span><span></span><span></span></div>`;
  cbotMsgs.appendChild(d);
  cbotMsgs.scrollTop = cbotMsgs.scrollHeight;
  return d;
}

function renderQuick(items, actionFn) {
  cbotQuick.innerHTML = '';
  if (!items?.length) return;
  items.forEach(label => {
    const btn = document.createElement('button');
    btn.className = 'qbtn';
    btn.textContent = label;
    btn.addEventListener('click', () => {
      if (label === 'Đến form đăng ký ↓' && actionFn) { actionFn(); return; }
      if (label === 'Đăng ký dùng thử →') {
        closeCbot();
        setTimeout(() => document.getElementById('subscribe')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
        return;
      }
      handleUserMsg(label);
    });
    cbotQuick.appendChild(btn);
  });
}

function addBotMsg(text, quick = [], actionFn = null) {
  const typing = showTyping();
  setTimeout(() => {
    typing.remove();
    addMsg(text, 'bot');
    renderQuick(quick, actionFn);
  }, 700 + Math.random() * 400);
}

function handleUserMsg(text) {
  if (!text.trim()) return;
  cbotQuick.innerHTML = '';
  addMsg(text, 'user');
  const result = findAnswer(text);
  addBotMsg(result.answer, result.quick, result.action);
  trackEvent('chatbot_msg', { q: text.slice(0, 60) });
}

cbotSend.addEventListener('click', () => {
  const v = cbotInp.value.trim();
  if (!v) return;
  cbotInp.value = '';
  handleUserMsg(v);
});
cbotInp.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); cbotSend.click(); }
});

// Auto badge after 8s
setTimeout(() => {
  if (!cbotOpen) cbotBadge.hidden = false;
}, 8000);
