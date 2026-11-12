/* Motion snippets — 8 primitives.
   Each block is delimited by ==== <id> ====; query_corpus.py still lists ids. */

/* ==== dpr-canvas ==== */
/* dpr-canvas.js — size a canvas to its CSS box with a capped devicePixelRatio.
 * Cap at 2: 3x screens rarely justify 3x pixels.
 */

function fitCanvas(canvas, options) {
  const opt = options || {};
  const cap = opt.dprCap == null ? 2 : opt.dprCap;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, cap);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { width: rect.width, height: rect.height, dpr: dpr, ctx: ctx };
  }

  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  resize();

  return {
    resize: resize,
    ctx: ctx,
    dispose: function () { observer.disconnect(); },
  };
}

/* ==== friction ==== */
/* friction.js — velocity + exponential friction for drag/wheel systems.
 * The same numbers as the measured belt/orbit cases; treat them as ranges.
 */

function createMotionState(options) {
  const opt = options || {};
  return {
    value: opt.value || 0,
    target: opt.target || 0,
    velocity: opt.velocity || 0,
    baseSpeed: opt.baseSpeed == null ? 62 : opt.baseSpeed,
    maxSpeed: opt.maxSpeed == null ? 900 : opt.maxSpeed,
    friction: opt.friction == null ? 1.1 : opt.friction,
  };
}

function stepFriction(state, dt, target) {
  if (typeof target === "number") state.target = target;
  // Exponential decay is frame-rate independent; do not use velocity *= 0.95.
  state.velocity *= Math.exp(-state.friction * dt);
  state.value += state.velocity * dt;
  return state.value;
}

function addImpulse(state, impulse) {
  state.velocity = Math.max(-state.maxSpeed, Math.min(state.maxSpeed, state.velocity + impulse));
}

/* Boost from wheel delta, normalised across deltaMode. */
function wheelImpulse(event, strength) {
  const factor = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1;
  return event.deltaY * factor * (strength == null ? 0.0014 : strength);
}

/* ==== io-reveal ==== */
/* io-reveal.js — one-shot IntersectionObserver reveal with a terminal reduced state.
 * Observed defaults: rootMargin "200px", threshold 0, 450ms, 16px.
 */

function mountReveal(root, options) {
  const opt = options || {};
  const selector = opt.selector || ".reveal";
  const rootMargin = opt.rootMargin || "200px";
  const threshold = opt.threshold == null ? 0 : opt.threshold;
  const items = Array.from(root.querySelectorAll(selector));
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  function show(el) {
    el.classList.add("is-in");
  }

  if (reduce.matches || !("IntersectionObserver" in window)) {
    items.forEach(show);
    return function dispose() {};
  }

  const io = new IntersectionObserver(function (entries) {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      show(entry.target);
      io.unobserve(entry.target);
    }
  }, { rootMargin: rootMargin, threshold: threshold });

  items.forEach(function (el) { io.observe(el); });

  function onReduceChange() {
    if (reduce.matches) items.forEach(show);
  }
  reduce.addEventListener("change", onReduceChange);

  return function dispose() {
    io.disconnect();
    reduce.removeEventListener("change", onReduceChange);
  };
}

/* ==== lerp ==== */
/* lerp.js — frame-rate-independent interpolation primitives.
 * Copy into your module (or prefix with `export`).
 */

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

/* Exponential smoothing that behaves the same at 60/120/144 Hz.
 * `smoothing` is the fraction of the remaining distance left after 1 second
 * (0.001 = fast, 0.05 = slow). */
function damp(current, target, smoothing, dt) {
  return lerp(target, current, Math.pow(smoothing, dt));
}

/* Wrap a value into [0, length). */
function wrap(value, length) {
  return ((value % length) + length) % length;
}

/* Rubber-band a value outside [min, max]: the further out, the harder. */
function rubber(value, min, max, strength) {
  if (value < min) return min - Math.pow(min - value, 0.85) * (strength || 0.15);
  if (value > max) return max + Math.pow(value - max, 0.85) * (strength || 0.15);
  return value;
}

/* ==== pointer-gestures ==== */
/* pointer-gestures.js — 8-direction drag + wheel normalisation.
 * Register the document once; map every pointer move to a direction.
 */

