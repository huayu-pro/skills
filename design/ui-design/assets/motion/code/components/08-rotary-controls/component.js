/* 08-rotary-controls — 270-degree rotary knobs + physical switch */
(function () {
  "use strict";

  const SWEEP = 270;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function mount(root, options = {}) {
    if (!root) throw new Error("rotary: root required");
    const knobs = [...root.querySelectorAll("[data-knob]")];
    const themeBtn = root.querySelector(".rf-rotary__theme");
    const themeLabel = root.querySelector("[data-theme-label]");
    const switchBtn = root.querySelector(".rf-rotary__switch");
    const switchLabel = root.querySelector(".rf-rotary__switch-label");
    const openBtn = root.querySelector("[data-open]");
    const dialog = root.querySelector(".rf-rotary__modal");
    const closeBtn = root.querySelector(".rf-rotary__close");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let lightsOn = false;
    let closedTimer = 0;
    const state = {};

    knobs.forEach((wrap) => {
      const name = wrap.dataset.knob;
      const min = Number(wrap.dataset.min || 0);
      const max = Number(wrap.dataset.max || 100);
      const dial = wrap.querySelector(".rf-rotary__dial");
      const pointer = wrap.querySelector(".rf-rotary__pointer");
      const out = wrap.querySelector(".rf-rotary__value");
      const ticks = wrap.querySelector(".rf-rotary__ticks");
      let value = Number(wrap.dataset.value || 0);
      let down = false;
      let startValue = 0;
      let startAngle = 0;
      let startX = 0;
      let startY = 0;

      for (let i = 0; i <= 10; i++) {
        const a = -SWEEP / 2 + (i / 10) * SWEEP;
        const t = document.createElement("span");
        t.className = "rf-rotary__tick";
        t.style.left = `${50 + Math.sin((a * Math.PI) / 180) * 42}%`;
        t.style.top = `${50 - Math.cos((a * Math.PI) / 180) * 42}%`;
        t.style.transform = `translate(-50%, -50%) rotate(${a}deg)`;
        ticks.appendChild(t);
      }

      function angleOf(e) {
        const r = dial.getBoundingClientRect();
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        return (Math.atan2(e.clientY - cy, e.clientX - cx) * 180) / Math.PI + 90;
      }

      function setValue(v, announce = true) {
        value = clamp(v, min, max);
        const a = -SWEEP / 2 + ((value - min) / (max - min)) * SWEEP;
        dial.style.setProperty("--angle", `${a.toFixed(2)}deg`);
        dial.setAttribute("aria-valuenow", String(Math.round(value)));
        out.textContent = String(Math.round(value));
        wrap.dataset.value = String(Math.round(value));
        state[name] = value;
        if (name === "level") root.style.setProperty("--level", (value / 100).toFixed(3));
        const sum = root.querySelector(`[data-sum="${name}"]`);
        if (sum) sum.textContent = String(Math.round(value));
      }

      function onDown(e) {
        down = true;
        startValue = value;
        startAngle = angleOf(e);
        startX = e.clientX;
        startY = e.clientY;
        try { dial.setPointerCapture(e.pointerId); } catch (_) {}
        e.preventDefault();
      }

      function onMove(e) {
        if (!down) return;
        const r = dial.getBoundingClientRect();
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        if (Math.hypot(e.clientX - cx, e.clientY - cy) < 12) {
          setValue(startValue + (dx - dy) / 5);
        } else {
          let delta = angleOf(e) - startAngle;
          delta = ((delta + 180) % 360 + 360) % 360 - 180;
          setValue(startValue + delta / (SWEEP / (max - min)));
        }
      }

      function onUp() { down = false; }

      dial.addEventListener("pointerdown", onDown, { signal });
      window.addEventListener("pointermove", onMove, { signal });
      window.addEventListener("pointerup", onUp, { signal });
      window.addEventListener("pointercancel", onUp, { signal });
      dial.addEventListener("wheel", (e) => {
        if (reduced) return;
        e.preventDefault();
        setValue(value + (e.deltaY > 0 ? 4 : -4));
      }, { passive: false, signal });
      dial.addEventListener("keydown", (e) => {
        if (e.key === "ArrowUp" || e.key === "ArrowRight") { setValue(value + 4); e.preventDefault(); }
        if (e.key === "ArrowDown" || e.key === "ArrowLeft") { setValue(value - 4); e.preventDefault(); }
        if (e.key === "Home") { setValue(min); e.preventDefault(); }
        if (e.key === "End") { setValue(max); e.preventDefault(); }
      }, { signal });

      setValue(value, false);
    });

    function setLights(on) {
      lightsOn = on;
      root.classList.toggle("is-light", on);
      themeBtn.setAttribute("aria-pressed", on ? "true" : "false");
      themeLabel.textContent = on ? "Light" : "Dark";
      switchBtn.setAttribute("aria-pressed", on ? "true" : "false");
      switchLabel.textContent = on ? "Lights on" : "Lights off";
      const sum = root.querySelector('[data-sum="lights"]');
      if (sum) sum.textContent = on ? "on" : "off";
    }

    themeBtn.addEventListener("click", (e) => setLights(!lightsOn, e), { signal });
    switchBtn.addEventListener("click", (e) => setLights(!lightsOn, e), { signal });

    openBtn.addEventListener("click", () => {
      if (!dialog.open) dialog.showModal();
      setTimeout(() => closeBtn.focus({ preventScroll: true }), 40);
    }, { signal });
    closeBtn.addEventListener("click", () => {
      dialog.close();
    }, { signal });
    dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); }, { signal });

    const onReduceChange = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
    };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    root.classList.toggle("is-reduced", reduced);
    setLights(false);

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.rotary = {
      get values() { return { ...state }; },
      get lights() { return lightsOn ? "on" : "off"; },
      get knobs() { return knobs.length; },
      get animations() { return document.getAnimations().length; },
    };

    return function dispose() {
      ac.abort();
      clearTimeout(closedTimer);
      if (dialog.open) dialog.close();
      root.classList.remove("is-light", "is-reduced");
      root.querySelectorAll(".rf-rotary__ticks").forEach((t) => { t.textContent = ""; });
      if (window.__rfStats) window.__rfStats.rotary = null;
    };
  }

  window.RFRotary = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="rotary-controls"]');
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
