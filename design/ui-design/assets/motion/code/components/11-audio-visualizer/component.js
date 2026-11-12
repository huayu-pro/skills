/* 11-audio-visualizer — oscillator pad + analyser bars, user-gesture unlock */
(function () {
  "use strict";

  const BARS = 64;
  const FREQS = [110, 164.81, 220, 277.18, 329.63];
  const TYPES = ["triangle", "sine", "triangle", "sine", "triangle"];
  const MASTER = 0.035;

  function mount(root, options = {}) {
    if (!root) throw new Error("audio: root required");
    const barsWrap = root.querySelector("[data-bars]");
    const playBtn = root.querySelector("[data-play]");
    const muteBtn = root.querySelector("[data-mute]");
    const stateEl = root.querySelector("[data-state]");
    const readout = root.querySelector("[data-readout]");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let ctx = null;
    let master = null;
    let analyser = null;
    let oscillators = [];
    let gains = [];
    let data = null;
    let raf = 0;
    let frames = 0;
    let state = "idle";
    let muted = false;
    let closedTimer = 0;
    const bars = [];

    for (let i = 0; i < BARS; i++) {
      const b = document.createElement("span");
      b.className = "rf-audio__bar-item";
      const seed = 0.08 + 0.1 * Math.abs(Math.sin(i * 0.7));
      b.style.setProperty("--v", seed.toFixed(3));
      barsWrap.appendChild(b);
      bars.push(b);
    }

    function setState(next) {
      state = next;
      stateEl.textContent = next;
      stateEl.dataset.state = next;
      playBtn.textContent = next === "on" || next === "muted" ? "Playing" : next === "starting" ? "Starting…" : "Enable sound";
    }

    function paintStatic() {
      bars.forEach((b, i) => {
        const v = 0.12 + 0.42 * Math.abs(Math.sin(i * 0.37) * Math.cos(i * 0.11));
        b.style.setProperty("--v", v.toFixed(3));
      });
    }

    function frame() {
      if (!analyser) return;
      analyser.getByteFrequencyData(data);
      for (let i = 0; i < bars.length; i++) {
        const v = data[i] / 255;
        bars[i].style.setProperty("--v", (0.06 + v * 0.94).toFixed(3));
      }
      frames++;
      raf = requestAnimationFrame(frame);
    }

    async function start() {
      if (ctx) {
        if (ctx.state === "suspended") await ctx.resume();
        if (state === "muted") setMute(false);
        else { setState("on"); if (!reduced) startRaf(); }
        return;
      }
      setState("starting");
      try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) throw new Error("no AudioContext");
        ctx = new AC({ latencyHint: "interactive" });
        master = ctx.createGain();
        master.gain.value = MASTER;
        analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        data = new Uint8Array(analyser.frequencyBinCount);
        master.connect(analyser);
        analyser.connect(ctx.destination);
        oscillators = FREQS.map((f, i) => {
          const o = ctx.createOscillator();
          const g = ctx.createGain();
          o.type = TYPES[i];
          o.frequency.value = f;
          g.gain.value = 0.24 / (i + 1);
          o.connect(g).connect(master);
          o.start();
          gains.push(g);
          return o;
        });
        await ctx.resume();
        setState("on");
        readout.textContent = MASTER.toFixed(3);
        if (reduced) paintStatic();
        else startRaf();
      } catch (err) {
        setState("error");
        paintStatic();
      }
    }

    function startRaf() {
      if (raf) return;
      raf = requestAnimationFrame(frame);
    }
    function stopRaf() {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    }

    function setMute(next) {
      muted = next;
      muteBtn.setAttribute("aria-pressed", next ? "true" : "false");
      if (master) {
        master.gain.setTargetAtTime(next ? 0 : MASTER, ctx.currentTime, 0.08);
        readout.textContent = (next ? 0 : MASTER).toFixed(3);
      }
      if (next) { setState("muted"); stopRaf(); paintStatic(); }
      else if (ctx) { setState("on"); if (!reduced) startRaf(); }
    }

    playBtn.addEventListener("click", start, { signal });
    muteBtn.addEventListener("click", () => setMute(!muted), { signal });

    function onVisibility() {
      if (!ctx) return;
      if (document.hidden) {
        stopRaf();
        ctx.suspend().catch(() => {});
      } else if (state === "on" && !reduced) {
        ctx.resume().catch(() => {});
        startRaf();
      }
    }
    document.addEventListener("visibilitychange", onVisibility, { signal });

    const onReduce = () => {
      reduced = reduceMQ.matches;
      root.classList.toggle("is-reduced", reduced);
      if (reduced) { stopRaf(); paintStatic(); }
      else if (state === "on") startRaf();
    };
    reduceMQ.addEventListener("change", onReduce, { signal });

    root.classList.toggle("is-reduced", reduced);
    setState("idle");
    if (reduced) paintStatic();

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.audio = {
      get state() { return state; },
      get frames() { return frames; },
      get bars() { return bars.length; },
      get muted() { return muted; },
    };

    return function dispose() {
      ac.abort();
      stopRaf();
      clearTimeout(closedTimer);
      document.removeEventListener("visibilitychange", onVisibility);
      oscillators.forEach((o) => { try { o.stop(); } catch (_) {} });
      oscillators = [];
      gains = [];
      if (ctx) { ctx.close().catch(() => {}); }
      ctx = null; master = null; analyser = null;
      barsWrap.textContent = "";
      bars.length = 0;
      root.classList.remove("is-reduced");
      if (window.__rfStats) window.__rfStats.audio = null;
    };
  }

  window.RFAudio = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="audio-visualizer"]');
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
