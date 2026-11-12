/* 12 — editorial landing: sticky header, reveal, accordion, back-to-top. */
export const css = `
.rp-editorial{--rp-pad:clamp(16px,4vw,56px)}
.rp-editorial-header{position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;padding:14px var(--rp-pad);backdrop-filter:blur(10px);background:color-mix(in srgb,canvas 82%,transparent);transition:transform .3s}
.rp-editorial-header.is-hidden{transform:translateY(-100%)}
.rp-editorial-reveal{opacity:0;transform:translateY(18px);transition:opacity .7s ease,transform .7s ease}
.rp-editorial-reveal.is-in{opacity:1;transform:none}
.rp-editorial-accordion{border-top:1px solid currentColor}
.rp-editorial-item{border-bottom:1px solid currentColor}
.rp-editorial-item button{width:100%;display:flex;justify-content:space-between;gap:16px;padding:16px 0;background:none;border:0;color:inherit;font:inherit;text-align:left;cursor:pointer}
.rp-editorial-item .body{display:grid;grid-template-rows:0fr;transition:grid-template-rows .35s}
.rp-editorial-item.is-open .body{grid-template-rows:1fr}
.rp-editorial-item .body > div{overflow:hidden}
.rp-editorial-top{position:fixed;right:18px;bottom:18px;width:38px;height:38px;border-radius:50%;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;opacity:0;pointer-events:none;transition:opacity .2s}
.rp-editorial-top.is-on{opacity:1;pointer-events:auto}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

export function mount(root, options = {}) {
  if (!root) throw new Error("editorial-landing: root required");
  root.classList.add("rp-editorial");
  const header = root.querySelector(options.header || "header");
  if (header) header.classList.add("rp-editorial-header");
  let lastY = scrollY;
  const onScroll = () => {
    if (header) header.classList.toggle("is-hidden", scrollY > lastY && scrollY > 120);
    lastY = scrollY;
    top.classList.toggle("is-on", scrollY > innerHeight);
  };
  const items = [...root.querySelectorAll(options.accordion || "[data-accordion]")];
  const cleanups = [];
  items.forEach((item, i) => {
    item.classList.add("rp-editorial-item");
    const btn = item.querySelector("button");
    const body = item.querySelector(".body") || item.querySelector("[data-body]");
    if (!btn || !body) return;
    body.classList.add("body");
    if (!body.firstElementChild) { const inner = document.createElement("div"); inner.innerHTML = body.innerHTML; body.textContent = ""; body.appendChild(inner); }
    const onClick = () => {
      const open = item.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", String(open));
    };
    btn.setAttribute("aria-expanded", String(item.classList.contains("is-open")));
    btn.addEventListener("click", onClick);
    cleanups.push(() => btn.removeEventListener("click", onClick));
  });
  const reveal = [...root.querySelectorAll(options.reveal || "main > section,main > article")];
  const io = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
  }, { threshold: 0.08 }) : null;
  reveal.forEach((el) => { el.classList.add("rp-editorial-reveal"); if (io) io.observe(el); else el.classList.add("is-in"); });
  const top = document.createElement("button"); top.className = "rp-editorial-top"; top.setAttribute("aria-label", "Back to top"); top.textContent = "↑";
  top.addEventListener("click", () => scrollTo({ top: 0, behavior: "smooth" }));
  document.body.appendChild(top);
  addEventListener("scroll", onScroll, { passive: true }); onScroll();
  return () => { removeEventListener("scroll", onScroll); if (io) io.disconnect(); cleanups.forEach((fn) => fn()); top.remove(); };
}
