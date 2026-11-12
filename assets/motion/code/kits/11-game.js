/* 11 — game: minimal canvas runner; arrow/WASD + pointer, score, restart. */
export const css = `
.rp-game{position:relative;overflow:hidden;touch-action:none;background:#0b0b0e;color:#fff}
.rp-game canvas{position:absolute;inset:0;width:100%;height:100%}
.rp-game-hud{position:absolute;left:16px;top:14px;font:12px/1.4 ui-monospace,monospace;letter-spacing:.08em;pointer-events:none}
.rp-game-hint{position:absolute;right:16px;bottom:14px;font:11px/1.4 ui-monospace,monospace;opacity:.55;pointer-events:none}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("game: root required");
  root.classList.add("rp-game");
  const canvas = document.createElement("canvas"); root.appendChild(canvas);
  const ctx = canvas.getContext("2d"); if (!ctx) { canvas.remove(); return () => {}; }
  const hud = document.createElement("div"); hud.className = "rp-game-hud";
  const hint = document.createElement("div"); hint.className = "rp-game-hint"; hint.textContent = "← → / A D / drag";
  root.append(hud, hint);
  const state = { y: 0.5, vy: 0, score: 0, over: false, obs: [], t: 0 };
  let raf = 0, last = performance.now(), keys = new Set(), pointer = null;
  const resize = () => { const dpr = Math.min(devicePixelRatio || 1, 2); canvas.width = Math.max(1, root.clientWidth * dpr); canvas.height = Math.max(1, root.clientHeight * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
  const reset = () => { state.y = 0.5; state.vy = 0; state.score = 0; state.over = false; state.obs = []; state.t = 0; };
  const jump = () => { if (state.over) reset(); else state.vy = -0.62; };
  const onKey = (e) => { if (["ArrowUp", "KeyW", " "].includes(e.code)) { jump(); e.preventDefault(); } keys.add(e.code); };
  const offKey = (e) => keys.delete(e.code);
  const onDown = (e) => { pointer = e.clientY; jump(); };
  const onMove = (e) => { if (pointer != null) pointer = e.clientY; };
  const onUp = () => { pointer = null; };
  addEventListener("keydown", onKey); addEventListener("keyup", offKey);
  root.addEventListener("pointerdown", onDown); addEventListener("pointermove", onMove); addEventListener("pointerup", onUp);
  addEventListener("resize", resize); resize();
  const tick = (t) => {
    const dt = Math.min(0.05, (t - last) / 1000); last = t;
    if (!state.over) {
      state.t += dt; state.vy += dt * 1.55; state.y += state.vy * dt;
      if (pointer != null) state.y += ((pointer / root.clientHeight) - state.y) * 0.12;
      if (state.y < 0.12) { state.y = 0.12; state.vy = 0; }
      if (state.y > 0.88) { state.y = 0.88; state.vy = 0; }
      if (Math.random() < dt * 1.4) state.obs.push({ x: 1.1, y: 0.2 + Math.random() * 0.6, s: 0.06 + Math.random() * 0.08 });
      for (const o of state.obs) o.x -= dt * (0.42 + state.score * 0.006);
      state.obs = state.obs.filter((o) => o.x > -0.2);
      for (const o of state.obs) if (Math.abs(o.x - 0.2) < 0.05 + o.s / 2 && Math.abs(o.y - state.y) < 0.06 + o.s / 2) state.over = true;
      state.score += dt * 10;
    }
    const w = root.clientWidth, h = root.clientHeight;
    ctx.fillStyle = "#0b0b0e"; ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "rgba(255,255,255,.08)"; ctx.beginPath(); ctx.moveTo(0, h * 0.12); ctx.lineTo(w, h * 0.12); ctx.moveTo(0, h * 0.88); ctx.lineTo(w, h * 0.88); ctx.stroke();
    ctx.fillStyle = "#e9e9ef"; ctx.fillRect(w * 0.2 - 9, state.y * h - 9, 18, 18);
    for (const o of state.obs) { ctx.fillStyle = "#8b8b98"; ctx.fillRect(o.x * w - o.s * w / 2, o.y * h - o.s * w / 2, o.s * w, o.s * w); }
    hud.textContent = `SCORE ${Math.floor(state.score)}` + (state.over ? "  —  PRESS TO RESTART" : "");
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => { cancelAnimationFrame(raf); removeEventListener("keydown", onKey); removeEventListener("keyup", offKey); removeEventListener("pointermove", onMove); removeEventListener("pointerup", onUp); removeEventListener("resize", resize); canvas.remove(); hud.remove(); hint.remove(); };
}
