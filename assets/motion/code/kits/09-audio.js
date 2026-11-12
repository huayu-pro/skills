/* 09 — audio: click-to-unlock WebAudio, oscillator pad + analyser bars. */
export const css = `
.rp-audio{position:absolute;inset:0;display:grid;place-items:center;cursor:pointer;background:#050506}
.rp-audio-bars{position:absolute;inset:0;display:flex;align-items:flex-end;gap:2px;opacity:.7}
.rp-audio-bar{flex:1;height:100%;background:currentColor;transform-origin:bottom;transform:scaleY(.02)}
.rp-audio-label{position:relative;z-index:2;font:12px/1 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;opacity:.75}
.rp-audio.is-on .rp-audio-label{opacity:0}
@media (prefers-reduced-motion: reduce){.rp-audio-bar{animation:none;transition:none}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("audio: root required");
  root.classList.add("rp-audio");
  const bars = document.createElement("div"); bars.className = "rp-audio-bars";
  const count = options.bars || 64;
  for (let i = 0; i < count; i++) { const b = document.createElement("i"); b.className = "rp-audio-bar"; bars.appendChild(b); }
  const label = document.createElement("div"); label.className = "rp-audio-label"; label.textContent = options.label || "click to enable audio";
  root.append(bars, label);
  let ctx = null, analyser = null, data = null, raf = 0, oscs = [];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const start = async () => {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    await ctx.resume().catch(() => {});
    analyser = ctx.createAnalyser(); analyser.fftSize = 256; data = new Uint8Array(analyser.frequencyBinCount);
    const master = ctx.createGain(); master.gain.value = Number(options.gain || 0.035); master.connect(analyser); analyser.connect(ctx.destination);
    const freqs = options.freqs || [110, 164.81, 220, 277.18, 329.63];
    oscs = freqs.map((f, i) => { const o = ctx.createOscillator(); o.type = i % 2 ? "sine" : "triangle"; o.frequency.value = f; const g = ctx.createGain(); g.gain.value = 0.24 / (i + 1); o.connect(g); g.connect(master); o.start(); return o; });
    root.classList.add("is-on");
    const tick = () => { analyser.getByteFrequencyData(data); const els = bars.children; for (let i = 0; i < els.length; i++) { const v = data[Math.floor(i * data.length / els.length)] / 255; els[i].style.transform = "scaleY(" + (0.02 + v * 0.63).toFixed(3) + ")"; } if (!reduce.matches) raf = requestAnimationFrame(tick); };
    tick();
  };
  root.addEventListener("pointerdown", start);
  const key = (e) => { if (e.key === "Enter" || e.key === " ") start(); };
  root.tabIndex = 0; root.addEventListener("keydown", key);
  return () => {
    cancelAnimationFrame(raf); root.removeEventListener("pointerdown", start); root.removeEventListener("keydown", key);
    oscs.forEach((o) => { try { o.stop(); } catch {} });
    if (ctx) ctx.close().catch(() => {});
    bars.remove(); label.remove();
  };
}
