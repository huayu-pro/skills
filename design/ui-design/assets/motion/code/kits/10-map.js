/* 10 — map: SVG pan/zoom with wheel, drag, pins, double-click reset. */
export const css = `
.rp-map{position:relative;overflow:hidden;touch-action:none;cursor:grab;background:#111}
.rp-map.is-dragging{cursor:grabbing}
.rp-map svg{position:absolute;left:50%;top:50%;width:1600px;height:1000px;margin:-500px 0 0 -800px;transform-origin:50% 50%;will-change:transform}
.rp-map-pin{position:absolute;left:var(--x,50%);top:var(--y,50%);width:10px;height:10px;border-radius:50%;background:currentColor;box-shadow:0 0 0 5px color-mix(in srgb,currentColor 22%,transparent);transform:translate(-50%,-50%)}
.rp-map-pin span{position:absolute;left:14px;top:-6px;font:11px/1 ui-monospace,monospace;white-space:nowrap}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("map: root required");
  root.classList.add("rp-map");
  let svg = root.querySelector("svg");
  if (!svg) {
    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 1600 1000");
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("fill", "none"); g.setAttribute("stroke", "currentColor"); g.setAttribute("stroke-opacity", "0.35");
    for (let i = 0; i < 12; i++) {
      const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", `M0 ${60 + i * 80} C 300 ${20 + i * 70}, 700 ${140 + i * 55}, 1600 ${50 + i * 72}`);
      g.appendChild(p);
    }
    svg.appendChild(g); root.appendChild(svg);
  }
  const pins = [...root.querySelectorAll(options.pins || "[data-pin]")].map((el) => {
    const pin = document.createElement("div"); pin.className = "rp-map-pin";
    pin.style.setProperty("--x", el.dataset.x + "%"); pin.style.setProperty("--y", el.dataset.y + "%");
    pin.innerHTML = `<span>${el.dataset.label || ""}</span>`; root.appendChild(pin); return pin;
  });
  let scale = 1, tx = 0, ty = 0, down = false, sx = 0, sy = 0, ox = 0, oy = 0;
  const render = () => { svg.style.transform = `translate(${tx}px,${ty}px) scale(${scale})`; };
  const onWheel = (e) => { scale = Math.max(0.4, Math.min(4, scale * Math.exp(-e.deltaY * 0.0015))); render(); e.preventDefault(); };
  const onDown = (e) => { down = true; sx = e.clientX; sy = e.clientY; ox = tx; oy = ty; root.classList.add("is-dragging"); };
  const onMove = (e) => { if (!down) return; tx = ox + e.clientX - sx; ty = oy + e.clientY - sy; render(); };
  const onUp = () => { down = false; root.classList.remove("is-dragging"); };
  const reset = () => { scale = 1; tx = ty = 0; render(); };
  root.addEventListener("wheel", onWheel, { passive: false });
  root.addEventListener("pointerdown", onDown);
  addEventListener("pointermove", onMove); addEventListener("pointerup", onUp);
  root.addEventListener("dblclick", reset);
  return () => { root.removeEventListener("wheel", onWheel); root.removeEventListener("pointerdown", onDown); removeEventListener("pointermove", onMove); removeEventListener("pointerup", onUp); root.removeEventListener("dblclick", reset); pins.forEach((p) => p.remove()); };
}
