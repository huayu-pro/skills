/* 08 — collage: draggable cards, rotation, z-index lift, optional snap. */
export const css = `
.rp-collage{position:relative;min-height:100vh;touch-action:none}
.rp-collage-card{position:absolute;left:0;top:0;width:220px;background:#fff;padding:10px 10px 28px;box-shadow:0 18px 50px rgba(0,0,0,.22);cursor:grab;user-select:none;will-change:transform}
.rp-collage-card.is-dragging{cursor:grabbing;box-shadow:0 26px 70px rgba(0,0,0,.32)}
.rp-collage-card img,.rp-collage-card video,.rp-collage-card canvas{width:100%;display:block}
.rp-collage-card figcaption{font:12px/1.3 ui-monospace,monospace;padding-top:8px;color:#222}
@media (prefers-reduced-motion: reduce){.rp-collage-card{animation:none;transition:none}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("collage: root required");
  root.classList.add("rp-collage");
  const cards = [...root.querySelectorAll(options.cards || ".rp-collage-card")];
  let z = 10;
  const cleanups = [];
  cards.forEach((card) => {
    card.classList.add("rp-collage-card");
    const startX = 40 + Math.random() * Math.max(1, root.clientWidth - 300);
    const startY = 40 + Math.random() * Math.max(1, root.clientHeight - 380);
    const rot = Number(card.dataset.rotate || (Math.random() * 8 - 4));
    card.dataset.x = String(startX);
    card.dataset.y = String(startY);
    const paint = () => {
      card.style.transform = `translate3d(${card.dataset.x}px, ${card.dataset.y}px, 0) rotate(${rot}deg)`;
    };
    paint();
    let down = false, sx = 0, sy = 0, ox = 0, oy = 0;
    const onDown = (e) => {
      down = true; sx = e.clientX; sy = e.clientY; ox = Number(card.dataset.x) || 0; oy = Number(card.dataset.y) || 0;
      card.style.zIndex = ++z; card.classList.add("is-dragging");
      try { card.setPointerCapture(e.pointerId); } catch {}
    };
    const onMove = (e) => {
      if (!down) return;
      card.dataset.x = String(ox + e.clientX - sx);
      card.dataset.y = String(oy + e.clientY - sy);
      paint();
    };
    const onUp = () => { down = false; card.classList.remove("is-dragging"); };
    card.addEventListener("pointerdown", onDown);
    card.addEventListener("pointermove", onMove);
    card.addEventListener("pointerup", onUp);
    cleanups.push(() => { card.removeEventListener("pointerdown", onDown); card.removeEventListener("pointermove", onMove); card.removeEventListener("pointerup", onUp); });
  });
  return () => cleanups.forEach((fn) => fn());
}
