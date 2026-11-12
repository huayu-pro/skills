/* 01 — scroll narrative: section reveal, progress bar, subtle parallax. */
export const css = `
.rp-scroll{position:relative}
.rp-scroll-progress{position:fixed;left:0;top:0;height:2px;width:100%;background:currentColor;z-index:9999;pointer-events:none;transform:scaleX(0);transform-origin:0 50%}
.rp-scroll-section{opacity:0;transform:translateY(24px);transition:opacity .7s ease,transform .7s ease}
.rp-scroll-section.is-in{opacity:1;transform:none}
.rp-scroll-parallax{will-change:transform}
@media (prefers-reduced-motion: reduce){.rp-scroll-section{opacity:1;transform:none;transition:none}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("scroll-narrative: root required");
  root.classList.add("rp-scroll");
  const sections = [...root.querySelectorAll(options.sections || ".rp-scroll-section")];
  const parallax = [...root.querySelectorAll(options.parallax || ".rp-scroll-parallax")];
  const bar = document.createElement("div");
  bar.className = "rp-scroll-progress";
  bar.setAttribute("aria-hidden", "true");
  document.body.appendChild(bar);

  let ticking = false;
  const update = () => {
    ticking = false;
    const max = document.documentElement.scrollHeight - innerHeight;
    bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, scrollY / max) : 0) + ")";
    for (const el of parallax) {
      const r = el.getBoundingClientRect();
      const p = (r.top + r.height / 2 - innerHeight / 2) / innerHeight;
      const amount = Number(el.dataset.parallax || options.parallaxAmount || 24);
      el.style.transform = `translate3d(0,${(-p * amount).toFixed(2)}px,0)`;
    }
  };
  const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };

  const io = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
  }, { rootMargin: "0px 0px -10% 0px", threshold: 0.08 }) : null;

  if (io) sections.forEach((el) => { el.classList.add("rp-scroll-section"); io.observe(el); });
  else sections.forEach((el) => el.classList.add("is-in"));
  addEventListener("scroll", onScroll, { passive: true });
  update();

  return () => {
    removeEventListener("scroll", onScroll);
    if (io) io.disconnect();
    bar.remove();
  };
}
