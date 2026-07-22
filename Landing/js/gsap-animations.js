'use strict';

/* ═══════════════════════════════════════════════
   PosPos Landing — GSAP animation layer
   Progressive enhancement: nếu GSAP/ScrollTrigger không load được (CDN chặn,
   offline) hoặc người dùng bật "prefers-reduced-motion", toàn bộ nội dung hiện
   ra ngay lập tức qua đúng cơ chế .reveal/.visible sẵn có trong style.css —
   trang không bao giờ bị kẹt ở trạng thái opacity:0.
   ═══════════════════════════════════════════════ */

(function () {
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealEls = document.querySelectorAll('.reveal');
  var counterEls = document.querySelectorAll('.hstat-n[data-target]');

  function showEverythingNow() {
    revealEls.forEach(function (el) { el.classList.add('visible'); });
    counterEls.forEach(function (el) { el.textContent = el.dataset.target; });
  }

  if (reduceMotion || typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
    showEverythingNow();
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  // ── Hero: timeline riêng, PAUSED cho tới khi skeleton overlay biến mất ──
  // (main.js hiện main/footer ở mốc window.load + 300ms — nếu chạy timeline
  // ngay lúc script parse, animation sẽ chạy xong trong lúc bị che sau overlay).
  var heroText = document.querySelector('.hero-text');
  var heroVisual = document.querySelector('.hero-visual');
  var heroTl = null;

  if (heroText) {
    gsap.set(heroText, { opacity: 1, y: 0 }); // wrapper hiện ngay, timeline điều khiển từng phần con bên trong
    heroTl = gsap.timeline({ paused: true, defaults: { ease: 'power3.out', duration: 0.9 } });
    heroTl
      .from('.eyebrow', { opacity: 0, y: 14 }, 0.1)
      .from('.hero-headline', { opacity: 0, y: 34 }, 0.24)
      .from('.hero-sub', { opacity: 0, y: 20 }, 0.4)
      .from('.hero-ctas', { opacity: 0, y: 16 }, 0.54)
      .from('.hero-stats .hstat', { opacity: 0, y: 14, stagger: 0.08 }, 0.66);
  }

  window.addEventListener('load', function () {
    setTimeout(function () { if (heroTl) heroTl.play(); }, 320);
  });
  // An toàn: nếu vì lý do gì đó 'load' không bao giờ bắn (hiếm), vẫn chạy sau 2.5s
  setTimeout(function () { if (heroTl && heroTl.progress() === 0) heroTl.play(); }, 2500);

  if (heroVisual) {
    gsap.set(heroVisual, { opacity: 1 });
    gsap.from(heroVisual, {
      opacity: 0, y: 50, scale: 0.96, duration: 1, ease: 'power3.out',
      scrollTrigger: { trigger: heroVisual, start: 'top 88%' },
    });
  }

  // Glow nhẹ trôi theo scroll — chi tiết depth kiểu Apple, rất tinh tế
  gsap.utils.toArray('.hero-glow').forEach(function (glow, i) {
    gsap.to(glow, {
      yPercent: i === 0 ? 12 : -10,
      ease: 'none',
      scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 0.6 },
    });
  });

  // ── Hero stat counters — GSAP numeric tween thay cho vòng lặp rAF thủ công ──
  counterEls.forEach(function (el) {
    var target = parseInt(el.dataset.target, 10);
    var proxy = { val: 0 };
    ScrollTrigger.create({
      trigger: el,
      start: 'top 90%',
      once: true,
      onEnter: function () {
        gsap.to(proxy, {
          val: target, duration: 1.6, ease: 'power3.out',
          onUpdate: function () { el.textContent = Math.round(proxy.val); },
        });
      },
    });
  });

  // ── Reveal cho phần còn lại của trang — batch theo nhóm để cascade mượt ──
  var otherReveals = Array.prototype.filter.call(revealEls, function (el) {
    return el !== heroText && el !== heroVisual;
  });

  otherReveals.forEach(function (el) {
    if (el.classList.contains('reveal-right')) {
      gsap.set(el, { opacity: 0, x: 36 });
    } else {
      gsap.set(el, { opacity: 0, y: 28 });
    }
  });

  ScrollTrigger.batch(otherReveals, {
    start: 'top 88%',
    once: true,
    onEnter: function (batch) {
      gsap.to(batch, {
        opacity: 1, y: 0, x: 0,
        stagger: 0.12, duration: 0.75, ease: 'power2.out',
      });
    },
  });
})();
