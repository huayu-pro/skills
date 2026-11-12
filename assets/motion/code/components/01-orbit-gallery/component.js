/* 01-orbit-gallery — orbit stage with depth channels + lens-style detail */
(function () {
  "use strict";

  const PROJECTS = [
    {
      title: "Aurora Ledger",
      tag: "Product / Finance",
      year: "2026",
      role: "Design & build",
      desc: "A calm ledger for a climate fund. Six project cards orbit a single core; depth drives scale, blur, brightness and stacking at once.",
      art: "radial-gradient(circle at 30% 20%, #bff3e6 0%, transparent 38%), radial-gradient(circle at 75% 70%, #2f7f9e 0%, transparent 55%), linear-gradient(145deg, #0f2a33, #071217 70%)",
    },
    {
      title: "Soft Machine",
      tag: "Editorial / Studio",
      year: "2025",
      role: "Art direction",
      desc: "An editorial system for a small studio. The orbit replaces the usual three-column grid; the core is the only fixed point.",
      art: "radial-gradient(circle at 70% 20%, #ffe3b0 0%, transparent 42%), radial-gradient(circle at 30% 80%, #b23b2e 0%, transparent 55%), linear-gradient(160deg, #2a1712, #120a08 75%)",
    },
    {
      title: "Night Bloom",
      tag: "Fashion / Campaign",
      year: "2026",
      role: "Motion study",
      desc: "A campaign stage where cards behave like objects on a slow turntable. Drag gives velocity; release keeps the drift.",
      art: "radial-gradient(circle at 35% 25%, #f4c7ff 0%, transparent 40%), radial-gradient(circle at 70% 75%, #5a2b8f 0%, transparent 58%), linear-gradient(150deg, #1b1030, #0a0614 75%)",
    },
    {
      title: "Field Notes",
      tag: "Research / Archive",
      year: "2024",
      role: "Interface",
      desc: "An archive of field recordings. The orbit is a browsing aid, not a gimmick: each card keeps its label and index visible.",
      art: "radial-gradient(circle at 25% 75%, #cfe8b0 0%, transparent 42%), radial-gradient(circle at 80% 20%, #3d6b4a 0%, transparent 55%), linear-gradient(145deg, #101b12, #070b08 75%)",
    },
    {
      title: "Mono House",
      tag: "Architecture / Practice",
      year: "2025",
      role: "Design system",
      desc: "A practice site with a single orbiting index. The grayscale art keeps the focus on the geometry of the orbit.",
      art: "radial-gradient(circle at 60% 30%, #f3f3f0 0%, transparent 36%), radial-gradient(circle at 30% 70%, #7e7e78 0%, transparent 52%), linear-gradient(150deg, #232323, #0c0c0c 75%)",
    },
    {
      title: "Signal Garden",
      tag: "Sound / Installation",
      year: "2026",
      role: "Prototype",
      desc: "A sound installation index. The warm art and the slow drift make the orbit feel like a physical rack, not a carousel.",
      art: "radial-gradient(circle at 70% 25%, #ffd39a 0%, transparent 38%), radial-gradient(circle at 25% 75%, #c04a1f 0%, transparent 58%), linear-gradient(150deg, #2b130b, #0d0604 75%)",
    },
  ];

  const STEP = (Math.PI * 2) / PROJECTS.length;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const mod = (v, n) => ((v % n) + n) % n;

  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function mount(root, options = {}) {
    if (!root) throw new Error("orbit: root required");
    const stage = root.querySelector(".rf-orbit__stage");
    const cardsWrap = root.querySelector(".rf-orbit__cards");
    const thumbsWrap = root.querySelector(".rf-orbit__thumbs");
    const countEl = root.querySelector(".rf-orbit__count");
    const dialog = root.querySelector(".rf-orbit__detail");
    const closeBtn = root.querySelector(".rf-orbit__close");
    const detailArt = root.querySelector(".rf-orbit__detail-art");
    const detailEyebrow = root.querySelector(".rf-orbit__eyebrow");
    const detailTitle = root.querySelector(".rf-orbit__detail h2");
    const detailDesc = root.querySelector(".rf-orbit__desc");
    const detailYear = root.querySelector(".rf-orbit__year");
    const detailRole = root.querySelector(".rf-orbit__role");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let raf = 0;
    let ro = null;
    let reduced = reduceMQ.matches;
    let angle = -0.35;
    let target = angle;
    let velocity = 0;
    let down = false;
    let startX = 0;
    let moved = 0;
    let lastDrag = 0;
    let current = 0;
    let frames = 0;
    let rx = 300;
    let ry = 180;
    let w = 0;
    let h = 0;
    let closedTimer = 0;

    const cards = [];
    const thumbs = [];

    PROJECTS.forEach((p, i) => {
      const card = el("button", "rf-orbit__card");
      card.type = "button";
      card.setAttribute("role", "listitem");
      card.setAttribute("aria-label", `${p.title} — ${p.tag}`);
      card.style.setProperty("--art", p.art);
      card.innerHTML =
        '<span class="rf-orbit__art" aria-hidden="true"></span>' +
        '<span class="rf-orbit__meta">' +
        `<span class="rf-orbit__no">0${i + 1}</span>` +
        `<span class="rf-orbit__title">${p.title}</span>` +
        `<span class="rf-orbit__tag">${p.tag}</span>` +
        "</span>";
      card.addEventListener("click", (e) => {
        if (moved > 8 && Date.now() - lastDrag < 350) return;
        open(i, e);
      }, { signal });
      card.addEventListener("focus", () => { focusIndex(i); }, { signal });
      cardsWrap.appendChild(card);
      cards.push(card);

      const thumb = el("button", "rf-orbit__thumb");
      thumb.type = "button";
      thumb.setAttribute("role", "listitem");
      thumb.setAttribute("aria-label", `查看 ${p.title}`);
      thumb.style.setProperty("--art", p.art);
      thumb.addEventListener("click", () => focusIndex(i), { signal });
      thumbsWrap.appendChild(thumb);
      thumbs.push(thumb);
    });

    function layout() {
      const r = stage.getBoundingClientRect();
      w = r.width;
      h = r.height;
      rx = Math.min(w * 0.34, 520);
      ry = Math.min(h * 0.26, 240);
      if (reduced) {
        cards.forEach((c) => { c.style.transform = ""; c.style.filter = ""; c.style.opacity = ""; c.style.zIndex = ""; });
        return;
      }
      render();
    }

    function render() {
      for (let i = 0; i < cards.length; i++) {
        const a = angle + i * STEP;
        const depth = Math.sin(a);
        const x = Math.cos(a) * rx;
        const y = Math.sin(a) * ry * 0.72;
        const scale = 0.72 + ((depth + 1) / 2) * 0.34;
        const blur = depth < 0 ? (1 - depth) * 1.1 : 0;
        const opacity = 0.62 + ((depth + 1) / 2) * 0.38;
        const z = 60 + Math.round(depth * 40);
        const card = cards[i];
        card.style.transform = `translate(-50%, -50%) translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) scale(${scale.toFixed(3)})`;
        card.style.filter = blur > 0.02 ? `blur(${blur.toFixed(2)}px)` : "none";
        card.style.opacity = opacity.toFixed(3);
        card.style.zIndex = String(z);
      }
      let front = 0;
      let best = -2;
      for (let i = 0; i < cards.length; i++) {
        const d = Math.sin(angle + i * STEP);
        if (d > best) { best = d; front = i; }
      }
      if (front !== current) {
        current = front;
        countEl.textContent = `0${front + 1} / 0${PROJECTS.length}`;
        thumbs.forEach((t, i) => t.classList.toggle("is-active", i === front));
      }
    }

    function frame() {
      if (reduced) return;
      angle += (target - angle) * 0.08 + velocity;
      velocity *= 0.9;
      if (Math.abs(velocity) < 0.00002) velocity = 0;
      render();
      frames++;
      raf = requestAnimationFrame(frame);
    }

    function nearestTarget(index) {
      const desired = -index * STEP;
      const delta = mod(desired - target + Math.PI, Math.PI * 2) - Math.PI;
      target += delta;
    }

    function focusIndex(index) {
      nearestTarget(index);
      if (reduced) {
        current = index;
        countEl.textContent = `0${index + 1} / 0${PROJECTS.length}`;
        thumbs.forEach((t, i) => t.classList.toggle("is-active", i === index));
      }
    }

    function open(index, event) {
      const p = PROJECTS[index];
      current = index;
      countEl.textContent = `0${index + 1} / 0${PROJECTS.length}`;
      thumbs.forEach((t, i) => t.classList.toggle("is-active", i === index));
      detailArt.style.setProperty("--art", p.art);
      detailArt.style.background = p.art;
      detailEyebrow.textContent = p.tag;
      detailTitle.textContent = p.title;
      detailDesc.textContent = p.desc;
      detailYear.textContent = p.year;
      detailRole.textContent = p.role;
      const x = event && event.clientX ? event.clientX : innerWidth / 2;
      const y = event && event.clientY ? event.clientY : innerHeight / 2;
      dialog.style.setProperty("--cx", `${x}px`);
      dialog.style.setProperty("--cy", `${y}px`);
      if (!dialog.open) dialog.showModal();
      if (reduced) {
        dialog.classList.add("is-open");
      } else {
        requestAnimationFrame(() => dialog.classList.add("is-open"));
      }
      setTimeout(() => closeBtn.focus({ preventScroll: true }), 60);
    }

    function close() {
      dialog.classList.remove("is-open");
      clearTimeout(closedTimer);
      closedTimer = setTimeout(() => {
        if (dialog.open) dialog.close();
      }, reduced ? 0 : 300);
    }

    function onPointerDown(e) {
      if (reduced) return;
      if (e.target.closest("button")) {
        // still allow drag from a card, but do not start on controls
        if (e.target.closest(".rf-orbit__controls")) return;
      }
      down = true;
      moved = 0;
      startX = e.clientX;
      stage.classList.add("is-dragging");
    }

    function onPointerMove(e) {
      if (!down || reduced) return;
      const dx = e.clientX - startX;
      startX = e.clientX;
      moved += Math.abs(dx);
      target += dx * 0.004;
      velocity = dx * 0.0004;
    }

    function onPointerUp() {
      down = false;
      stage.classList.remove("is-dragging");
      if (moved > 8) lastDrag = Date.now();
    }

    function onWheel(e) {
      if (reduced) return;
      e.preventDefault();
      target += clamp(e.deltaY, -120, 120) * 0.0014;
    }

    function onKey(e) {
      if (reduced) return;
      if (e.key === "ArrowLeft") { target -= STEP; e.preventDefault(); }
      if (e.key === "ArrowRight") { target += STEP; e.preventDefault(); }
      if (e.key === "Enter" && document.activeElement === stage) { open(current, null); e.preventDefault(); }
    }

    stage.addEventListener("pointerdown", onPointerDown, { signal });
    window.addEventListener("pointermove", onPointerMove, { signal });
    window.addEventListener("pointerup", onPointerUp, { signal });
    window.addEventListener("pointercancel", onPointerUp, { signal });
    stage.addEventListener("wheel", onWheel, { passive: false, signal });
    stage.addEventListener("keydown", onKey, { signal });
    stage.tabIndex = 0;

    root.querySelector("[data-prev]").addEventListener("click", () => { target -= STEP; }, { signal });
    root.querySelector("[data-next]").addEventListener("click", () => { target += STEP; }, { signal });

    closeBtn.addEventListener("click", close, { signal });
    dialog.addEventListener("click", (e) => { if (e.target === dialog) close(); }, { signal });
    dialog.addEventListener("cancel", (e) => { e.preventDefault(); close(); }, { signal });

    const onReduceChange = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) {
        cancelAnimationFrame(raf);
        raf = 0;
        cards.forEach((c) => { c.style.transform = ""; c.style.filter = ""; c.style.opacity = ""; c.style.zIndex = ""; });
      } else if (!raf) {
        raf = requestAnimationFrame(frame);
      }
    };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(layout);
      ro.observe(stage);
    } else {
      window.addEventListener("resize", layout, { signal });
    }

    root.classList.toggle("is-reduced", reduced);
    layout();
    if (!reduced) {
      window.__rfStats = window.__rfStats || {};
      window.__rfStats.orbit = { cards: cards.length, get angle() { return angle; }, get frames() { return frames; } };
      raf = requestAnimationFrame(frame);
    }

    return function dispose() {
      ac.abort();
      cancelAnimationFrame(raf);
      clearTimeout(closedTimer);
      if (ro) ro.disconnect();
      if (dialog.open) dialog.close();
      dialog.classList.remove("is-open");
      root.classList.remove("is-reduced", "is-dragging");
      cardsWrap.textContent = "";
      thumbsWrap.textContent = "";
      if (window.__rfStats) window.__rfStats.orbit = null;
    };
  }

  window.RFOrbit = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="orbit-gallery"]');
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
