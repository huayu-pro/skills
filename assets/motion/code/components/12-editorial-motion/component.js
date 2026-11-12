/* 12-editorial-motion — line reveal + char wave + dt marquee + velocity skew */
(function () {
  "use strict";

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function mount(root, options = {}) {
    if (!root) throw new Error("editorial: root required");
    const lines = root.querySelector("[data-lines]");
    const waveHost = root.querySelector("[data-wave]");
    const marquee = root.querySelector("[data-marquee]");
    const tabs = [...root.querySelectorAll("[data-tab]")];
    const panels = [...root.querySelectorAll("[data-panel]")];
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let raf = 0;
    let frames = 0;
    let x = 0;
    let speed = 60;
    let skew = 0;
    let lastY = scrollY;
    let ticking = false;
    let tab = "one";

    if (waveHost) {
      const text = waveHost.dataset.wave || "";
      waveHost.textContent = "";
      [...text].forEach((ch, i) => {
        const s = document.createElement("span");
        s.className = "rf-editorial__wave-char";
        s.style.setProperty("--i", String(i));
        s.textContent = ch === " " ? "\u00A0" : ch;
        waveHost.appendChild(s);
      });
    }

    const copy = "TYPE AS MATERIAL ✳ RHYTHM IS STRUCTURE ✳ ISSUE 12 ✳ ";
    const track = copy + copy + copy + copy;
    if (marquee) {
      marquee.innerHTML = track
        .split("")
        .map((c, i) => (c === "✳" || c === " " ? (c === "✳" ? "<em>✳</em>" : " ") : c))
        .join("")
        .replace(/<em>✳<\/em>/g, "<em>✳</em>");
      // Wrap each copy in spans for visual rhythm
      marquee.innerHTML = [0, 1, 2, 3].map(() => `<span>${copy.replaceAll("✳", "<em>✳</em>")}</span>`).join("");
    }

    function reveal() {
      if (lines) lines.classList.add("is-in");
    }

    function frame(now) {
      if (reduced) return;
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      x -= speed * dt;
      if (marquee && x <= -marquee.scrollWidth / 2) x += marquee.scrollWidth / 2;
      if (marquee) marquee.style.transform = `translate3d(${x.toFixed(2)}px,0,0)`;
      frames++;
      raf = requestAnimationFrame(frame);
    }

    let last = performance.now();

    function onScroll() {
      if (reduced) return;
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        const y = scrollY;
        const v = clamp((y - lastY) / 40, -1, 1);
        lastY = y;
        skew += (v * 3 - skew) * 0.12;
        if (lines) lines.style.transform = `skewY(${skew.toFixed(2)}deg)`;
      });
    }

    tabs.forEach((t) => {
      t.addEventListener("click", () => {
        tab = t.dataset.tab;
        tabs.forEach((b) => {
          const on = b === t;
          b.classList.toggle("is-active", on);
          b.setAttribute("aria-selected", on ? "true" : "false");
        });
        panels.forEach((p) => p.classList.toggle("is-active", p.dataset.panel === tab));
      }, { signal });
    });

    window.addEventListener("scroll", onScroll, { passive: true, signal });

    const onReduce = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) {
        cancelAnimationFrame(raf);
        raf = 0;
        if (lines) lines.style.transform = "none";
        if (marquee) marquee.style.transform = "none";
      } else {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    };
    reduceMQ.addEventListener("change", onReduce, { signal });

    root.classList.toggle("is-reduced", reduced);
    if (reduced) {
      if (lines) lines.classList.add("is-in");
    } else {
      requestAnimationFrame(() => requestAnimationFrame(reveal));
      raf = requestAnimationFrame(frame);
    }

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.editorial = {
      get frames() { return frames; },
      get skew() { return skew; },
      get tab() { return tab; },
      get waveChars() { return waveHost ? waveHost.children.length : 0; },
    };

    return function dispose() {
      ac.abort();
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      root.classList.remove("is-reduced");
      if (lines) lines.style.transform = "none";
      if (marquee) marquee.style.transform = "none";
      if (marquee) marquee.textContent = "";
      if (waveHost) waveHost.textContent = "";
      if (window.__rfStats) window.__rfStats.editorial = null;
    };
  }

  window.RFEditorial = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="editorial-motion"]');
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
