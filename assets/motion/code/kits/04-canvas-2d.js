/* 04 — Canvas 2D particle tunnel with pointer swirl, DPR-aware. */
export const css = `.rp-canvas2d{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none}@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("canvas-2d: root required");
  const canvas = document.createElement("canvas");
  canvas.className = "rp-canvas2d";
  root.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) { canvas.remove(); return () => {}; }
  const count = options.count || 420;
  const particles = Array.from({ length: count }, () => ({ z: Math.random(), a: Math.random() * Math.PI * 2, r: 0.15 + Math.random() * 0.85, s: 0.15 + Math.random() * 0.5 }));
  const mouse = { x: 0.5, y: 0.5 };
  const resize = () => {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(root.clientWidth * dpr));
    canvas.height = Math.max(1, Math.round(root.clientHeight * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  const onMove = (e) => { const r = canvas.getBoundingClientRect(); mouse.x = (e.clientX - r.left) / Math.max(1, r.width); mouse.y = (e.clientY - r.top) / Math.max(1, r.height); };
  addEventListener("pointermove", onMove, { passive: true });
  addEventListener("resize", resize);
  resize();
  let raf = 0, last = performance.now();
  const draw = (t) => {
    const dt = Math.min(0.05, (t - last) / 1000); last = t;
    const w = root.clientWidth, h = root.clientHeight;
    ctx.fillStyle = options.background || "rgba(8,8,10,0.22)";
    ctx.fillRect(0, 0, w, h);
    const cx = w / 2 + (mouse.x - 0.5) * w * 0.12;
    const cy = h / 2 + (mouse.y - 0.5) * h * 0.12;
    for (const p of particles) {
      p.z -= dt * (0.08 + p.s * 0.12);
      if (p.z <= 0.02) { p.z = 1; p.a = Math.random() * Math.PI * 2; }
      const r = Math.pow(p.z, 2) * Math.min(w, h) * 0.55 * p.r;
      const x = cx + Math.cos(p.a + p.z * 2.4) * r;
      const y = cy + Math.sin(p.a + p.z * 2.4) * r * 0.72;
      const size = Math.max(0.6, (1 - p.z) * 3.2);
      ctx.fillStyle = `rgba(235,240,255,${(1 - p.z) * 0.75})`;
      ctx.beginPath(); ctx.arc(x, y, size, 0, Math.PI * 2); ctx.fill();
    }
    raf = requestAnimationFrame(draw);
  };
  raf = requestAnimationFrame(draw);
  return () => { cancelAnimationFrame(raf); removeEventListener("pointermove", onMove); removeEventListener("resize", resize); canvas.remove(); };
}
