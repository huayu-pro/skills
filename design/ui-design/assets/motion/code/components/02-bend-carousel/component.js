/* 02-bend-carousel — 32 slices faking a cylindrical panel */
(function () {
  "use strict";

  const SLICES = 32;
  const EDGE_DEG = 17;
  const DEPTH_PX = 92;
  const ENTRY_CURVE = 1.55;

  const PROJECTS = [
    {
      title: "Bonza Boreal",
      tag: "Architecture / Landscape",
      year: "2026",
      role: "Art direction",
      desc: "A curved index for a Nordic studio. The panel is not a flat image: 32 slices rotate and recede to fake a cylinder.",
      art: "radial-gradient(circle at 32% 24%, #eaf4ff 0%, transparent 40%), radial-gradient(circle at 72% 72%, #3e6f8f 0%, transparent 58%), linear-gradient(150deg, #15222b, #070d12 78%)",
    },
    {
      title: "Amorem Vividia",
      tag: "Type / Campaign",
      year: "2025",
      role: "Design & motion",
      desc: "A campaign for a type foundry. The bend lets the type sit on a surface instead of a slide; the glitch is a 420ms state change, not a loop.",
      art: "radial-gradient(circle at 68% 20%, #ffcf9a 0%, transparent 38%), radial-gradient(circle at 28% 78%, #b43b36 0%, transparent 58%), linear-gradient(155deg, #2a1614, #100807 78%)",
    },
    {
      title: "Audio Vivaldi",
      tag: "Sound / Study",
      year: "2026",
      role: "Prototype",
      desc: "An audio-visual study. The panel behaves like a curved screen; cyan light and a 620ms entry make the surface feel physical.",
      art: "radial-gradient(circle at 30% 30%, #c8fff4 0%, transparent 40%), radial-gradient(circle at 74% 76%, #1f7f8f 0%, transparent 58%), linear-gradient(150deg, #0d252a, #061014 78%)",
    },
    {
      title: "Grain & Glass",
      tag: "Material / Research",
      year: "2024",
      role: "Motion study",
      desc: "A material study. The panel keeps a hard edge while the interior bends; the entry curve 1.55 is what makes it land instead of snap.",
      art: "radial-gradient(circle at 60% 24%, #f0e7d2 0%, transparent 38%), radial-gradient(circle at 24% 74%, #7a5b39 0%, transparent 56%), linear-gradient(150deg, #211a13, #0d0906 78%)",
    },
  ];

  const mod = (v, n) => ((v % n) + n) % n;

  function mount(root, options = {}) {
    if (!root) throw new Error("bend: root required");
    const stage = root.querySelector(".rf-bend__stage");
    const wrap = root.querySelector(".rf-bend__panels");
    const dotsWrap = root.querySelector(".rf-bend__dots");
    const countEl = root.querySelector(".rf-bend__count");
    const dialog = root.querySelector(".rf-bend__detail");
    const closeBtn = root.querySelector(".rf-bend__close");
    const detailArt = root.querySelector(".rf-bend__detail-art");
    const detailEyebrow = root.querySelector(".rf-bend__eyebrow");
    const detailTitle = root.querySelector(".rf-bend__detail h2");
    const detailDesc = root.querySelector(".rf-bend__desc");
    const detailYear = root.querySelector(".rf-bend__year");
    const detailRole = root.querySelector(".rf-bend__role");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let index = 0;
    let down = false;
    let startX = 0;
    let moved = 0;
    let dragX = 0;
    let lastWheel = 0;
    let enterTimer = 0;
    let closedTimer = 0;
    const panels = [];
    const dots = [];

    PROJECTS.forEach((p, i) => {
      const panel = document.createElement("article");
      panel.className = "rf-bend__panel";
      panel.setAttribute("role", "listitem");
      panel.setAttribute("aria-label", `${p.title} — ${p.tag}`);
      panel.style.setProperty("--curve", "1");
      panel.style.setProperty("--art", p.art);

      for (let s = 0; s < SLICES; s++) {
        const t = (s / (SLICES - 1)) * 2 - 1;
        const ry = t * -EDGE_DEG;
        const tz = -(1 - Math.cos(Math.abs(t) * Math.PI / 2)) * DEPTH_PX;
        const slice = document.createElement("div");
        slice.className = "rf-bend__slice";
        slice.style.width = `calc(${100 / SLICES}% + 1.5px)`;
        slice.style.left = `calc(${(s * 100) / SLICES}% - 0.75px)`;
        slice.style.transform = `rotateY(${ry.toFixed(3)}deg) translateZ(calc(${tz.toFixed(3)}px * var(--curve, 1)))`;
        slice.style.backgroundImage = p.art;
        slice.style.backgroundSize = `${SLICES * 100}% 100%`;
        slice.style.backgroundPosition = `${(s / (SLICES - 1)) * 100}% 0`;
        panel.appendChild(slice);
      }

      const shade = document.createElement("div");
      shade.className = "rf-bend__shade";
      shade.setAttribute("aria-hidden", "true");
      panel.appendChild(shade);

      const no = document.createElement("span");
      no.className = "rf-bend__no";
      no.textContent = `0${i + 1}`;
      panel.appendChild(no);

      const label = document.createElement("div");
      label.className = "rf-bend__label";
      label.innerHTML = `<div><h2>${p.title}</h2><p>${p.tag}</p></div><span>${p.year}</span>`;
      panel.appendChild(label);

      panel.addEventListener("click", (e) => {
        if (moved > 8) return;
        if (i === index) open(i, e);
        else go(i > index ? 1 : -1);
      }, { signal });
      wrap.appendChild(panel);
      panels.push(panel);

      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "rf-bend__dot";
      dot.setAttribute("role", "tab");
      dot.setAttribute("aria-label", `第 ${i + 1} 张：${p.title}`);
      dot.addEventListener("click", () => { index = i; setActive(); }, { signal });
      dotsWrap.appendChild(dot);
      dots.push(dot);
    });

    function setActive() {
      countEl.textContent = `0${index + 1} / 0${PROJECTS.length}`;
      panels.forEach((panel, i) => {
        panel.classList.remove("is-active", "is-prev", "is-next", "is-far");
        panel.style.setProperty("--drag", "0px");
        panel.style.setProperty("--drag-ry", "0deg");
        const d = mod(i - index, PROJECTS.length);
        if (d === 0) panel.classList.add("is-active");
        else if (d === 1) panel.classList.add("is-next");
        else if (d === PROJECTS.length - 1) panel.classList.add("is-prev");
        else panel.classList.add("is-far");
      });
      dots.forEach((d, i) => {
        d.classList.toggle("is-active", i === index);
        d.setAttribute("aria-selected", i === index ? "true" : "false");
      });
      const active = panels[index];
      active.classList.add("is-entering");
      active.style.setProperty("--curve", String(ENTRY_CURVE));
      clearTimeout(enterTimer);
      enterTimer = setTimeout(() => {
        active.style.setProperty("--curve", "1");
        active.classList.remove("is-entering");
      }, 760);
    }

    function go(dir) {
      index = mod(index + dir, PROJECTS.length);
      setActive();
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
      if (e.target.closest(".rf-bend__controls")) return;
      down = true;
      moved = 0;
      startX = e.clientX;
      dragX = 0;
      stage.classList.add("is-dragging");
    }

    function onPointerMove(e) {
      if (!down || reduced) return;
      const dx = e.clientX - startX;
      moved += Math.abs(dx - dragX);
      dragX = dx;
      const active = panels[index];
      if (active) {
        active.style.setProperty("--drag", `${Math.max(-120, Math.min(120, dx * 0.35))}px`);
        active.style.setProperty("--drag-ry", `${Math.max(-6, Math.min(6, dx * -0.02))}deg`);
      }
    }

    function onPointerUp() {
      if (!down) return;
      down = false;
      stage.classList.remove("is-dragging");
      const active = panels[index];
      if (!active) return;
      if (Math.abs(dragX) > 40) {
        go(dragX < 0 ? 1 : -1);
      } else {
        active.style.setProperty("--drag", "0px");
        active.style.setProperty("--drag-ry", "0deg");
      }
      dragX = 0;
    }

    function onWheel(e) {
      if (reduced) return;
      const now = Date.now();
      if (now - lastWheel < 620) return;
      if (Math.abs(e.deltaY) < 4) return;
      e.preventDefault();
      lastWheel = now;
      go(e.deltaY > 0 ? 1 : -1);
    }

    function onKey(e) {
      if (e.key === "ArrowLeft") { go(-1); e.preventDefault(); }
      if (e.key === "ArrowRight") { go(1); e.preventDefault(); }
      if (e.key === "Enter" && document.activeElement === stage) { open(index, null); e.preventDefault(); }
    }

    stage.addEventListener("pointerdown", onPointerDown, { signal });
    window.addEventListener("pointermove", onPointerMove, { signal });
    window.addEventListener("pointerup", onPointerUp, { signal });
    window.addEventListener("pointercancel", onPointerUp, { signal });
    stage.addEventListener("wheel", onWheel, { passive: false, signal });
    stage.addEventListener("keydown", onKey, { signal });
    stage.tabIndex = 0;

    root.querySelector("[data-prev]").addEventListener("click", () => go(-1), { signal });
    root.querySelector("[data-next]").addEventListener("click", () => go(1), { signal });

    closeBtn.addEventListener("click", close, { signal });
    dialog.addEventListener("click", (e) => { if (e.target === dialog) close(); }, { signal });
    dialog.addEventListener("cancel", (e) => { e.preventDefault(); close(); }, { signal });

    const onReduceChange = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
    };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    root.classList.toggle("is-reduced", reduced);
    setActive();

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.bend = {
      get index() { return index; },
      get panels() { return panels.length; },
      get animations() { return document.getAnimations().length; },
    };

    return function dispose() {
      ac.abort();
      clearTimeout(enterTimer);
      clearTimeout(closedTimer);
      if (dialog.open) dialog.close();
      dialog.classList.remove("is-open");
      root.classList.remove("is-reduced", "is-dragging");
      wrap.textContent = "";
      dotsWrap.textContent = "";
      panels.length = 0;
      dots.length = 0;
      if (window.__rfStats) window.__rfStats.bend = null;
    };
  }

  window.RFBend = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="bend-carousel"]');
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
