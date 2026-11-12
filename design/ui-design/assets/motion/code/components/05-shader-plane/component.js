/* 05-shader-plane — WebGL2 full-screen fragment plane with graceful fallback */
(function () {
  "use strict";

  const VERT = `#version 300 es
in vec2 a_pos;
void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }`;

  const FRAG = `#version 300 es
precision highp float;
uniform vec2 u_res;
uniform float u_time;
uniform vec2 u_mouse;
uniform float u_progress;
out vec4 outColor;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    v += a * noise(p);
    p *= 2.02;
    a *= 0.5;
  }
  return v;
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p = uv * 2.0 - 1.0;
  p.x *= u_res.x / u_res.y;
  vec2 m = u_mouse * 2.0 - 1.0;
  m.x *= u_res.x / u_res.y;

  float t = u_time * 0.18;
  float r = length(p);
  float n = fbm(p * 1.8 + vec2(t * 0.3, -t * 0.2));
  float rings = sin(r * 13.0 - t * 3.2 + n * 3.0 + u_progress * 2.0);
  float ring = smoothstep(0.72, 1.0, rings) * 0.16;
  float glow = 0.18 * exp(-length(p - m) * 3.2);
  float sweep = 0.05 * exp(-abs(p.y - sin(p.x * 1.4 + t) * 0.4) * 6.0);

  vec3 base = mix(vec3(0.028, 0.035, 0.048), vec3(0.055, 0.075, 0.11), uv.y);
  vec3 warm = vec3(0.95, 0.72, 0.38);
  vec3 cool = vec3(0.35, 0.66, 0.82);
  vec3 col = base + warm * ring * (0.6 + u_progress * 0.8) + cool * glow + cool * sweep;
  col += (hash(gl_FragCoord.xy + floor(u_time * 20.0)) - 0.5) * 0.028;
  col *= smoothstep(1.7, 0.2, r);
  outColor = vec4(col, 1.0);
}`;

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function compile(gl, type, src) {
    const sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(sh);
      gl.deleteShader(sh);
      throw new Error(log || "shader compile failed");
    }
    return sh;
  }

  function mount(root, options = {}) {
    if (!root) throw new Error("shader: root required");
    const canvas = root.querySelector(".rf-shader__canvas");
    const pauseBtn = root.querySelector(".rf-shader__pause");
    const pulseBtn = root.querySelector("[data-pulse]");
    const statusEl = root.querySelector("[data-status]");
    const reduceMQ = matchMedia("(prefers-reduced-motion: reduce)");

    const ac = new AbortController();
    const { signal } = ac;
    let reduced = reduceMQ.matches;
    let gl = null;
    let program = null;
    let buffer = null;
    let raf = 0;
    let last = performance.now();
    let time = 0;
    let frames = 0;
    let paused = false;
    let manualPause = false;
    let mouse = { x: 0.62, y: 0.42 };
    let mouseTarget = { x: 0.62, y: 0.42 };
    let progress = 0;
    let progressTarget = 0;
    let pulseTimer = 0;
    let uRes = null, uTime = null, uMouse = null, uProgress = null;
    let dpr = 1;

    function fail() {
      root.classList.add("is-fallback");
      if (statusEl) statusEl.textContent = "fallback";
    }

    function initGL() {
      gl = canvas.getContext("webgl2", {
        antialias: false,
        alpha: false,
        depth: false,
        stencil: false,
        powerPreference: "high-performance",
      });
      if (!gl) { fail(); return false; }
      try {
        const vs = compile(gl, gl.VERTEX_SHADER, VERT);
        const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
        program = gl.createProgram();
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);
        gl.deleteShader(vs);
        gl.deleteShader(fs);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
          throw new Error(gl.getProgramInfoLog(program) || "link failed");
        }
        gl.useProgram(program);
        buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        const loc = gl.getAttribLocation(program, "a_pos");
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

        uRes = gl.getUniformLocation(program, "u_res");
        uTime = gl.getUniformLocation(program, "u_time");
        uMouse = gl.getUniformLocation(program, "u_mouse");
        uProgress = gl.getUniformLocation(program, "u_progress");
        return true;
      } catch (err) {
        fail();
        return false;
      }
    }

    function resize() {
      if (!gl) return;
      const r = root.getBoundingClientRect();
      dpr = Math.min(devicePixelRatio || 1, 2);
      const w = Math.max(1, Math.floor(r.width * dpr));
      const h = Math.max(1, Math.floor(r.height * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
        gl.viewport(0, 0, w, h);
      }
    }

    function draw() {
      if (!gl) return;
      resize();
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uTime, time);
      gl.uniform2f(uMouse, mouse.x, mouse.y);
      gl.uniform1f(uProgress, progress);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      frames++;
    }

    function frame(now) {
      if (paused) return;
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      time += dt;
      mouse.x += (mouseTarget.x - mouse.x) * 0.08;
      mouse.y += (mouseTarget.y - mouse.y) * 0.08;
      progress += (progressTarget - progress) * 0.06;
      draw();
      if (window.__rfStats && window.__rfStats.shader) {
        // getters read the live values; no assignment here
      }
      raf = requestAnimationFrame(frame);
    }

    function start() {
      if (reduced || paused) return;
      last = performance.now();
      if (!raf) raf = requestAnimationFrame(frame);
    }

    function stop() {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    }

    function setPaused(next, manual) {
      paused = next;
      if (manual) manualPause = next;
      pauseBtn.textContent = next ? "Play" : "Pause";
      pauseBtn.setAttribute("aria-pressed", next ? "true" : "false");
      root.classList.toggle("is-paused", next);
      if (statusEl) statusEl.textContent = next ? "paused" : reduced ? "static" : "running";
      if (next) stop(); else start();
    }

    function onPointerMove(e) {
      const r = root.getBoundingClientRect();
      mouseTarget.x = clamp((e.clientX - r.left) / r.width, 0, 1);
      mouseTarget.y = clamp(1 - (e.clientY - r.top) / r.height, 0, 1);
    }

    function onPulse() {
      progressTarget = 1;
      clearTimeout(pulseTimer);
      pulseTimer = setTimeout(() => { progressTarget = 0; }, 700);
    }

    function onVisibility() {
      if (document.hidden) stop();
      else if (!manualPause && !reduced) start();
    }

    function onContextLost(e) {
      e.preventDefault();
      stop();
      fail();
      if (statusEl) statusEl.textContent = "context lost";
    }

    function onContextRestored() {
      root.classList.remove("is-fallback");
      if (initGL()) {
        if (statusEl) statusEl.textContent = reduced ? "static" : "running";
        if (!reduced && !manualPause) start();
        draw();
      }
    }

    const ok = initGL();
    if (!ok) {
      reduceMQ.addEventListener("change", () => {}, { signal });
      window.__rfStats = window.__rfStats || {};
      window.__rfStats.shader = { ok: false, frames: 0, paused: true };
      return function dispose() {
        ac.abort();
        root.classList.remove("is-fallback");
        if (window.__rfStats) window.__rfStats.shader = null;
      };
    }

    canvas.addEventListener("webglcontextlost", onContextLost, { signal });
    canvas.addEventListener("webglcontextrestored", onContextRestored, { signal });
    root.addEventListener("pointermove", onPointerMove, { signal });
    pauseBtn.addEventListener("click", () => setPaused(!paused, true), { signal });
    pulseBtn.addEventListener("click", onPulse, { signal });
    document.addEventListener("visibilitychange", onVisibility, { signal });

    const onReduceChange = () => {
      reduced = reduceMQ.matches;
      if (reduced) {
        stop();
        draw();
        if (statusEl) statusEl.textContent = "static";
      } else if (!manualPause) {
        if (statusEl) statusEl.textContent = "running";
        start();
      }
    };
    reduceMQ.addEventListener("change", onReduceChange, { signal });

    if (reduced) {
      draw();
      if (statusEl) statusEl.textContent = "static";
    } else {
      start();
    }

    window.__rfStats = window.__rfStats || {};
    window.__rfStats.shader = {
      get ok() { return !!gl; },
      get frames() { return frames; },
      get paused() { return paused; },
      get dpr() { return dpr; },
    };

    return function dispose() {
      ac.abort();
      stop();
      clearTimeout(pulseTimer);
      if (gl) {
        if (program) gl.deleteProgram(program);
        if (buffer) gl.deleteBuffer(buffer);
      }
      gl = null;
      program = null;
      buffer = null;
      root.classList.remove("is-paused", "is-fallback");
      if (window.__rfStats) window.__rfStats.shader = null;
    };
  }

  window.RFShader = { mount };

  function autoMount() {
    if (window.__RF_NO_AUTO__) return;
    const root = document.querySelector('[data-rf="shader-plane"]');
    if (!root || root.dataset.rfMounted === "1") return;
    root.dataset.rfMounted = "1";
    const dispose = mount(root);
    window.__rfDispose = dispose;
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount, { once: true });
  } else {
    autoMount();
  }
})();
