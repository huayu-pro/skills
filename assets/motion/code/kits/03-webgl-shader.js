/* 03 — WebGL fullscreen shader: grain + tunnel-ish warp, pointer + time uniforms. */
export const css = `.rp-shader{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none}@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
`;

const VERT = `#version 300 es
in vec2 a; void main(){ gl_Position=vec4(a,0.,1.); }`;
const FRAG = `#version 300 es
precision highp float;
uniform vec2 u_res; uniform float u_time; uniform vec2 u_mouse;
out vec4 o;
float hash(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
void main(){
  vec2 uv=(gl_FragCoord.xy-.5*u_res)/min(u_res.x,u_res.y);
  float r=length(uv); float a=atan(uv.y,uv.x);
  float t=u_time*.25;
  float lines=sin(a*18.+r*26.-t*4.)*.5+.5;
  float rings=sin(r*38.-t*8.)*.5+.5;
  vec3 col=mix(vec3(.03,.04,.06),vec3(.92,.94,.96),smoothstep(.05,.95,r));
  col=mix(col,vec3(.1,.55,.9),lines*.12*smoothstep(.2,1.,r));
  col+=rings*.06;
  vec2 m=(u_mouse/u_res-.5); col+=.08*exp(-length(uv-m)*8.);
  col+=(hash(gl_FragCoord.xy+fract(u_time))-.5)*.05;
  o=vec4(col,1.);
}`;

export function mount(root, options = {}) {
  if (!root) throw new Error("webgl-shader: root required");
  const canvas = document.createElement("canvas");
  canvas.className = "rp-shader";
  root.appendChild(canvas);
  const gl = canvas.getContext("webgl2", { antialias: false, alpha: false });
  if (!gl) { canvas.remove(); return () => {}; }
  const compile = (type, src) => {
    const sh = gl.createShader(type); gl.shaderSource(sh, src); gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh) || "shader");
    return sh;
  };
  let prog;
  try {
    prog = gl.createProgram();
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) || "link");
  } catch (e) { canvas.remove(); console.warn("webgl-shader:", e.message); return () => {}; }
  gl.useProgram(prog);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, "a");
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const uRes = gl.getUniformLocation(prog, "u_res");
  const uTime = gl.getUniformLocation(prog, "u_time");
  const uMouse = gl.getUniformLocation(prog, "u_mouse");
  const mouse = { x: innerWidth / 2, y: innerHeight / 2 };
  const onMove = (e) => { const r = canvas.getBoundingClientRect(); mouse.x = e.clientX - r.left; mouse.y = r.height - (e.clientY - r.top); };
  const resize = () => {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(root.clientWidth * dpr));
    canvas.height = Math.max(1, Math.round(root.clientHeight * dpr));
    gl.viewport(0, 0, canvas.width, canvas.height);
  };
  addEventListener("pointermove", onMove, { passive: true });
  addEventListener("resize", resize);
  resize();
  let raf = 0; const t0 = performance.now();
  const loop = (t) => {
    gl.uniform2f(uRes, canvas.width, canvas.height);
    gl.uniform1f(uTime, (t - t0) / 1000);
    gl.uniform2f(uMouse, mouse.x, mouse.y);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    raf = requestAnimationFrame(loop);
  };
  raf = requestAnimationFrame(loop);
  return () => { cancelAnimationFrame(raf); removeEventListener("pointermove", onMove); removeEventListener("resize", resize); canvas.remove(); };
}
