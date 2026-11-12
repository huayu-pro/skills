/* 07-color-lab — 6-step scales, WCAG contrast, HSL picker */
(function () {
  "use strict";

  const BASES = [
    { name: "Graphite", hex: "#3B3A40" },
    { name: "Vermilion", hex: "#FF6038" },
    { name: "Amber", hex: "#FFA411" },
    { name: "Blue", hex: "#2E8CFF" },
  ];
  const LIGHTS = [94, 82, 68, 54, 38, 22];
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function hexToRgb(hex) {
    const h = hex.replace("#", "");
    const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
  }
  function rgbToHex(r, g, b) {
    const to = (v) => clamp(Math.round(v), 0, 255).toString(16).padStart(2, "0");
    return `#${to(r)}${to(g)}${to(b)}`.toUpperCase();
  }
  function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h = 0, s = 0;
    const l = (max + min) / 2;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h /= 6;
    }
    return { h: h * 360, s: s * 100, l: l * 100 };
  }
  function hslToHex(h, s, l) {
    h = ((h % 360) + 360) % 360;
    s = clamp(s, 0, 100) / 100;
    l = clamp(l, 0, 100) / 100;
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = l - c / 2;
    let r = 0, g = 0, b = 0;
    if (h < 60) [r, g, b] = [c, x, 0];
    else if (h < 120) [r, g, b] = [x, c, 0];
    else if (h < 180) [r, g, b] = [0, c, x];
    else if (h < 240) [r, g, b] = [0, x, c];
    else if (h < 300) [r, g, b] = [x, 0, c];
    else [r, g, b] = [c, 0, x];
    return rgbToHex((r + m) * 255, (g + m) * 255, (b + m) * 255);
  }
  function luminance(hex) {
    const { r, g, b } = hexToRgb(hex);
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  }
  function contrast(a, b) {
    const l1 = luminance(a), l2 = luminance(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }
  function readable(bg) {
    return contrast(bg, "#FFFFFF") >= contrast(bg, "#000000") ? "#FFFFFF" : "#000000";
  }
  function grade(c) {
    if (c >= 7) return "AAA";
    if (c >= 4.5) return "AA";
    if (c >= 3) return "AA large";
    return "—";
  }

  function mount(root, options = {}) {
    if (!root) throw new Error("color: root required");
    const basesWrap = root.querySelector(".rf-color__bases");
    const scalesWrap = root.querySelector(".rf-color__scales");
    const auditWrap = root.querySelector(".rf-color__audit");
    const big = root.querySelector(".rf-color__big");
    const hexEl = root.querySelector(".rf-color__hex");
    const bigMeta = root.querySelector(".rf-color__big-meta");
    const codeEl = root.querySelector(".rf-color__code");
    const picker = root.querySelector(".rf-color__picker");
    const copyBtn = root.querySelector(".rf-color__copy");
    const contrastInput = root.querySelector("[data-contrast]");
    const spreadInput = root.querySelector("[data-spread]");
    const hueInput = root.querySelector("[data-hue]");
    const outContrast = root.querySelector('[data-out="contrast"]');
    const outSpread = root.querySelector('[data-out="spread"]');
    const outHue = root.querySelector('[data-out="hue"]');
    const tabs = [...root.querySelectorAll("[data-tab]")];
    const panels = [...root.querySelectorAll("[data-panel]")];
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let baseIndex = 1;
    let customBase = null;
    let step = 2;
    let spread = 1;
    let hueShift = 0;
    let renders = 0;
    let pickerX = 0.8;
    let pickerY = 0.42;
    let copiedTimer = 0;

    BASES.forEach((b, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "rf-color__base" + (i === baseIndex ? " is-active" : "");
      btn.style.background = b.hex;
      btn.setAttribute("role", "radio");
      btn.setAttribute("aria-checked", i === baseIndex ? "true" : "false");
      btn.setAttribute("aria-label", b.name);
      btn.addEventListener("click", () => {
        baseIndex = i;
        customBase = null;
        pickerX = 0.8;
        pickerY = 0.42;
        render();
      }, { signal });
      basesWrap.appendChild(btn);
    });

    function currentBase() {
      return customBase || BASES[baseIndex].hex;
    }

    function makeScale(baseHex) {
      const base = rgbToHsl(...Object.values(hexToRgb(baseHex)));
      return LIGHTS.map((L, i) => {
        const t = (i - 2.5) / 3;
        const h = base.h + hueShift + t * 10;
        const sat = base.s * (1 - Math.abs(50 - L) / 180) * 1.05 * spread;
        return hslToHex(h, sat, L);
      });
    }

    function render() {
      renders++;
      const baseHex = currentBase();
      const scale = makeScale(baseHex);
      const activeHex = scale[step] || baseHex;

      big.style.background = activeHex;
      hexEl.textContent = activeHex;
      bigMeta.textContent = `${customBase ? "Custom" : BASES[baseIndex].name} · step 0${step + 1}`;
      hexEl.style.color = "#FFFFFF";
      root.querySelector(".rf-color__big-meta").style.color = "rgba(255,255,255,.72)";
      root.querySelector(".rf-color__big .rf-color__eyebrow").style.color = "rgba(255,255,255,.7)";

      basesWrap.querySelectorAll(".rf-color__base").forEach((b, i) => {
        const on = !customBase && i === baseIndex;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-checked", on ? "true" : "false");
      });

      scalesWrap.textContent = "";
      let idx = 0;
      for (let b = 0; b < BASES.length; b++) {
        const bHex = customBase || BASES[b].hex;
        const bScale = makeScale(bHex);
        for (let s = 0; s < bScale.length; s++) {
          const hex = bScale[s];
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "rf-color__swatch" + (!customBase && b === baseIndex && s === step ? " is-active" : "");
          btn.style.background = hex;
          btn.style.color = readable(hex);
          const cw = contrast(hex, "#FFFFFF").toFixed(1);
          const cb = contrast(hex, "#000000").toFixed(1);
          btn.innerHTML = `<span>${hex}</span><small>${Math.max(cw, cb)}:1</small>`;
          btn.setAttribute("aria-label", `${BASES[b].name} step ${s + 1} ${hex}`);
          btn.addEventListener("click", () => {
            baseIndex = b;
            customBase = null;
            step = s;
            render();
          }, { signal });
          scalesWrap.appendChild(btn);
          if (!reduced) {
            btn.animate(
              [{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }],
              { duration: 360, delay: idx * 20, easing: "cubic-bezier(.2,.8,.2,1)", fill: "both" }
            );
          }
          idx++;
        }
      }

      auditWrap.textContent = "";
      scale.forEach((hex, i) => {
        const cw = contrast(hex, "#FFFFFF");
        const cb = contrast(hex, "#000000");
        const item = document.createElement("div");
        item.className = "rf-color__audit-item";
        const c = Math.max(cw, cb);
        item.innerHTML = `<strong>${hex}</strong>white ${cw.toFixed(1)} · black ${cb.toFixed(1)}<br><em>${grade(c)}</em>`;
        auditWrap.appendChild(item);
      });

      const vars = BASES.map((b) => {
        const sc = makeScale(b.hex);
        return `--color-${b.name.toLowerCase()}-${sc.map((h, i) => `${i + 1}:${h}`).join(", ")}`;
      }).join("\n");
      codeEl.textContent = `:root {\n${vars}\n}\n\n/* selected */\n--color-selected: ${activeHex}; /* contrast ${Math.max(contrast(activeHex, "#fff"), contrast(activeHex, "#000")).toFixed(2)}:1 */`;

      drawPicker();
      if (window.__rfStats && window.__rfStats.color) {
        // getters read live values
      }
    }

    function drawPicker() {
      const ctx = picker.getContext("2d");
      if (!ctx) return;
      const w = picker.width, h = picker.height;
      const hue = rgbToHsl(...Object.values(hexToRgb(currentBase()))).h + hueShift;
      const gx = ctx.createLinearGradient(0, 0, w, 0);
      gx.addColorStop(0, "#FFFFFF");
      gx.addColorStop(1, hslToHex(hue, 100, 50));
      ctx.fillStyle = gx;
      ctx.fillRect(0, 0, w, h);
      const gy = ctx.createLinearGradient(0, 0, 0, h);
      gy.addColorStop(0, "rgba(0,0,0,0)");
      gy.addColorStop(1, "rgba(0,0,0,1)");
      ctx.fillStyle = gy;
      ctx.fillRect(0, 0, w, h);
      const hx = pickerX * w, hy = pickerY * h;
      ctx.beginPath();
      ctx.arc(hx, hy, 7, 0, Math.PI * 2);
      ctx.strokeStyle = "#FFFFFF";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(hx, hy, 9, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(0,0,0,.55)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    function pickFromEvent(e) {
      const r = picker.getBoundingClientRect();
      pickerX = clamp((e.clientX - r.left) / r.width, 0, 1);
      pickerY = clamp((e.clientY - r.top) / r.height, 0, 1);
      const hue = rgbToHsl(...Object.values(hexToRgb(BASES[baseIndex].hex))).h + hueShift;
      const light = (1 - pickerY) * (1 - pickerX * 0.5) * 100;
      const sat = pickerX * 100;
      customBase = hslToHex(hue, sat, light);
      step = 2;
      render();
    }

    picker.addEventListener("pointerdown", (e) => {
      picker.setPointerCapture(e.pointerId);
      pickFromEvent(e);
    }, { signal });
    picker.addEventListener("pointermove", (e) => {
      if (e.buttons) pickFromEvent(e);
    }, { signal });

    function syncSpreadFromContrast() {
      const c = Number(contrastInput.value);
      spread = 0.72 + ((c - 3) / 9) * 0.56;
      spreadInput.value = spread.toFixed(2);
      outContrast.textContent = c.toFixed(1);
      outSpread.textContent = spread.toFixed(2);
      render();
    }
    function syncContrastFromSpread() {
      spread = Number(spreadInput.value);
      const c = 3 + ((spread - 0.72) / 0.56) * 9;
      contrastInput.value = c.toFixed(1);
      outContrast.textContent = c.toFixed(1);
      outSpread.textContent = spread.toFixed(2);
      render();
    }
    contrastInput.addEventListener("input", syncSpreadFromContrast, { signal });
    spreadInput.addEventListener("input", syncContrastFromSpread, { signal });
    hueInput.addEventListener("input", () => {
      hueShift = Number(hueInput.value);
      outHue.textContent = `${hueShift}°`;
      render();
    }, { signal });

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => {
          const on = t === tab;
          t.classList.toggle("is-active", on);
          t.setAttribute("aria-selected", on ? "true" : "false");
        });
        panels.forEach((p) => p.classList.toggle("is-active", p.dataset.panel === tab.dataset.tab));
        if (tab.dataset.tab === "picker") drawPicker();
      }, { signal });
    });

    copyBtn.addEventListener("click", async () => {
      const text = codeEl.textContent || "";
      try {
        await navigator.clipboard.writeText(text);
      } catch (_) {
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
      copyBtn.textContent = "Copied";
      clearTimeout(copiedTimer);
      copiedTimer = setTimeout(() => { copyBtn.textContent = "Copy CSS"; }, 1200);
    }, { signal });

    const onReduceChange = () => { reduced = reduceMQ.matches; };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    root.classList.toggle("is-reduced", reduced);
    outContrast.textContent = Number(contrastInput.value).toFixed(1);
    outSpread.textContent = Number(spreadInput.value).toFixed(2);
    outHue.textContent = "0°";
    render();

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.color = {
      get renders() { return renders; },
      get selected() { return currentBase(); },
      get scaleSize() { return scalesWrap.children.length; },
      get contrast() { return Math.max(contrast(currentBase(), "#fff"), contrast(currentBase(), "#000")); },
    };

    return function dispose() {
      ac.abort();
      clearTimeout(copiedTimer);
      basesWrap.textContent = "";
      scalesWrap.textContent = "";
      auditWrap.textContent = "";
      codeEl.textContent = "";
      root.classList.remove("is-reduced");
      if (window.__rfStats) window.__rfStats.color = null;
    };
  }

  window.RFColor = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="color-lab"]');
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
