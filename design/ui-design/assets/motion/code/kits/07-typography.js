/* 07 — typography: line reveal, marquee, scroll velocity skew. */
export const css = `
.rp-type-line{display:block;overflow:hidden}
.rp-type-line > span{display:block;transform:translateY(110%);transition:transform .8s cubic-bezier(.2,.75,.2,1)}
.rp-type-line.is-in > span{transform:none}
.rp-marquee{overflow:hidden;white-space:nowrap}
.rp-marquee-track{display:inline-flex;gap:2ch;will-change:transform}
.rp-type-skew{will-change:transform}
@media (prefers-reduced-motion: reduce){.rp-type-line > span{transform:none;transition:none}.rp-marquee-track{transform:none!important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("typography: root required");
  const lines = [...root.querySelectorAll(options.lines || "[data-type-line]")];
  lines.forEach((line) => {
    if (!line.querySelector(":scope > span")) {
      const inner = document.createElement("span"); inner.innerHTML = line.innerHTML; line.textContent = ""; line.appendChild(inner);
    }
    line.classList.add("rp-type-line");
  });
  const io = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
  }, { threshold: 0.2 }) : null;
  if (io) lines.forEach((l) => io.observe(l)); else lines.forEach((l) => l.classList.add("is-in"));

  const marquees = [...root.querySelectorAll(options.marquees || "[data-marquee]")].map((el) => {
    el.classList.add("rp-marquee");
    let track = el.querySelector(".rp-marquee-track");
    if (!track) { track = document.createElement("div"); track.className = "rp-marquee-track"; track.innerHTML = el.innerHTML; el.textContent = ""; el.appendChild(track); }
    track.innerHTML += track.innerHTML;
    return { el, track, x: 0, speed: Number(el.dataset.speed || options.speed || 0.4) };
  });
  const skew = [...root.querySelectorAll(options.skew || "[data-type-skew]")];
  let lastY = scrollY, raf = 0;
  const tick = () => {
    for (const m of marquees) {
      m.x -= m.speed;
      if (Math.abs(m.x) > m.track.scrollWidth / 2) m.x = 0;
      m.track.style.transform = `translate3d(${m.x}px,0,0)`;
    }
    const v = Math.max(-1, Math.min(1, (scrollY - lastY) / 40));
    lastY = scrollY;
    for (const el of skew) el.style.transform = `skewY(${(v * 3).toFixed(2)}deg)`;
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => { cancelAnimationFrame(raf); if (io) io.disconnect(); };
}
