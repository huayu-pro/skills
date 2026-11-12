/* 16-scan-vhs — F12 merged component.
   CSS drives the three layers; JS only toggles, pauses and counts glitches. */
(function () {
  "use strict";

  function mount(root, options) {
    if (!root) throw new Error("scan-vhs: root required");
    const opt = options || {};
    window.__rfStats = window.__rfStats || {};
    const glitch = root.querySelector(opt.glitch || ".mr-scan__glitch");
    const readout = root.querySelector(".mr-scan__readout");
    const pauseButton = root.querySelector("[data-pause]");
    const toggles = Array.from(root.querySelectorAll("[data-toggle]"));
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let paused = false;
    let hidden = false;
    let glitches = 0;
    let reduced = reduce.matches;

    function setPaused(next) {
      paused = next;
      root.classList.toggle("is-paused", paused);
      if (pauseButton) {
        pauseButton.textContent = paused ? "Play" : "Pause";
        pauseButton.setAttribute("aria-pressed", paused ? "true" : "false");
      }
      if (window.__rfStats) {
        window.__rfStats.scan = { glitches: glitches, paused: paused, reduced: reduced };
      }
    }

    function onPause() {
      setPaused(!paused);
    }

    function onToggle(event) {
      const button = event.currentTarget;
      const name = button.getAttribute("data-toggle");
      const next = button.getAttribute("aria-pressed") !== "true";
      button.setAttribute("aria-pressed", next ? "true" : "false");
      root.classList.toggle("is-off-" + name, !next);
    }

    function onGlitch() {
      if (paused || hidden || reduced) return;
      glitches += 1;
      if (readout) readout.textContent = "glitches " + glitches;
      if (window.__rfStats) window.__rfStats.scan = { glitches: glitches, paused: paused, reduced: reduced };
    }

    function onVisibility() {
      hidden = document.hidden;
      root.classList.toggle("is-hidden-tab", hidden);
    }

    function onReduceChange() {
      reduced = reduce.matches;
      if (reduced) {
        root.classList.add("is-paused");
        if (window.__rfStats) window.__rfStats.scan = { glitches: glitches, paused: true, reduced: true };
      } else {
        root.classList.remove("is-paused");
        if (!paused) setPaused(false);
      }
    }

    if (glitch) glitch.addEventListener("animationiteration", onGlitch);
    if (pauseButton) pauseButton.addEventListener("click", onPause);
    toggles.forEach(function (button) { button.addEventListener("click", onToggle); });
    document.addEventListener("visibilitychange", onVisibility);
    reduce.addEventListener("change", onReduceChange);
    if (reduced) setPaused(true);

    if (window.__rfStats) window.__rfStats.scan = { glitches: 0, paused: paused, reduced: reduced };

    return function dispose() {
      if (glitch) glitch.removeEventListener("animationiteration", onGlitch);
      if (pauseButton) pauseButton.removeEventListener("click", onPause);
      toggles.forEach(function (button) { button.removeEventListener("click", onToggle); });
      document.removeEventListener("visibilitychange", onVisibility);
      reduce.removeEventListener("change", onReduceChange);
      if (window.__rfStats) window.__rfStats.scan = null;
    };
  }

  const root = document.querySelector('[data-rf="scan-vhs"]');
  if (root) window.__rfDispose = mount(root);
  window.__rfMount = mount;
})();