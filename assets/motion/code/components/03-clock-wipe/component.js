/* 03-clock-wipe — draggable clock + circular theme wipe + lift sheet */
(function () {
  "use strict";

  const TICKS = 60;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const mod = (v, n) => ((v % n) + n) % n;

  function mount(root, options = {}) {
    if (!root) throw new Error("clock: root required");
    const dial = root.querySelector(".rf-clock__dial");
    const ticks = root.querySelector(".rf-clock__ticks");
    const timeEl = root.querySelector(".rf-clock__time");
    const dateEl = root.querySelector(".rf-clock__date");
    const sheet = root.querySelector(".rf-clock__sheet");
    const themeBtn = root.querySelector(".rf-clock__theme");
    const themeText = root.querySelector(".rf-clock__theme-text");
    const wipe = root.querySelector(".rf-clock__wipe");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let minutes = 10 * 60 + 10;
    let seconds = 30;
    let down = false;
    let startMin = minutes;
    let startAngle = 0;
    let moved = 0;
    let lift = 0;
    let themeTimer = 0;
    let closeTimer = 0;

    for (let i = 0; i < TICKS; i++) {
      const a = (i / TICKS) * 360;
      const t = document.createElement("span");
      t.className = "rf-clock__tick" + (i % 5 === 0 ? " is-major" : "");
      t.style.left = `${50 + Math.sin((a * Math.PI) / 180) * 46}%`;
      t.style.top = `${50 - Math.cos((a * Math.PI) / 180) * 46}%`;
      t.style.transform = `translate(-50%, -50%) rotate(${a}deg)`;
      ticks.appendChild(t);
    }

    function setClock() {
      const h = Math.floor(minutes / 60) % 12;
      const m = minutes % 60;
      const s = seconds;
      dial.style.setProperty("--h", `${(h + m / 60) * 30}deg`);
      dial.style.setProperty("--m", `${m * 6}deg`);
      dial.style.setProperty("--s", `${s * 6}deg`);
      timeEl.textContent = `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
      const day = 1 + Math.floor(minutes / 1440);
      const month = 1 + (Math.floor(day / 30) % 12);
      const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
      dateEl.textContent = `${String(((day - 1) % 30) + 1).padStart(2, "0")} ${months[month - 1]} 2026`;
    }

    function angleOf(e) {
      const r = dial.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      return (Math.atan2(e.clientY - cy, e.clientX - cx) * 180) / Math.PI + 90;
    }

    function setFromAngle(angle) {
      const norm = mod(angle, 360);
      minutes = mod((norm / 360) * 720, 720);
      seconds = mod(norm * 2, 60);
      setClock();
    }

    function onPointerDown(e) {
      if (e.target.closest(".rf-clock__theme")) return;
      down = true;
      moved = 0;
      startAngle = angleOf(e);
      setFromAngle(startAngle);
      startMin = minutes;
      try { dial.setPointerCapture(e.pointerId); } catch (_) {}
    }

    function onPointerMove(e) {
      if (!down) return;
      const a = angleOf(e);
      let delta = a - startAngle;
      delta = ((delta + 180) % 360 + 360) % 360 - 180;
      moved += Math.abs(delta);
      const next = mod(startMin + (delta / 360) * 720, 720);
      minutes = next;
      seconds = mod(a * 2, 60);
      setClock();
    }

    function onPointerUp() {
      down = false;
    }

    function onWheel(e) {
      if (reduced) return;
      if (Math.abs(e.deltaY) < 2) return;
      e.preventDefault();
      lift = clamp(lift + e.deltaY / 1200, 0, 1);
      sheet.style.setProperty("--lift", lift.toFixed(3));
    }

    function toggleTheme(event) {
      const isDark = root.classList.contains("is-dark");
      const nextDark = !isDark;
      const x = event && event.clientX ? event.clientX : innerWidth / 2;
      const y = event && event.clientY ? event.clientY : 80;
      wipe.style.setProperty("--cx", `${x}px`);
      wipe.style.setProperty("--cy", `${y}px`);
      wipe.style.background = nextDark ? "#0c0d10" : "#f1ede3";

      const apply = () => {
        root.classList.toggle("is-dark", nextDark);
        themeBtn.setAttribute("aria-pressed", nextDark ? "true" : "false");
        themeText.textContent = nextDark ? "Light" : "Dark";
      };

      if (reduced) {
        apply();
        return;
      }
      root.classList.add("is-wiping");
      clearTimeout(themeTimer);
      themeTimer = setTimeout(() => {
        apply();
        wipe.style.transition = "none";
        root.classList.remove("is-wiping");
        void wipe.offsetWidth;
        wipe.style.transition = "";
      }, 680);
    }

    function onKey(e) {
      if (e.key === "ArrowUp") { minutes = mod(minutes + (e.shiftKey ? 10 : 1), 720); setClock(); e.preventDefault(); }
      if (e.key === "ArrowDown") { minutes = mod(minutes - (e.shiftKey ? 10 : 1), 720); setClock(); e.preventDefault(); }
      if (e.key === " " || e.code === "Space") { toggleTheme(e); e.preventDefault(); }
      if (e.key.toLowerCase() === "f") { lift = lift > 0.5 ? 0 : 1; sheet.style.setProperty("--lift", lift.toFixed(3)); }
    }

    dial.addEventListener("pointerdown", onPointerDown, { signal });
    window.addEventListener("pointermove", onPointerMove, { signal });
    window.addEventListener("pointerup", onPointerUp, { signal });
    window.addEventListener("pointercancel", onPointerUp, { signal });
    root.querySelector(".rf-clock__stage").addEventListener("wheel", onWheel, { passive: false, signal });
    dial.addEventListener("keydown", onKey, { signal });
    dial.tabIndex = 0;
    themeBtn.addEventListener("click", toggleTheme, { signal });

    const onReduceChange = () => { reduced = reduceMQ.matches; };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    root.classList.toggle("is-reduced", reduced);
    setClock();
    sheet.style.setProperty("--lift", "0");

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.clock = {
      get minutes() { return minutes; },
      get lift() { return lift; },
      get theme() { return root.classList.contains("is-dark") ? "dark" : "light"; },
      get animations() { return document.getAnimations().length; },
    };

    return function dispose() {
      ac.abort();
      clearTimeout(themeTimer);
      clearTimeout(closeTimer);
      root.classList.remove("is-wiping");
      root.classList.remove("is-dark", "is-reduced");
      ticks.textContent = "";
      if (window.__rfStats) window.__rfStats.clock = null;
    };
  }

  window.RFClock = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="clock-wipe"]');
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
