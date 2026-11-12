/* 06 — custom cursor: dot + lagging ring + magnetic targets. */
export const css = `
.rp-cursor-dot,.rp-cursor-ring{position:fixed;left:0;top:0;pointer-events:none;z-index:10000;border-radius:50%;transform:translate(-50%,-50%);mix-blend-mode:difference}
.rp-cursor-dot{width:6px;height:6px;background:#fff}
.rp-cursor-ring{width:34px;height:34px;border:1px solid rgba(255,255,255,.75);transition:transform .2s,opacity .2s}
.rp-cursor-ring.is-hover{transform:translate(-50%,-50%) scale(1.706);opacity:.9}
.rp-magnetic{transition:transform .25s cubic-bezier(.2,.8,.2,1);will-change:transform}
@media (pointer: coarse){.rp-cursor-dot,.rp-cursor-ring{display:none}}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("cursor: root required");
  if (matchMedia("(pointer: coarse)").matches) return () => {};
  const dot = document.createElement("div"); dot.className = "rp-cursor-dot";
  const ring = document.createElement("div"); ring.className = "rp-cursor-ring";
  document.body.append(dot, ring);
  const targets = [...root.querySelectorAll(options.targets || "a,button,[data-cursor]")];
  targets.forEach((el) => el.classList.add("rp-magnetic"));
  let mx = innerWidth / 2, my = innerHeight / 2, rx = mx, ry = my;
  const onMove = (e) => {
    mx = e.clientX; my = e.clientY;
    dot.style.transform = `translate(${mx}px,${my}px) translate(-50%,-50%)`;
  };
  const onOver = (e) => {
    const t = e.target.closest && e.target.closest(options.targets || "a,button,[data-cursor]");
    ring.classList.toggle("is-hover", !!t);
  };
  let raf = 0;
  const tick = () => {
    rx += (mx - rx) * 0.16; ry += (my - ry) * 0.16;
    ring.style.transform = `translate(${rx}px,${ry}px) translate(-50%,-50%)`;
    raf = requestAnimationFrame(tick);
  };
  const onTargetMove = (e) => {
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) * 0.18;
    const dy = (e.clientY - (r.top + r.height / 2)) * 0.18;
    el.style.transform = `translate(${dx}px,${dy}px)`;
  };
  const onTargetLeave = (e) => { e.currentTarget.style.transform = ""; };
  addEventListener("pointermove", onMove, { passive: true });
  addEventListener("pointerover", onOver, { passive: true });
  targets.forEach((el) => { el.addEventListener("pointermove", onTargetMove); el.addEventListener("pointerleave", onTargetLeave); });
  raf = requestAnimationFrame(tick);
  return () => {
    cancelAnimationFrame(raf);
    removeEventListener("pointermove", onMove); removeEventListener("pointerover", onOver);
    targets.forEach((el) => { el.removeEventListener("pointermove", onTargetMove); el.removeEventListener("pointerleave", onTargetLeave); });
    dot.remove(); ring.remove();
  };
}
