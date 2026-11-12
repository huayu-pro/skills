/* 02 — horizontal rail: wheel/drag to translate, optional snap, progress. */
export const css = `
.rp-horizontal{position:relative;overflow:hidden;touch-action:none;cursor:grab}
.rp-horizontal.is-dragging{cursor:grabbing}
.rp-horizontal-track{display:flex;flex-wrap:nowrap;will-change:transform}
.rp-horizontal-panel{flex:0 0 auto;min-width:100vw;min-height:100vh;display:grid;place-items:center}
.rp-horizontal-progress{position:fixed;left:0;bottom:0;height:2px;background:currentColor;z-index:9999;width:100%;transform:scaleX(0);transform-origin:0 50%}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("horizontal: root required");
  root.classList.add("rp-horizontal");
  const track = root.querySelector(options.track || ".rp-horizontal-track") || root.firstElementChild;
  if (!track) throw new Error("horizontal: track required");
  track.classList.add("rp-horizontal-track");
  const panels = [...track.children].filter((el) => el.nodeType === 1);
  panels.forEach((el) => el.classList.add("rp-horizontal-panel"));
  const bar = document.createElement("div");
  bar.className = "rp-horizontal-progress";
  document.body.appendChild(bar);

  let x = 0, down = false, startX = 0, startOffset = 0, moved = 0;
  const max = () => Math.max(0, track.scrollWidth - root.clientWidth);
  const clamp = (v) => Math.max(-max(), Math.min(0, v));
  const render = () => {
    track.style.transform = `translate3d(${x}px,0,0)`;
    bar.style.transform = "scaleX(" + (max() > 0 ? -x / max() : 0) + ")";
  };
  const onWheel = (e) => {
    if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
    x = clamp(x - e.deltaY);
    render();
    e.preventDefault();
  };
  const onDown = (e) => { down = true; moved = 0; startX = e.clientX; startOffset = x; root.classList.add("is-dragging"); };
  const onMove = (e) => {
    if (!down) return;
    moved = e.clientX - startX;
    x = clamp(startOffset + moved);
    render();
  };
  const onUp = () => {
    if (!down) return;
    down = false;
    root.classList.remove("is-dragging");
    if (options.snap && panels.length) {
      const target = Math.round(-x / root.clientWidth) * root.clientWidth;
      x = clamp(-target);
      render();
    }
  };
  addEventListener("wheel", onWheel, { passive: false });
  root.addEventListener("pointerdown", onDown);
  addEventListener("pointermove", onMove);
  addEventListener("pointerup", onUp);
  render();

  return () => {
    removeEventListener("wheel", onWheel);
    removeEventListener("pointermove", onMove);
    removeEventListener("pointerup", onUp);
    root.removeEventListener("pointerdown", onDown);
    bar.remove();
  };
}
