/* 17-video-collage — F13 merged component.
   Six slots, pointer parallax by depth, IntersectionObserver pause.
   Replace each .mr-collage__media div with:
     <video muted playsinline preload="metadata" poster="..."><source ...></video>
   The same mount() will play/pause real videos. */
(function () {
  "use strict";

  function mount(root, options) {
    if (!root) throw new Error("video-collage: root required");
    const opt = options || {};
    window.__rfStats = window.__rfStats || {};
    const grid = root.querySelector(opt.grid || ".mr-collage__grid");
    const cards = Array.from(root.querySelectorAll(".mr-collage__card"));
    const pauseButton = root.querySelector("[data-pause]");
    const readout = root.querySelector(".mr-collage__readout");
    const videos = Array.from(root.querySelectorAll("video"));
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let reduced = reduce.matches;
    let paused = false;
    let hidden = false;
    let raf = 0;
    let frames = 0;
    let dx = 0;
    let dy = 0;
    let targetX = 0;
    let targetY = 0;
    let ro = null;
    let io = null;

    function render() {
      for (const card of cards) {
        card.style.setProperty("--dx", dx.toFixed(3));
        card.style.setProperty("--dy", dy.toFixed(3));
      }
    }

    function frame() {
      raf = 0;
      if (reduced || paused || hidden) return;
      dx += (targetX - dx) * 0.12;
      dy += (targetY - dy) * 0.12;
      render();
      frames += 1;
      if (window.__rfStats) {
        window.__rfStats.videoCollage = {
          frames: frames,
          playing: !paused,
          cards: cards.length,
          videos: videos.length,
        };
      }
      if (Math.abs(targetX - dx) > 0.001 || Math.abs(targetY - dy) > 0.001) {
        raf = requestAnimationFrame(frame);
      }
    }

    function kick() {
      if (!raf && !reduced && !paused && !hidden) raf = requestAnimationFrame(frame);
    }

    function onPointer(event) {
      if (!grid || reduced) return;
      const rect = grid.getBoundingClientRect();
      targetX = Math.max(-1, Math.min(1, ((event.clientX - rect.left) / rect.width) * 2 - 1));
      targetY = Math.max(-1, Math.min(1, ((event.clientY - rect.top) / rect.height) * 2 - 1));
      kick();
    }

    function onLeave() {
      targetX = 0;
      targetY = 0;
      kick();
    }

    function setPaused(next) {
      paused = next;
      root.classList.toggle("is-paused", paused);
      if (pauseButton) {
        pauseButton.textContent = paused ? "Play all" : "Pause all";
        pauseButton.setAttribute("aria-pressed", paused ? "true" : "false");
      }
      for (const video of videos) {
        if (paused || reduced) video.pause();
        else video.play().catch(function () {});
      }
      if (readout) readout.textContent = paused || reduced ? "paused" : "playing";
      if (window.__rfStats) {
        window.__rfStats.videoCollage = {
          frames: frames,
          playing: !paused && !reduced,
          cards: cards.length,
          videos: videos.length,
        };
      }
      kick();
    }

    function onPause() {
      setPaused(!paused);
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
        for (const video of videos) video.pause();
        if (readout) readout.textContent = "reduced";
      } else {
        kick();
      }
    }

    if (grid) {
      grid.addEventListener("pointermove", onPointer);
      grid.addEventListener("pointerleave", onLeave);
    }
    if (pauseButton) pauseButton.addEventListener("click", onPause);
    document.addEventListener("visibilitychange", onVisibility);
    reduce.addEventListener("change", onReduceChange);

    if ("IntersectionObserver" in window) {
      io = new IntersectionObserver(function (entries) {
        for (const entry of entries) {
          entry.target.classList.toggle("is-offscreen", !entry.isIntersecting);
        }
      }, { rootMargin: "120px", threshold: 0 });
      cards.forEach(function (card) { io.observe(card); });
    }

    render();
    if (reduced) setPaused(true);

    return function dispose() {
      if (raf) cancelAnimationFrame(raf);
      if (grid) {
        grid.removeEventListener("pointermove", onPointer);
        grid.removeEventListener("pointerleave", onLeave);
      }
      if (pauseButton) pauseButton.removeEventListener("click", onPause);
      document.removeEventListener("visibilitychange", onVisibility);
      reduce.removeEventListener("change", onReduceChange);
      if (io) io.disconnect();
      for (const video of videos) video.pause();
      if (window.__rfStats) window.__rfStats.videoCollage = null;
    };
  }

  const root = document.querySelector('[data-rf="video-collage"]');
  if (root) window.__rfDispose = mount(root);
  window.__rfMount = mount;
})();