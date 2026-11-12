/* 15-pixel-canvas — F5 merged component.
   Draw at 160x120, scale with image-rendering: pixelated.
   Six colours, integer coordinates, no anti-aliasing. */
(function () {
  "use strict";

  const W = 160;
  const H = 120;
  const C = {
    sky0: "#0b1026",
    sky1: "#16224a",
    sky2: "#2b3f6b",
    sea0: "#123a4a",
    sea1: "#1d5a63",
    sea2: "#2d7a78",
    mountain: "#22304f",
    mountain2: "#31436a",
    sun: "#e8b45a",
    sun2: "#f4c77a",
    ink: "#f4efe4",
    red: "#d95d39",
  };

  const HERO = [
    "0011100",
    "0011100",
    "0001000",
    "0111110",
    "0010100",
    "0010100",
    "0010100",
    "0100010",
    "0100010",
    "1000001",
  ];

  function mount(root, options) {
    if (!root) throw new Error("pixel-canvas: root required");
    window.__rfStats = window.__rfStats || {};
    const canvas = root.querySelector(".mr-pixel__canvas");
    const speedInput = root.querySelector("[data-speed]");
    const pauseButton = root.querySelector("[data-pause]");
    const readout = root.querySelector(".mr-pixel__readout");
    if (!canvas) throw new Error("pixel-canvas: canvas required");

    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("pixel-canvas: Canvas2D unavailable");
    ctx.imageSmoothingEnabled = false;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let reduced = reduce.matches;
    let paused = false;
    let hidden = false;
    let raf = 0;
    let frames = 0;
    let time = 0;
    let speed = 1;
    let last = performance.now();

    function rect(x, y, w, h, color) {
      ctx.fillStyle = color;
      ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
    }

    function disc(cx, cy, radius, color) {
      ctx.fillStyle = color;
      for (let y = -radius; y <= radius; y++) {
        const span = Math.floor(Math.sqrt(radius * radius - y * y));
        ctx.fillRect(Math.round(cx - span), Math.round(cy + y), span * 2 + 1, 1);
      }
    }

    function triangle(x0, y0, half, height, color) {
      ctx.fillStyle = color;
      for (let row = 0; row < height; row++) {
        const t = row / height;
        const span = Math.floor(half * t);
        ctx.fillRect(Math.round(x0 - span), Math.round(y0 + row), span * 2 + 1, 1);
      }
    }

    function drawSky() {
      rect(0, 0, W, 44, C.sky0);
      rect(0, 44, W, 18, C.sky1);
      rect(0, 62, W, 18, C.sky2);
    }

    function drawSun(phase) {
      const cx = 118;
      const cy = 34 + Math.round(Math.sin(phase * Math.PI * 2) * 2);
      disc(cx, cy, 12, C.sun);
      disc(cx - 3, cy - 3, 7, C.sun2);
    }

    function drawMountains() {
      triangle(28, 62, 34, 30, C.mountain);
      triangle(58, 66, 46, 26, C.mountain2);
      triangle(132, 68, 30, 22, C.mountain);
      rect(0, 84, W, 4, C.sea0);
    }

    function drawSea(phase) {
      rect(0, 86, W, H - 86, C.sea0);
      for (let y = 90; y < H; y += 6) {
        rect(0, y, W, 2, C.sea1);
      }
      const shift = Math.round(phase * 12);
      for (let i = 0; i < 11; i++) {
        const x = (i * 17 + shift) % W;
        const y = 94 + (i % 4) * 7;
        rect(x, y, 6, 1, C.sea2);
      }
    }

    function drawCloud(x, y) {
      rect(x, y, 14, 4, C.ink);
      rect(x + 3, y - 2, 8, 3, C.ink);
      rect(x + 2, y + 3, 10, 2, C.sky2);
    }

    function drawHero(phase) {
      const bob = Math.round(Math.sin(phase * Math.PI * 4) * 1);
      const baseX = 48;
      const baseY = 88 + bob;
      for (let row = 0; row < HERO.length; row++) {
        const line = HERO[row];
        for (let col = 0; col < line.length; col++) {
          if (line[col] === "1") {
            rect(baseX + col, baseY + row, 1, 1, row < 3 ? C.red : C.ink);
          }
        }
      }
      rect(baseX - 2, baseY + HERO.length, 12, 2, C.mountain);
    }

    function draw(phase) {
      drawSky();
      drawSun(phase);
      drawCloud((phase * 40 + 18) % (W + 30) - 20, 22);
      drawCloud((phase * 24 + 92) % (W + 40) - 20, 34);
      drawMountains();
      drawSea(phase);
      drawHero(phase);
      if (readout) readout.textContent = "phase " + phase.toFixed(2);
    }

    function frame(now) {
      raf = 0;
      const dt = Math.min((now - last) / 1000, 1 / 30);
      last = now;
      if (!paused && !hidden) {
        time += dt * speed;
        const phase = time % 1;
        draw(phase);
        frames += 1;
        if (window.__rfStats) {
          window.__rfStats.pixel = { frames: frames, phase: Number(phase.toFixed(3)), speed: speed };
        }
        raf = requestAnimationFrame(frame);
      }
    }

    function kick() {
      if (!raf && !paused && !hidden && !reduced) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    }

    function onSpeed() {
      speed = Number(speedInput.value) || 0;
    }

    function onPause() {
      paused = !paused;
      if (pauseButton) {
        pauseButton.textContent = paused ? "Play" : "Pause";
        pauseButton.setAttribute("aria-pressed", paused ? "true" : "false");
      }
      if (paused && raf) { cancelAnimationFrame(raf); raf = 0; }
      if (!paused) kick();
    }

    function onVisibility() {
      hidden = document.hidden;
      if (hidden && raf) { cancelAnimationFrame(raf); raf = 0; }
      if (!hidden) kick();
    }

    function onReduceChange() {
      reduced = reduce.matches;
      if (reduced) {
        if (raf) { cancelAnimationFrame(raf); raf = 0; }
        draw(0.3);
      } else {
        kick();
      }
    }

    if (speedInput) speedInput.addEventListener("input", onSpeed);
    if (pauseButton) pauseButton.addEventListener("click", onPause);
    document.addEventListener("visibilitychange", onVisibility);
    reduce.addEventListener("change", onReduceChange);

    draw(0.3);
    if (!reduced) kick();

    return function dispose() {
      if (raf) cancelAnimationFrame(raf);
      if (speedInput) speedInput.removeEventListener("input", onSpeed);
      if (pauseButton) pauseButton.removeEventListener("click", onPause);
      document.removeEventListener("visibilitychange", onVisibility);
      reduce.removeEventListener("change", onReduceChange);
      if (window.__rfStats) window.__rfStats.pixel = null;
    };
  }

  const root = document.querySelector('[data-rf="pixel-canvas"]');
  if (root) window.__rfDispose = mount(root);
  window.__rfMount = mount;
})();