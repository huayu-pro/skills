/* 05 — CSS 3D orbit: cards on a ring, drag/wheel to rotate, perspective. */
export const css = `
.rp-orbit{position:relative;height:100vh;perspective:1200px;overflow:hidden;touch-action:none;cursor:grab}
.rp-orbit.is-dragging{cursor:grabbing}
.rp-orbit-stage{position:absolute;left:50%;top:50%;transform-style:preserve-3d;will-change:transform}
.rp-orbit-card{position:absolute;width:260px;height:340px;margin:-170px 0 0 -130px;border-radius:14px;overflow:hidden;background:#17171b;box-shadow:0 20px 60px rgba(0,0,0,.35);backface-visibility:hidden}
.rp-orbit-card img,.rp-orbit-card canvas,.rp-orbit-card video{width:100%;height:100%;object-fit:cover;display:block}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("orbit-3d: root required");
  root.classList.add("rp-orbit");
  let stage = root.querySelector(options.stage || ".rp-orbit-stage");
  if (!stage) { stage = document.createElement("div"); stage.className = "rp-orbit-stage"; root.appendChild(stage); }
  const cards = [...root.querySelectorAll(options.cards || ".rp-orbit-card")];
  if (!cards.length) return () => {};
  cards.forEach((c) => c.classList.add("rp-orbit-card"));
  const radius = Number(options.radius || 420);
  const n = cards.length;
  cards.forEach((c, i) => { c.style.transform = `rotateY(${(360 / n) * i}deg) translateZ(${radius}px)`; });
  let angle = Number(options.startAngle || 0), target = angle, down = false, startX = 0, startAngle = 0;
  let raf = 0, auto = options.auto !== false;
  const tick = () => {
    if (!down) {
      if (auto) target += 0.08;
      target += (angle - target) * 0.08;
      target = angle;
    }
    angle += (target - angle) * 0.08;
    stage.style.transform = `translateZ(-${radius}px) rotateY(${angle.toFixed(3)}deg)`;
    raf = requestAnimationFrame(tick);
  };
  const onDown = (e) => { down = true; startX = e.clientX; startAngle = angle; root.classList.add("is-dragging"); };
  const onMove = (e) => { if (!down) return; angle = startAngle + (e.clientX - startX) * 0.35; target = angle; };
  const onUp = () => { down = false; root.classList.remove("is-dragging"); };
  const onWheel = (e) => { target += e.deltaY * 0.25; e.preventDefault(); };
  root.addEventListener("pointerdown", onDown);
  addEventListener("pointermove", onMove);
  addEventListener("pointerup", onUp);
  root.addEventListener("wheel", onWheel, { passive: false });
  raf = requestAnimationFrame(tick);
  return () => { cancelAnimationFrame(raf); root.removeEventListener("pointerdown", onDown); removeEventListener("pointermove", onMove); removeEventListener("pointerup", onUp); root.removeEventListener("wheel", onWheel); };
}
