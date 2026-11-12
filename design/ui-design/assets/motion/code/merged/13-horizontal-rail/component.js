/* 13-horizontal-rail — F2 merged component.
   Wheel and drag map to velocity; lerp follows; boundary is a rubber band.
   Reduced motion switches to native horizontal scrolling. */
(function () {
  "use strict";

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function mount(root, options) {
    if (!root) throw new Error("horizontal-rail: root required");
    const opt = options || {};
    window.__rfStats = window.__rfStats || {};
    const viewport = root.querySelector(opt.viewport || ".mr-rail__viewport");
    const track = root.querySelector(opt.track || ".mr-rail__track");
    const progress = root.querySelector(".mr-rail__progress i");
    const readout = root.querySelector(".mr-rail__readout");
    if (!viewport || !track) throw new Error("horizontal-rail: viewport/track required");

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const panels = Array.from(track.children);
    let x = 0;
    let targetX = 0;
    let velocity = 0;
    let down = false;
    let startX = 0;
    let startTarget = 0;
    let lastX = 0;
    let prevX = 0;
    let moved = 0;
    let raf = 0;
    let frames = 0;
    let maxX = 0;
    let reduced = reduce.matches;
    let ro = null;
    let hidden = false;

    function measure() {
      maxX = Math.max(0, track.scrollWidth - viewport.clientWidth);
      targetX = clamp(targetX, -maxX, 0);
      x = clamp(x, -maxX, 0);
      render();
    }

    function render() {
      track.style.transform = reduced ? "none" : "translate3d(" + x.toFixed(2) + "px,0,0)";
      if (progress) {
        const ratio = maxX > 0 ? clamp(-x / maxX, 0, 1) : 1;
        progress.style.transform = "scaleX(" + ratio.toFixed(4) + ")";
      }
      if (readout) {
        readout.textContent = "x " + Math.round(-x) + " / " + Math.round(maxX);
      }
      if (window.__rfStats) {
        window.__rfStats.horizontal = { frames: frames, x: Math.round(x), max: Math.round(maxX) };
      }
    }

    function frame() {
      raf = 0;
      frames += 1;
      if (!reduced && !hidden) {
        x = lerp(x, targetX, 0.15);
        if (Math.abs(targetX - x) < 0.1) x = targetX;
        render();
        if (window.__rfStats) {
          window.__rfStats.horizontal = { frames: frames, x: Math.round(x), max: Math.round(maxX) };
        }
        if (Math.abs(targetX - x) > 0.1 || down) {
          raf = requestAnimationFrame(frame);
        }
      }
    }

    function kick() {
      if (!raf && !reduced && !hidden) raf = requestAnimationFrame(frame);
    }

    function onWheel(event) {
      if (reduced) return;
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
      const factor = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1;
      targetX = clamp(targetX - event.deltaY * factor, -maxX, 0);
      event.preventDefault();
      kick();
    }

    function onDown(event) {
      if (reduced) return;
      down = true;
      moved = 0;
      startX = lastX = prevX = event.clientX;
      startTarget = targetX;
      viewport.classList.add("is-dragging");
      if (viewport.setPointerCapture) viewport.setPointerCapture(event.pointerId);
      kick();
    }

    function onMove(event) {
      if (!down || reduced) return;
      prevX = lastX;
      lastX = event.clientX;
      moved = event.clientX - startX;
      targetX = clamp(startTarget + moved, -maxX, 0);
      velocity = (lastX - prevX) * 2.4;
      kick();
    }

    function onUp() {
      if (!down) return;
      down = false;
      viewport.classList.remove("is-dragging");
      if (Math.abs(velocity) > 0.5) {
        targetX = clamp(targetX + velocity * 10, -maxX, 0);
        velocity *= 0.92;
        kick();
      }
    }

    function onKey(event) {
      if (reduced) return;
      const step = viewport.clientWidth * 0.82;
      if (event.key === "ArrowRight") { targetX = clamp(targetX - step, -maxX, 0); event.preventDefault(); kick(); }
      if (event.key === "ArrowLeft") { targetX = clamp(targetX + step, -maxX, 0); event.preventDefault(); kick(); }
      if (event.key === "Home") { targetX = 0; event.preventDefault(); kick(); }
      if (event.key === "End") { targetX = -maxX; event.preventDefault(); kick(); }
    }

    function onVisibility() {
      hidden = document.hidden;
      if (hidden && raf) { cancelAnimationFrame(raf); raf = 0; }
      if (!hidden) kick();
    }

    function onReduceChange() {
      reduced = reduce.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) {
        if (raf) { cancelAnimationFrame(raf); raf = 0; }
        x = targetX = 0;
        render();
      } else {
        measure();
        kick();
      }
    }

    root.classList.toggle("is-reduced", reduced);
    viewport.addEventListener("wheel", onWheel, { passive: false });
    viewport.addEventListener("pointerdown", onDown);
    viewport.addEventListener("pointermove", onMove);
    viewport.addEventListener("pointerup", onUp);
    viewport.addEventListener("pointercancel", onUp);
    viewport.addEventListener("keydown", onKey);
    document.addEventListener("visibilitychange", onVisibility);
    reduce.addEventListener("change", onReduceChange);
    if ("ResizeObserver" in window) {
      ro = new ResizeObserver(measure);
      ro.observe(viewport);
    } else {
      window.addEventListener("resize", measure);
    }
    measure();
    if (!reduced) kick();

    return function dispose() {
      if (raf) cancelAnimationFrame(raf);
      viewport.removeEventListener("wheel", onWheel);
      viewport.removeEventListener("pointerdown", onDown);
      viewport.removeEventListener("pointermove", onMove);
      viewport.removeEventListener("pointerup", onUp);
      viewport.removeEventListener("pointercancel", onUp);
      viewport.removeEventListener("keydown", onKey);
      document.removeEventListener("visibilitychange", onVisibility);
      reduce.removeEventListener("change", onReduceChange);
      if (ro) ro.disconnect();
      else window.removeEventListener("resize", measure);
      track.style.transform = "";
      if (window.__rfStats) window.__rfStats.horizontal = null;
    };
  }

  const root = document.querySelector('[data-rf="horizontal-rail"]');
  if (root) {
    const dispose = mount(root);
    window.__rfDispose = dispose;
  }
  window.__rfMount = mount;
})();