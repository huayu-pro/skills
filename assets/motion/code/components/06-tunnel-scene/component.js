/* 06-tunnel-scene — 26-layer Canvas2D tunnel + scroll typography */
(function () {
  "use strict";

  const LAYERS = 26;
  const PARTICLES = 46;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function mount(root, options = {}) {
    if (!root) throw new Error("tunnel: root required");
    const canvas = root.querySelector(".rf-tunnel__canvas");
    const progressEl = root.querySelector(".rf-tunnel__progress");
    const panels = [...root.querySelectorAll("[data-panel]")];
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("tunnel: Canvas2D unavailable");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let raf = 0;
    let last = performance.now();
    let time = 0;
    let frames = 0;
    let scrollN = 0;
    let scrollTarget = 0;
    let dragX = 0, dragY = 0, dragXT = 0, dragYT = 0;
    let down = false;
    let startX = 0, startY = 0;
    let moved = 0;
    let releaseAt = 0;
    let w = 1, h = 1, dpr = 1;

    function resize() {
      dpr = Math.min(devicePixelRatio || 1, 2);
      w = innerWidth;
      h = innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function onScroll() {
      const max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
      scrollTarget = clamp(scrollY / max, 0, 1);
    }

    function onPointerDown(e) {
      if (reduced) return;
      down = true;
      moved = 0;
      startX = e.clientX;
      startY = e.clientY;
      root.classList.add("is-dragging");
    }

    function onPointerMove(e) {
      if (reduced) return;
      if (down) {
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        startX = e.clientX;
        startY = e.clientY;
        moved += Math.abs(dx) + Math.abs(dy);
        dragXT = clamp(dragXT + dx, -220, 220);
        dragYT = clamp(dragYT + dy, -180, 180);
      } else {
        dragXT = clamp((e.clientX / innerWidth - 0.5) * 120, -120, 120);
        dragYT = clamp((e.clientY / innerHeight - 0.5) * 80, -80, 80);
      }
    }

    function onPointerUp() {
      if (!down) return;
      down = false;
      releaseAt = performance.now();
      root.classList.remove("is-dragging");
    }

    function draw() {
      ctx.clearRect(0, 0, w, h);
      const cx = w / 2;
      const cy = h / 2;
      const rotBase = (dragXT * 0.0016 + (dragXT / 120) * 0.06) * 0.01;
      const timeMs = time * 1000;

      for (let i = 0; i < LAYERS; i++) {
        const phase = ((i / LAYERS + scrollN * 1.35 + timeMs * 0.00035) % 1 + 1) % 1;
        const z = Math.pow(phase, 1.8);
        const scale = 0.08 + z * 1.9;
        const rw = w * scale;
        const rh = h * scale * 0.92;
        const rot = (rotBase + dragXT * 0.0005) * (0.4 + z);
        const alpha = 0.05 + z * 0.36;
        const rad = Math.min(rw, rh) * 0.08;

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(rot);
        ctx.beginPath();
        if (typeof ctx.roundRect === "function") {
          ctx.roundRect(-rw / 2, -rh / 2, rw, rh, rad);
        } else {
          ctx.rect(-rw / 2, -rh / 2, rw, rh);
        }
        ctx.strokeStyle = `rgba(232, 180, 90, ${alpha.toFixed(3)})`;
        ctx.lineWidth = Math.max(0.6, 1.2 * z);
        ctx.stroke();
        ctx.restore();
      }

      for (let i = 0; i < PARTICLES; i++) {
        const seed = (i * 0.618033 + scrollN * 0.7 + timeMs * 0.00012) % 1;
        const z = Math.pow(seed, 1.6);
        const angle = i * 2.399963 + timeMs * 0.0002;
        const radius = (0.12 + z * 0.9) * Math.min(w, h) * 0.55;
        const px = cx + Math.cos(angle) * radius + dragXT * 0.15;
        const py = cy + Math.sin(angle) * radius * 0.72 + dragYT * 0.15;
        const size = (1 - z) * 2.6 + 0.4;
        ctx.beginPath();
        ctx.arc(px, py, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(244, 239, 228, ${(0.08 + z * 0.5).toFixed(3)})`;
        ctx.fill();
      }
    }

    function updatePanels() {
      for (const p of panels) {
        const r = p.getBoundingClientRect();
        const v = clamp(1 - Math.abs(r.top + r.height / 2 - innerHeight / 2) / (innerHeight * 0.9), 0, 1);
        p.style.transform = `translateY(${((1 - v) * 38).toFixed(2)}px)`;
        p.style.opacity = (0.35 + v * 0.65).toFixed(3);
      }
    }

    function frame(now) {
      if (reduced) return;
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      time += dt;
      scrollN += (scrollTarget - scrollN) * 0.14;
      dragX += (dragXT - dragX) * 0.12;
      dragY += (dragYT - dragY) * 0.12;

      if (!down && releaseAt && now - releaseAt > 500) {
        const decay = Math.pow(0.94, dt / 0.04);
        dragXT *= decay;
        dragYT *= decay;
        dragX *= decay;
        dragY *= decay;
      }

      draw();
      updatePanels();
      progressEl.textContent = String(Math.round(scrollN * 100)).padStart(2, "0");
      frames++;
      raf = requestAnimationFrame(frame);
    }

    function staticFrame() {
      resize();
      scrollN = scrollTarget = 0;
      dragX = dragXT = 0;
      dragY = dragYT = 0;
      draw();
      updatePanels();
      progressEl.textContent = "00";
    }

    root.addEventListener("pointerdown", onPointerDown, { signal });
    window.addEventListener("pointermove", onPointerMove, { signal });
    window.addEventListener("pointerup", onPointerUp, { signal });
    window.addEventListener("pointercancel", onPointerUp, { signal });
    window.addEventListener("scroll", onScroll, { passive: true, signal });
    window.addEventListener("resize", resize, { signal });

    const onReduceChange = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) {
        cancelAnimationFrame(raf);
        raf = 0;
        staticFrame();
      } else {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    root.classList.toggle("is-reduced", reduced);
    resize();
    onScroll();
    if (reduced) {
      staticFrame();
    } else {
      last = performance.now();
      raf = requestAnimationFrame(frame);
    }

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.tunnel = {
      get frames() { return frames; },
      get scrollN() { return scrollN; },
      get dragX() { return dragXT; },
      get layers() { return LAYERS; },
    };

    return function dispose() {
      ac.abort();
      cancelAnimationFrame(raf);
      root.classList.remove("is-reduced", "is-dragging");
      ctx.clearRect(0, 0, w, h);
      if (window.__rfStats) window.__rfStats.tunnel = null;
    };
  }

  window.RFTunnel = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="tunnel-scene"]');
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
