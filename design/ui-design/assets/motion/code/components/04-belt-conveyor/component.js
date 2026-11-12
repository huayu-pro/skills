/* 04-belt-conveyor — speed-driven belt with exponential friction */
(function () {
  "use strict";

  const N = 11;
  const SPACING = 300;
  const TOTAL = N * SPACING;
  const BASE = 62;
  const MAX = 900;
  const FRICTION = 1.1;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const mod = (v, n) => ((v % n) + n) % n;

  const PROJECTS = [
    { title: "Ritual Objects", tag: "Identity", year: "2026", role: "Brand system", desc: "A belt of objects for a ceramics studio. Speed, not scroll position, decides what is near.", art: "radial-gradient(circle at 30% 22%, #e8d6b8 0%, transparent 40%), radial-gradient(circle at 72% 74%, #6f4a2e 0%, transparent 58%), linear-gradient(150deg, #241811, #0d0805 78%)" },
    { title: "Warm Index", tag: "Editorial", year: "2025", role: "Art direction", desc: "An index that behaves like a physical belt: when you push, it keeps moving, then settles back to a resting speed.", art: "radial-gradient(circle at 68% 20%, #ffd7a1 0%, transparent 38%), radial-gradient(circle at 28% 78%, #a8461f 0%, transparent 58%), linear-gradient(155deg, #2a140c, #0f0704 78%)" },
    { title: "Soft Grid", tag: "Digital", year: "2026", role: "Product design", desc: "A portfolio for a product studio. Cards rotate slightly with distance; the belt is the only layout.", art: "radial-gradient(circle at 34% 28%, #cfe8ff 0%, transparent 40%), radial-gradient(circle at 74% 76%, #2b4f79 0%, transparent 58%), linear-gradient(150deg, #102033, #070d15 78%)" },
    { title: "Field Signal", tag: "Print", year: "2024", role: "Editorial", desc: "A print archive. The wrap is seamless: every card comes back after half a belt.", art: "radial-gradient(circle at 64% 24%, #d9f2c8 0%, transparent 38%), radial-gradient(circle at 26% 74%, #3f6b3a 0%, transparent 58%), linear-gradient(150deg, #122013, #070d08 78%)" },
    { title: "Night Shift", tag: "Digital", year: "2025", role: "Interface", desc: "A night-mode product page. The belt slows on hover, then resumes; no scroll hijack.", art: "radial-gradient(circle at 30% 24%, #d8c7ff 0%, transparent 40%), radial-gradient(circle at 74% 76%, #4a2f80 0%, transparent 58%), linear-gradient(150deg, #1a1230, #0a0614 78%)" },
    { title: "Paper Trail", tag: "Print", year: "2026", role: "Editorial", desc: "A paper-led identity. Each card keeps a visible index so the belt never feels like a slot machine.", art: "radial-gradient(circle at 68% 22%, #fff3d6 0%, transparent 38%), radial-gradient(circle at 27% 76%, #8a6a3f 0%, transparent 58%), linear-gradient(150deg, #251b10, #0e0905 78%)" },
    { title: "Mono Run", tag: "Identity", year: "2024", role: "Brand", desc: "A monochrome identity. The belt's rotation is the only motion; no per-card hover trick.", art: "radial-gradient(circle at 34% 24%, #f1f1ee 0%, transparent 38%), radial-gradient(circle at 72% 76%, #5b5b57 0%, transparent 58%), linear-gradient(150deg, #222222, #0b0b0b 78%)" },
    { title: "Green Room", tag: "Digital", year: "2025", role: "Product", desc: "A backstage tool. The belt is a browsing aid: drag to push, release to coast.", art: "radial-gradient(circle at 66% 26%, #c8ffe8 0%, transparent 38%), radial-gradient(circle at 28% 74%, #1f7a5a 0%, transparent 58%), linear-gradient(150deg, #0d2820, #06110d 78%)" },
    { title: "Copper Line", tag: "Identity", year: "2026", role: "Brand", desc: "A copper-toned identity. The card's rotation is proportional to distance, so the belt reads as a curve.", art: "radial-gradient(circle at 32% 22%, #ffd9b8 0%, transparent 40%), radial-gradient(circle at 74% 76%, #9a4a24 0%, transparent 58%), linear-gradient(150deg, #2a160d, #100805 78%)" },
    { title: "Quiet Type", tag: "Editorial", year: "2024", role: "Type", desc: "A type specimen. The belt is slowed down to 62 px/s so the reader can read the labels.", art: "radial-gradient(circle at 70% 24%, #f4efe4 0%, transparent 38%), radial-gradient(circle at 26% 76%, #7d7466 0%, transparent 58%), linear-gradient(150deg, #211e18, #0d0b08 78%)" },
    { title: "Blue Hour", tag: "Digital", year: "2026", role: "Motion study", desc: "A blue-hour study. The drag boost decays with exp(-dt × 1.1); release long enough and it returns to resting speed.", art: "radial-gradient(circle at 34% 26%, #c8e4ff 0%, transparent 40%), radial-gradient(circle at 72% 74%, #1e4f7a 0%, transparent 58%), linear-gradient(150deg, #0d1c2b, #060b11 78%)" },
  ];

  function mount(root, options = {}) {
    if (!root) throw new Error("belt: root required");
    const stage = root.querySelector(".rf-belt__stage");
    const track = root.querySelector(".rf-belt__track");
    const countEl = root.querySelector(".rf-belt__count");
    const dialog = root.querySelector(".rf-belt__detail");
    const closeBtn = root.querySelector(".rf-belt__close");
    const detailArt = root.querySelector(".rf-belt__detail-art");
    const detailEyebrow = root.querySelector(".rf-belt__eyebrow");
    const detailTitle = root.querySelector(".rf-belt__detail h2");
    const detailDesc = root.querySelector(".rf-belt__desc");
    const detailYear = root.querySelector(".rf-belt__year");
    const detailRole = root.querySelector(".rf-belt__role");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let raf = 0;
    let last = performance.now();
    let offset = 0;
    let boost = 0;
    let down = false;
    let startX = 0;
    let moved = 0;
    let lastDrag = 0;
    let front = 0;
    let frames = 0;
    let closedTimer = 0;
    const cards = [];

    PROJECTS.forEach((p, i) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "rf-belt__card";
      card.setAttribute("role", "listitem");
      card.setAttribute("aria-label", `${p.title} — ${p.tag}`);
      card.style.setProperty("--art", p.art);
      card.innerHTML =
        '<span class="rf-belt__art" aria-hidden="true"></span>' +
        '<span class="rf-belt__meta">' +
        `<span class="rf-belt__no">0${i + 1}</span>` +
        `<span class="rf-belt__title">${p.title}</span>` +
        `<span class="rf-belt__tag">${p.tag} · ${p.year}</span>` +
        "</span>";
      card.addEventListener("click", (e) => {
        if (moved > 8 && Date.now() - lastDrag < 350) return;
        open(i, e);
      }, { signal });
      track.appendChild(card);
      cards.push(card);
    });

    function layout() {
      if (reduced) return;
      for (let i = 0; i < cards.length; i++) {
        let x = mod(i * SPACING + offset, TOTAL);
        if (x > TOTAL / 2) x -= TOTAL;
        const dist = Math.abs(x);
        const vw = stage.clientWidth || innerWidth;
        const scale = Math.max(0.42, 1 - dist / (vw * 1.05));
        const rot = (x / vw) * -26;
        const rise = Math.min(1, dist / vw) * 26;
        const fadeStart = vw * 0.62;
        const opacity = dist < fadeStart ? 1 : Math.max(0.22, 1 - (dist - fadeStart) / (vw * 0.5));
        const z = Math.round(100 - dist / 10);
        const card = cards[i];
        card.style.transform = `translate(-50%, -50%) translate3d(${x.toFixed(2)}px, ${rise.toFixed(2)}px, 0) scale(${scale.toFixed(3)}) rotate(${rot.toFixed(2)}deg)`;
        card.style.opacity = opacity.toFixed(3);
        card.style.zIndex = String(z);
      }
      let best = 0;
      let bestD = Infinity;
      for (let i = 0; i < cards.length; i++) {
        let x = mod(i * SPACING + offset, TOTAL);
        if (x > TOTAL / 2) x -= TOTAL;
        if (Math.abs(x) < bestD) { bestD = Math.abs(x); best = i; }
      }
      if (best !== front) {
        front = best;
        countEl.textContent = `0${best + 1} / ${N}`;
      }
    }

    function frame(now) {
      if (reduced) return;
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      boost *= Math.exp(-dt * FRICTION);
      if (Math.abs(boost) < 0.4) boost = 0;
      const speed = BASE + boost;
      offset -= speed * dt;
      offset = mod(offset, TOTAL);
      layout();
      frames++;
      raf = requestAnimationFrame(frame);
    }

    function kick(v) {
      boost = clamp(boost + v, -BASE + 10, MAX - BASE);
    }

    function open(i, event) {
      const p = PROJECTS[i];
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
      if (reduced) dialog.classList.add("is-open");
      else requestAnimationFrame(() => dialog.classList.add("is-open"));
      setTimeout(() => closeBtn.focus({ preventScroll: true }), 60);
    }

    function close() {
      dialog.classList.remove("is-open");
      clearTimeout(closedTimer);
      closedTimer = setTimeout(() => { if (dialog.open) dialog.close(); }, reduced ? 0 : 300);
    }

    function onPointerDown(e) {
      if (reduced) return;
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
      offset += dx;
      boost = clamp(boost + Math.abs(dx) * 3, -BASE + 10, MAX - BASE);
      offset = mod(offset, TOTAL);
      layout();
    }

    function onPointerUp() {
      if (!down) return;
      down = false;
      stage.classList.remove("is-dragging");
      if (moved > 8) lastDrag = Date.now();
      kick(boost * 0.4);
    }

    function onWheel(e) {
      if (reduced) return;
      if (Math.abs(e.deltaY) < 2) return;
      e.preventDefault();
      kick(clamp(e.deltaY, -120, 120) * 0.9);
    }

    function onKey(e) {
      if (reduced) return;
      if (e.key === "ArrowLeft") { kick(-240); e.preventDefault(); }
      if (e.key === "ArrowRight") { kick(240); e.preventDefault(); }
      if (e.key === "Enter" && document.activeElement === stage) { open(front, null); e.preventDefault(); }
    }

    stage.addEventListener("pointerdown", onPointerDown, { signal });
    window.addEventListener("pointermove", onPointerMove, { signal });
    window.addEventListener("pointerup", onPointerUp, { signal });
    window.addEventListener("pointercancel", onPointerUp, { signal });
    stage.addEventListener("wheel", onWheel, { passive: false, signal });
    stage.addEventListener("keydown", onKey, { signal });
    stage.tabIndex = 0;

    closeBtn.addEventListener("click", close, { signal });
    dialog.addEventListener("click", (e) => { if (e.target === dialog) close(); }, { signal });
    dialog.addEventListener("cancel", (e) => { e.preventDefault(); close(); }, { signal });

    const onReduceChange = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) {
        cancelAnimationFrame(raf);
        raf = 0;
      } else if (!raf) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    root.classList.toggle("is-reduced", reduced);
    layout();

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.belt = {
      get offset() { return offset; },
      get boost() { return boost; },
      get speed() { return BASE + boost; },
      get frames() { return frames; },
      get cards() { return cards.length; },
    };

    if (!reduced) raf = requestAnimationFrame(frame);

    return function dispose() {
      ac.abort();
      cancelAnimationFrame(raf);
      clearTimeout(closedTimer);
      if (dialog.open) dialog.close();
      dialog.classList.remove("is-open");
      root.classList.remove("is-reduced", "is-dragging");
      track.textContent = "";
      cards.length = 0;
      if (window.__rfStats) window.__rfStats.belt = null;
    };
  }

  window.RFBelt = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="belt-conveyor"]');
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
