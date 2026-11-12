/* 10-scroll-narrative — IO reveal + sticky pin + accordion + modal */
(function () {
  "use strict";

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const smooth = (a, b, v) => {
    const t = clamp((v - a) / (b - a), 0, 1);
    return t * t * (3 - 2 * t);
  };

  function mount(root, options = {}) {
    if (!root) throw new Error("scroll: root required");
    const bar = root.querySelector(".rf-scroll__bar");
    const pin = root.querySelector(".rf-scroll__pin");
    const pinInner = root.querySelector(".rf-scroll__pin-inner");
    const panels = [...root.querySelectorAll(".rf-scroll__panel")];
    const tiles = [...root.querySelectorAll("[data-reveal]")];
    const accBtns = [...root.querySelectorAll(".rf-scroll__acc-btn")];
    const openBtn = root.querySelector("[data-open]");
    const dialog = root.querySelector(".rf-scroll__modal");
    const closeBtn = root.querySelector(".rf-scroll__close");
    const form = root.querySelector(".rf-scroll__form");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let lastY = scrollY;
    let ticking = false;
    let reveals = 0;
    let progress = 0;
    let io = null;
    let closedTimer = 0;

    function onScroll() {
      if (reduced) return;
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(() => {
          ticking = false;
          const y = scrollY;
          bar.classList.toggle("is-hidden", y > lastY && y > 160);
          lastY = y;
          updatePin();
        });
      }
    }

    function updatePin() {
      const r = pin.getBoundingClientRect();
      const total = Math.max(1, r.height - innerHeight);
      progress = clamp(-r.top / total, 0, 1);
      pinInner.style.setProperty("--p", progress.toFixed(4));
      panels.forEach((panel, i) => {
        let o = 0;
        if (i === 0) o = 1 - smooth(0.12, 0.42, progress);
        else if (i === 1) o = smooth(0.12, 0.42, progress) * (1 - smooth(0.52, 0.82, progress));
        else o = smooth(0.52, 0.82, progress);
        o = clamp(o, 0, 1);
        panel.style.opacity = o.toFixed(3);
        panel.style.transform = `translateY(${((1 - o) * 26).toFixed(1)}px) scale(${(0.96 + o * 0.04).toFixed(3)})`;
        panel.style.pointerEvents = o > 0.6 ? "auto" : "none";
      });
    }

    io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        e.target.classList.add("is-in");
        reveals++;
        io.unobserve(e.target);
      }
    }, { rootMargin: "200px", threshold: 0 });

    if (reduced) {
      tiles.forEach((t) => t.classList.add("is-in"));
      panels.forEach((p) => { p.style.opacity = "1"; p.style.transform = "none"; });
    } else {
      tiles.forEach((t) => io.observe(t));
      updatePin();
    }

    accBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const item = btn.closest(".rf-scroll__acc-item");
        const open = !item.classList.contains("is-open");
        item.classList.toggle("is-open", open);
        btn.setAttribute("aria-expanded", open ? "true" : "false");
      }, { signal });
    });

    openBtn.addEventListener("click", () => {
      if (!dialog.open) dialog.showModal();
      setTimeout(() => closeBtn.focus({ preventScroll: true }), 40);
    }, { signal });
    closeBtn.addEventListener("click", () => dialog.close(), { signal });
    dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); }, { signal });
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const submit = form.querySelector(".rf-scroll__submit");
      submit.textContent = "Sent";
      setTimeout(() => { dialog.close(); submit.textContent = "Send"; }, 500);
    }, { signal });

    window.addEventListener("scroll", onScroll, { passive: true, signal });
    window.addEventListener("resize", () => { if (!reduced) updatePin(); }, { signal });

    const onReduce = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) {
        bar.classList.remove("is-hidden");
        tiles.forEach((t) => t.classList.add("is-in"));
        panels.forEach((p) => { p.style.opacity = "1"; p.style.transform = "none"; });
      } else {
        updatePin();
        tiles.forEach((t) => { if (!t.classList.contains("is-in") && io) io.observe(t); });
      }
    };
    reduceMQ.addEventListener("change", onReduce, { signal });

    root.classList.toggle("is-reduced", reduced);

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.scroll = {
      get reveals() { return reveals; },
      get progress() { return progress; },
      get tiles() { return tiles.length; },
      get animations() { return document.getAnimations().length; },
    };

    return function dispose() {
      ac.abort();
      clearTimeout(closedTimer);
      if (io) io.disconnect();
      if (dialog.open) dialog.close();
      root.classList.remove("is-reduced");
      bar.classList.remove("is-hidden");
      if (window.__rfStats) window.__rfStats.scroll = null;
    };
  }

  window.RFScroll = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="scroll-narrative"]');
    if (!root || root.dataset.rfMounted === "1") return;
    root.dataset.rfMounted = "1";
    const dispose = mount(root);
    window.__rfDispose = dispose;
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount, { once: true });
  } else {
    autoMount();
  }
})();
