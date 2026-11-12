/* 14-webgl-object — F4 merged component.
   Raw WebGL2, one covering triangle, one raymarched box.
   No Three.js, no textures, no external assets. */
(function () {
  "use strict";

  const VERT = `#version 300 es
in vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }`;

  const FRAG = `#version 300 es
precision highp float;
uniform vec2 u_res;
uniform float u_time;
uniform vec2 u_mouse;
out vec4 outColor;

mat2 rot(float a) {
  float c = cos(a), s = sin(a);
  return mat2(c, -s, s, c);
}

float sdBox(vec3 p, vec3 b) {
  vec3 q = abs(p) - b;
  return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}

float map(vec3 p) {
  p.xz *= rot(u_time * 0.35);
  p.xy *= rot(0.32);
  return sdBox(p, vec3(0.82));
}

vec3 calcNormal(vec3 p) {
  vec2 e = vec2(0.0015, 0.0);
  return normalize(vec3(
    map(p + e.xyy) - map(p - e.xyy),
    map(p + e.yxy) - map(p - e.yxy),
    map(p + e.yyx) - map(p - e.yyx)
  ));
}

void main() {
  vec2 uv = (gl_FragCoord.xy * 2.0 - u_res) / min(u_res.x, u_res.y);
  vec3 ro = vec3(0.0, 0.0, 3.4);
  ro.xz *= rot((u_mouse.x - 0.5) * 0.55);
  ro.y += (u_mouse.y - 0.5) * 0.35;

  vec3 fwd = normalize(-ro);
  vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), fwd));
  vec3 up = cross(fwd, right);
  vec3 rd = normalize(fwd * 1.8 + right * uv.x + up * uv.y);

  float t = 0.0;
  float d = 0.0;
  for (int i = 0; i < 80; i++) {
    d = map(ro + rd * t);
    if (d < 0.001 || t > 9.0) break;
    t += d;
  }

  vec3 col = vec3(0.018, 0.022, 0.032);
  if (d < 0.01) {
    vec3 p = ro + rd * t;
    vec3 n = calcNormal(p);
    vec3 light = normalize(vec3(0.55, 0.8, 0.45));
    float diff = max(dot(n, light), 0.0);
    float rim = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 28.0);
    col = vec3(0.07, 0.08, 0.11);
    col += diff * vec3(0.92, 0.70, 0.32);
    col += rim * vec3(0.16, 0.30, 0.50);
    col += spec * vec3(0.65);
  }
  col *= 1.0 - 0.22 * length(uv * 0.6);
  outColor = vec4(pow(col, vec3(0.4545)), 1.0);
}`;

  function createShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error("shader: " + log);
    }
    return shader;
  }

  function createProgram(gl) {
    const vs = createShader(gl, gl.VERTEX_SHADER, VERT);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, FRAG);
    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error("link: " + gl.getProgramInfoLog(program));
    }
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    return program;
  }

  function mount(root, options) {
    if (!root) throw new Error("webgl-object: root required");
    const opt = options || {};
    window.__rfStats = window.__rfStats || {};
    const canvas = root.querySelector(".mr-webgl__canvas");
    const fallback = root.querySelector(".mr-webgl__fallback");
    const pauseButton = root.querySelector("[data-pause]");
    const readout = root.querySelector(".mr-webgl__readout");
    if (!canvas) throw new Error("webgl-object: canvas required");

    const gl = canvas.getContext("webgl2", {
      antialias: false,
      alpha: false,
      powerPreference: "high-performance",
    });
    if (!gl) {
      if (fallback) fallback.hidden = false;
      canvas.hidden = true;
      if (readout) readout.textContent = "WebGL2 unavailable";
      if (window.__rfStats) window.__rfStats.webgl = { ok: false, frames: 0 };
      return function dispose() {};
    }

    let program;
    let buffer;
    let locations;
    try {
      program = createProgram(gl);
      buffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
      const aPos = gl.getAttribLocation(program, "aPos");
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
      locations = {
        res: gl.getUniformLocation(program, "u_res"),
        time: gl.getUniformLocation(program, "u_time"),
        mouse: gl.getUniformLocation(program, "u_mouse"),
      };
    } catch (error) {
      if (fallback) fallback.hidden = false;
      canvas.hidden = true;
      if (readout) readout.textContent = "shader failed";
      if (window.__rfStats) window.__rfStats.webgl = { ok: false, frames: 0 };
      return function dispose() {
        if (program) gl.deleteProgram(program);
      };
    }

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let reduced = reduce.matches;
    let paused = false;
    let hidden = false;
    let raf = 0;
    let frames = 0;
    let time = 0.6;
    let last = performance.now();
    let mouseX = 0.5;
    let mouseY = 0.5;
    let targetX = 0.5;
    let targetY = 0.5;
    let dpr = 1;

    function resize() {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.round(rect.width * dpr));
      const height = Math.max(1, Math.round(rect.height * dpr));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
    }

    function draw() {
      if (locations.res) gl.uniform2f(locations.res, canvas.width, canvas.height);
      if (locations.time) gl.uniform1f(locations.time, time);
      if (locations.mouse) gl.uniform2f(locations.mouse, mouseX, mouseY);
      gl.clearColor(0.02, 0.025, 0.035, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.useProgram(program);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      frames += 1;
      if (readout) readout.textContent = "frames " + frames;
      if (window.__rfStats) {
        window.__rfStats.webgl = { ok: true, frames: frames, reduced: reduced, paused: paused };
      }
    }

    function frame(now) {
      raf = 0;
      const dt = Math.min((now - last) / 1000, 1 / 30);
      last = now;
      if (!paused && !hidden) {
        time += dt;
        mouseX += (targetX - mouseX) * 0.12;
        mouseY += (targetY - mouseY) * 0.12;
        draw();
        raf = requestAnimationFrame(frame);
      }
    }

    function kick() {
      if (!raf && !paused && !hidden && !reduced) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    }

    function onPointer(event) {
      const rect = canvas.getBoundingClientRect();
      targetX = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
      targetY = Math.max(0, Math.min(1, 1 - (event.clientY - rect.top) / rect.height));
    }

    function onPause() {
      paused = !paused;
      if (pauseButton) {
        pauseButton.textContent = paused ? "Play" : "Pause";
        pauseButton.setAttribute("aria-pressed", paused ? "true" : "false");
      }
      if (paused && raf) { cancelAnimationFrame(raf); raf = 0; }
      if (!paused) kick();
    }

    function onVisibility() {
      hidden = document.hidden;
      if (hidden && raf) { cancelAnimationFrame(raf); raf = 0; }
      if (!hidden) kick();
    }

    function onReduceChange() {
      reduced = reduce.matches;
      if (reduced) {
        if (raf) { cancelAnimationFrame(raf); raf = 0; }
        time = 0.6;
        draw();
      } else {
        kick();
      }
    }

    function onLost(event) {
      event.preventDefault();
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      if (fallback) fallback.hidden = false;
      if (readout) readout.textContent = "context lost";
    }

    canvas.addEventListener("pointermove", onPointer);
    canvas.addEventListener("webglcontextlost", onLost);
    document.addEventListener("visibilitychange", onVisibility);
    reduce.addEventListener("change", onReduceChange);
    if (pauseButton) pauseButton.addEventListener("click", onPause);
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();
    draw();
    if (!reduced) kick();

    return function dispose() {
      if (raf) cancelAnimationFrame(raf);
      canvas.removeEventListener("pointermove", onPointer);
      canvas.removeEventListener("webglcontextlost", onLost);
      document.removeEventListener("visibilitychange", onVisibility);
      reduce.removeEventListener("change", onReduceChange);
      if (pauseButton) pauseButton.removeEventListener("click", onPause);
      ro.disconnect();
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      if (window.__rfStats) window.__rfStats.webgl = null;
    };
  }

  const root = document.querySelector('[data-rf="webgl-object"]');
  if (root) window.__rfDispose = mount(root);
  window.__rfMount = mount;
})();