function createGestures(root, options) {
  const opt = options || {};
  const threshold = opt.threshold == null ? 6 : opt.threshold;
  const onMove = opt.onMove || function () {};
  const onRelease = opt.onRelease || function () {};
  const state = { down: false, x: 0, y: 0, lastX: 0, lastY: 0, dx: 0, dy: 0, t: 0 };

  function direction(dx, dy) {
    if (Math.abs(dx) < threshold && Math.abs(dy) < threshold) return null;
    if (Math.abs(dx) > Math.abs(dy) * 1.4) return dx > 0 ? "E" : "W";
    if (Math.abs(dy) > Math.abs(dx) * 1.4) return dy > 0 ? "S" : "N";
    return dx > 0 ? (dy > 0 ? "SE" : "NE") : (dy > 0 ? "SW" : "NW");
  }

  function down(event) {
    state.down = true;
    state.x = state.lastX = event.clientX;
    state.y = state.lastY = event.clientY;
    state.t = performance.now();
    if (root.setPointerCapture) root.setPointerCapture(event.pointerId);
  }

  function move(event) {
    if (!state.down) return;
    const dx = event.clientX - state.lastX;
    const dy = event.clientY - state.lastY;
    state.lastX = event.clientX;
    state.lastY = event.clientY;
    state.dx += dx;
    state.dy += dy;
    onMove({ dx: dx, dy: dy, totalX: state.dx, totalY: state.dy, direction: direction(state.dx, state.dy) });
  }

  function up() {
    if (!state.down) return;
    state.down = false;
    onRelease({ totalX: state.dx, totalY: state.dy, elapsed: performance.now() - state.t });
  }

  root.addEventListener("pointerdown", down);
  root.addEventListener("pointermove", move);
  root.addEventListener("pointerup", up);
  root.addEventListener("pointercancel", up);

  return function dispose() {
    root.removeEventListener("pointerdown", down);
    root.removeEventListener("pointermove", move);
    root.removeEventListener("pointerup", up);
    root.removeEventListener("pointercancel", up);
  };
}

function normalizeWheel(event) {
  const factor = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1;
  return { x: event.deltaX * factor, y: event.deltaY * factor };
}

/* ==== spring ==== */
/* spring.js — v5.0 dt-based spring with explicit damping ratio.
 * zeta=1 is critically damped (no overshoot); zeta<1 has a small bounce.
 * Legacy k=120/damping=20 is zeta≈0.91, NOT critical.
 */

function createSpring(options) {
  const opt = options || {};
  const zeta = opt.zeta == null ? 1 : opt.zeta;
  const hz = opt.hz == null ? 1.8 : opt.hz;
  const omega = 2 * Math.PI * hz;
  let value = opt.value || 0;
  let velocity = 0;
  let target = opt.target || 0;

  return {
    get value() { return value; },
    get velocity() { return velocity; },
    get zeta() { return zeta; },
    set target(next) { target = next; },
    step(next, dt) {
      if (typeof next === "number") target = next;
      const step = Math.min(Math.max(dt, 0), 1 / 30);
      const accel = omega * omega * (target - value) - 2 * zeta * omega * velocity;
      velocity += accel * step;
      value += velocity * step;
      return value;
    },
    reset(next) { value = next; velocity = 0; },
  };
}

/* A simple, readable landing spring: returns a 0..1 progress with a soft
 * settle. `duration` is approximate (the spring is integrated). */
function springProgress(elapsed, duration) {
  const t = Math.min(1, elapsed / duration);
  const c = 1.70158;
  const c3 = c + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2);
}

/* ==== sticky-pin ==== */
/* sticky-pin.js — scroll progress for a pinned section.
 * Returns 0..1 across the pin budget; no scroll hijacking.
 */

function mountPin(section, options) {
  const opt = options || {};
  const budget = opt.budget || 3.2;          // 320vh runway
  const onProgress = opt.onProgress || function () {};
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  if (reduce.matches) {
    onProgress(1);
    return function dispose() {};
  }

  let frame = 0;
  let last = -1;

  function update() {
    frame = 0;
    const rect = section.getBoundingClientRect();
    const total = Math.max(1, section.offsetHeight - window.innerHeight);
    const progress = Math.max(0, Math.min(1, -rect.top / total));
    if (Math.abs(progress - last) > 0.001) {
      last = progress;
      onProgress(progress);
    }
  }

  function onScroll() {
    if (!frame) frame = requestAnimationFrame(update);
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  update();

  return function dispose() {
    if (frame) cancelAnimationFrame(frame);
    window.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
  };
}

/* For a CSS-only version: the section is `height: calc(100vh * budget)` and
 * the inner stage is `position: sticky; top: 0; height: 100vh`. */

/* ==== webgl-boilerplate ==== */
/* webgl-boilerplate.js — WebGL2 full-screen plane with compile/link errors and context loss.
 * One covering triangle; four uniforms; pause-friendly.
 */

function createShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error("shader compile failed: " + log);
  }
  return shader;
}

function createProgram(gl, fragmentSource) {
  const vert = "#version 300 es\nin vec2 aPos;\nvoid main(){gl_Position=vec4(aPos,0.,1.);}";
  const vs = createShader(gl, gl.VERTEX_SHADER, vert);
  const fs = createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error("program link failed: " + gl.getProgramInfoLog(program));
  }
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  return program;
}

function mountPlane(canvas, fragmentSource, uniforms) {
  const gl = canvas.getContext("webgl2", { antialias: false, alpha: false });
  if (!gl) return null;

  let program = createProgram(gl, fragmentSource);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(program, "aPos");
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

  function draw(time, width, height, mouseX, mouseY, progress) {
    gl.viewport(0, 0, width, height);
    gl.useProgram(program);
    if (uniforms.res) gl.uniform2f(uniforms.res, width, height);
    if (uniforms.time) gl.uniform1f(uniforms.time, time);
    if (uniforms.mouse) gl.uniform2f(uniforms.mouse, mouseX, mouseY);
    if (uniforms.progress) gl.uniform1f(uniforms.progress, progress);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  function dispose() {
    gl.deleteBuffer(buffer);
    gl.deleteProgram(program);
  }

  return { gl: gl, draw: draw, dispose: dispose };
}
