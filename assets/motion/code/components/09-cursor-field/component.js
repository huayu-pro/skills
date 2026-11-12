/* 09-cursor-field — dot/ring cursor, magnet, depth parallax, tilt cards */
(function () {
  "use strict";

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function mount(root, options = {}) {
    if (!root) throw new Error("cursor: root required");
    const dot = root.querySelector(".rf-cursor__dot");
    const ring = root.querySelector(".rf-cursor__ring");
    const layers = [...root.querySelectorAll("[data-depth]")];
    const magnets = [...root.querySelectorAll(".magnet")];
    const cards = [...root.querySelectorAll("[data-tilt]")];
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");
    const fineMQ = matchMedia("(pointer: fine)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let fine = fineMQ.matches;
    let raf = 0;
    let frames = 0;
    let mx = innerWidth / 2, my = innerHeight / 2;
    let rx = mx, ry = my;
    let tx = 0, ty = 0;

    function setFine() {
      fine = fineMQ.matches;
      root.classList.toggle("is-fine", fine);
      root.classList.toggle("is-coarse", !fine);
      document.documentElement.classList.toggle("rf-cursor-fine", fine);
      root.querySelector(".rf-cursor__status").textContent = fine ? "pointer: fine" : "pointer: coarse";
    }

    function onMove(e) {
      mx = e.clientX;
      my = e.clientY;
      dot.style.transform = `translate3d(${mx}px, ${my}px, 0)`;
      if (reduced) {
        ring.style.transform = `translate3d(${mx}px, ${my}px, 0)`;
      }
      tx = (mx / innerWidth - 0.5) * 2;
      ty = (my / innerHeight - 0.5) * 2;
      if (!reduced) {
        for (const el of layers) {
          const depth = Number(el.dataset.depth || 1);
          el.style.setProperty("--px", `${(tx * depth * 10).toFixed(2)}px`);
          el.style.setProperty("--py", `${(ty * depth * 10).toFixed(2)}px`);
        }
      }
      for (const m of magnets) {
        const r = m.getBoundingClientRect();
        const dx = mx - (r.left + r.width / 2);
        const dy = my - (r.top + r.height / 2);
        if (Math.abs(dx) < r.width && Math.abs(dy) < r.height) {
          m.style.setProperty("--mx", `${clamp(dx * 0.18, -14, 14).toFixed(2)}px`);
          m.style.setProperty("--my", `${clamp(dy * 0.18, -14, 14).toFixed(2)}px`);
        }
      }
      for (const c of cards) {
        const r = c.getBoundingClientRect();
        if (mx < r.left || mx > r.right || my < r.top || my > r.bottom) continue;
        const nx = (mx - r.left) / r.width - 0.5;
        const ny = (my - r.top) / r.height - 0.5;
        if (reduced) continue;
        c.style.setProperty("--rx", `${(-ny * 30).toFixed(2)}deg`);
        c.style.setProperty("--ry", `${(nx * 30).toFixed(2)}deg`);
      }
    }

    function onOver(e) {
      const hit = e.target.closest("a, button, [data-tilt]");
      root.classList.toggle("is-hover", !!hit);
    }

    function onLeave() {
      for (const m of magnets) {
        m.style.setProperty("--mx", "0px");
        m.style.setProperty("--my", "0px");
      }
      for (const c of cards) {
        c.style.setProperty("--rx", "0deg");
        c.style.setProperty("--ry", "0deg");
      }
      root.classList.remove("is-hover");
    }

    function frame() {
      if (reduced || !fine) return;
      rx += (mx - rx) * 0.16;
      ry += (my - ry) * 0.16;
      ring.style.transform = `translate3d(${rx.toFixed(2)}px, ${ry.toFixed(2)}px, 0)`;
      frames++;
      raf = requestAnimationFrame(frame);
    }

    window.addEventListener("pointermove", onMove, { signal });
    window.addEventListener("pointerover", onOver, { signal });
    root.addEventListener("pointerleave", onLeave, { signal });
    document.addEventListener("mouseleave", onLeave, { signal });

    const onReduce = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) {
        cancelAnimationFrame(raf);
        raf = 0;
        ring.style.transform = `translate3d(${mx}px, ${my}px, 0)`;
        onLeave();
      } else if (fine && !raf) {
        raf = requestAnimationFrame(frame);
      }
    };
    reduceMQ.addEventListener("change", onReduce, { signal });
    fineMQ.addEventListener("change", () => {
      setFine();
      if (!fine) { cancelAnimationFrame(raf); raf = 0; }
      else if (!reduced && !raf) raf = requestAnimationFrame(frame);
    }, { signal });

    setFine();
    root.classList.toggle("is-reduced", reduced);
    if (fine && !reduced) raf = requestAnimationFrame(frame);

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.cursor = {
      get frames() { return frames; },
      get x() { return mx; },
      get y() { return my; },
      get fine() { return fine; },
    };

    return function dispose() {
      ac.abort();
      cancelAnimationFrame(raf);
      root.classList.remove("is-fine", "is-coarse", "is-hover", "is-reduced");
      document.documentElement.classList.remove("rf-cursor-fine");
      if (window.__rfStats) window.__rfStats.cursor = null;
    };
  }

  window.RFCursor = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="cursor-field"]');
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
