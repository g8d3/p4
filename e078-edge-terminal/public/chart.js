/* GLChart — WebGL candlestick chart (no dependencies).
 * Shapes go through one shader on the GPU; axis labels are HTML overlays.
 * Supports wheel zoom, drag pan, pinch, crosshair + OHLC tooltip. */

'use strict';

class GLChart {
  constructor(canvas, opts = {}) {
    this.canvas = canvas;
    this.opts = Object.assign({ padRight: 62, axisBottom: 18, volH: 46, padLeft: 6, padTop: 8 }, opts);
    this.candles = [];
    this.overlays = [];
    this.view = { i0: 0, i1: 60 };
    this.hover = null;       // {i, x, y}
    this.dpr = 1;
    this.onHover = opts.onHover || null;
    this.cpuFallback = false;

    const gl = canvas.getContext('webgl2', { antialias: true, alpha: false, powerPreference: 'high-performance' })
           || canvas.getContext('webgl', { antialias: true, alpha: false });
    this.gl = gl;
    if (!gl) { this.cpuFallback = true; return; }

    const vs = `attribute vec2 a_pos; attribute vec4 a_col; uniform vec2 u_res;
      varying vec4 v_col;
      void main(){ v_col = a_col;
        vec2 c = vec2(a_pos.x / u_res.x * 2.0 - 1.0, 1.0 - a_pos.y / u_res.y * 2.0);
        gl_Position = vec4(c, 0.0, 1.0); }`;
    const fs = `precision mediump float; varying vec4 v_col;
      void main(){ gl_FragColor = vec4(v_col.rgb * v_col.a, v_col.a); }`;
    const prog = this._program(vs, fs);
    if (!prog) { this.cpuFallback = true; return; }
    this.prog = prog;
    this.buf = gl.createBuffer();

    this.aPos = gl.getAttribLocation(prog, 'a_pos');
    this.aCol = gl.getAttribLocation(prog, 'a_col');
    this.uRes = gl.getUniformLocation(prog, 'u_res');

    this._bindEvents();
    this._resize();
    if (typeof ResizeObserver !== 'undefined') {
      this._ro = new ResizeObserver(() => this._resize());
      this._ro.observe(canvas);
    } else {
      window.addEventListener('resize', () => this._resize());
    }
  }

  _program(vsSrc, fsSrc) {
    const gl = this.gl;
    const mk = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.error(gl.getShaderInfoLog(s)); return null; }
      return s;
    };
    const vs = mk(gl.VERTEX_SHADER, vsSrc), fs = mk(gl.FRAGMENT_SHADER, fsSrc);
    if (!vs || !fs) return null;
    const p = gl.createProgram();
    gl.attachShader(p, vs); gl.attachShader(p, fs); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { console.error(gl.getProgramInfoLog(p)); return null; }
    return p;
  }

  /* ----------------------------------------------------------- events */
  _bindEvents() {
    const c = this.canvas;
    this._pointers = new Map();
    let dragging = false, lastX = 0, pinchDist = 0;

    c.addEventListener('pointerdown', (e) => {
      c.setPointerCapture(e.pointerId);
      this._pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (this._pointers.size === 1) { dragging = true; lastX = e.clientX; }
      if (this._pointers.size === 2) pinchDist = this._pinch();
    });
    c.addEventListener('pointermove', (e) => {
      const r = c.getBoundingClientRect();
      if (this._pointers.has(e.pointerId)) this._pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

      if (this._pointers.size === 2) {
        const d = this._pinch();
        if (pinchDist > 0 && d > 0) this._zoom(1 - (d - pinchDist) / 220, e.clientX - r.left);
        pinchDist = d;
        return;
      }
      if (dragging && e.buttons) {
        const dx = e.clientX - lastX; lastX = e.clientX;
        if (dx) this._pan(dx);
      }
      this._setHover(e.clientX - r.left, e.clientY - r.top);
    });
    const up = (e) => {
      this._pointers.delete(e.pointerId);
      if (this._pointers.size < 2) pinchDist = 0;
      if (this._pointers.size === 0) { dragging = false; this._setHover(null); }
    };
    c.addEventListener('pointerup', up);
    c.addEventListener('pointercancel', up);
    c.addEventListener('pointerleave', up);
    c.addEventListener('wheel', (e) => {
      e.preventDefault();
      const r = c.getBoundingClientRect();
      const factor = e.deltaY > 0 ? 1.12 : 1 / 1.12;
      this._zoom(factor, e.clientX - r.left);
    }, { passive: false });
  }
  _pinch() {
    const p = [...this._pointers.values()];
    if (p.length < 2) return 0;
    return Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
  }

  _zoom(factor, anchorX) {
    const v = this.view;
    const n = this.candles.length;
    const plotW = this._plotW();
    const frac = plotW ? (anchorX - this.opts.padLeft) / plotW : 0.5;
    let count = (v.i1 - v.i0 + 1) * factor;
    count = Math.max(12, Math.min(n, count));
    const anchor = v.i0 + frac * (v.i1 - v.i0 + 1);
    let i0 = anchor - frac * count;
    let i1 = i0 + count - 1;
    if (i1 > n - 1) { i1 = n - 1; i0 = i1 - count + 1; }
    if (i0 < 0) { i0 = 0; i1 = Math.min(n - 1, count - 1); }
    this.view = { i0, i1 };
    this.draw();
  }
  _pan(dxPixels) {
    const v = this.view;
    const perBar = this._plotW() / (v.i1 - v.i0 + 1);
    const shift = -(dxPixels / perBar);
    let i0 = v.i0 + shift, i1 = v.i1 + shift;
    const n = this.candles.length;
    if (i0 < 0) { i1 -= i0; i0 = 0; }
    if (i1 > n - 1) { i0 -= (i1 - (n - 1)); i1 = n - 1; }
    if (i0 < 0) i0 = 0;
    this.view = { i0, i1 };
    this.draw();
  }
  _setHover(x, y) {
    if (x == null) { this.hover = null; this.draw(); return; }
    const v = this.view;
    const perBar = this._plotW() / (v.i1 - v.i0 + 1);
    let i = Math.round(v.i0 + (x - this.opts.padLeft) / perBar - 0.5);
    i = Math.max(Math.floor(v.i0), Math.min(Math.ceil(v.i1), i));
    const snapX = this.opts.padLeft + (i - v.i0 + 0.5) * perBar;
    this.hover = { i, x: snapX, y };
    this.draw();
    if (this.onHover) this.onHover(this.candles[i] || null, { x, y });
  }

  /* ------------------------------------------------------------ data */
  setData(candles, overlays = []) {
    const atEnd = this.candles.length && this.view.i1 >= this.candles.length - 1.5;
    this.candles = candles || [];
    this.overlays = overlays;
    const n = this.candles.length;
    if (!n) return;
    if (!this._userMoved || atEnd) this.view = { i0: Math.max(0, n - 90), i1: n - 1 };
    if (this.view.i1 > n - 1) this.view.i1 = n - 1;
    if (this.view.i0 < 0) this.view.i0 = 0;
    this.draw();
  }
  fit(count = 90) {
    const n = this.candles.length;
    if (!n) return;
    this.view = { i0: Math.max(0, n - count), i1: n - 1 };
    this.draw();
  }

  _resize() {
    const c = this.canvas;
    const rect = c.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.width = Math.round(rect.width * this.dpr);
    c.height = Math.round(rect.height * this.dpr);
    this.w = rect.width; this.h = rect.height;
    this.draw();
  }
  _plotW() { return (this.w - this.opts.padLeft - this.opts.padRight) || 1; }

  /* ----------------------------------------------------------- render */
  draw() {
    if (this.cpuFallback || !this.gl || !this.w) return;
    const gl = this.gl, o = this.opts;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0.039, 0.055, 0.078, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    if (!this.candles.length) return;

    const v = this.view;
    const plotL = o.padLeft, plotR = this.w - o.padRight;
    const plotT = o.padTop, plotB = this.h - o.axisBottom - o.volH;
    const volT = plotB + 8, volB = this.h - o.axisBottom;

    const i0 = Math.max(0, Math.floor(v.i0)), i1 = Math.min(this.candles.length - 1, Math.ceil(v.i1));
    const visible = this.candles.slice(i0, i1 + 1);

    let min = Infinity, max = -Infinity;
    for (const c of visible) { if (c.l < min) min = c.l; if (c.h > max) max = c.h; }
    this.overlays.forEach((ov) => {
      for (let i = i0; i <= i1; i++) {
        const val = ov.values[i];
        if (val == null) continue;
        if (val < min) min = val; if (val > max) max = val;
      }
    });
    if (!isFinite(min) || !isFinite(max) || max === min) { min = min * 0.99; max = max * 1.01; }
    const pad = (max - min) * 0.06;
    min -= pad; max += pad;

    const perBar = (plotR - plotL) / (v.i1 - v.i0 + 1);
    const bodyW = Math.max(1, perBar * 0.66);
    const xOf = (i) => plotL + (i - v.i0 + 0.5) * perBar;
    const yOf = (p) => plotT + (max - p) / (max - min) * (plotB - plotT);

    let maxVol = 0;
    for (const c of visible) if (c.v > maxVol) maxVol = c.v;
    const volH = volB - volT;

    const verts = [];
    const quad = (x0, y0, x1, y1, r, g, b, a) => {
      verts.push(x0, y0, r, g, b, a, x1, y0, r, g, b, a, x0, y1, r, g, b, a,
                 x0, y1, r, g, b, a, x1, y0, r, g, b, a, x1, y1, r, g, b, a);
    };

    // grid: horizontal price lines + vertical time lines
    for (let k = 0; k <= 5; k++) {
      const y = plotT + (plotB - plotT) * (k / 5);
      quad(plotL, y, plotR, y + 0.5, 1, 1, 1, 0.055);
    }
    const step = Math.max(6, Math.round(70 / perBar));
    for (let i = Math.ceil(i0 / step) * step; i <= i1; i += step) {
      const x = xOf(i); quad(x - 0.5, plotT, x, volB, 1, 1, 1, 0.04);
    }

    // volume
    for (let i = i0; i <= i1; i++) {
      const c = this.candles[i];
      const h = maxVol ? (c.v / maxVol) * volH : 0;
      const up = c.c >= c.o;
      quad(xOf(i) - bodyW / 2, volB - h, xOf(i) + bodyW / 2, volB,
           up ? 0.24 : 1, up ? 0.86 : 0.37, up ? 0.59 : 0.43, 0.32);
    }

    // candles
    for (let i = i0; i <= i1; i++) {
      const c = this.candles[i];
      const up = c.c >= c.o;
      const col = up ? [0.24, 0.86, 0.59] : [1, 0.37, 0.43];
      const x = xOf(i);
      // wick
      quad(x - 0.5, yOf(c.h), x + 0.5, yOf(c.l), col[0], col[1], col[2], 0.95);
      // body
      const yo = yOf(c.o), yc = yOf(c.c);
      const top = Math.min(yo, yc), bot = Math.max(yo, yc);
      quad(x - bodyW / 2, top, x + bodyW / 2, Math.max(bot, top + 1), col[0], col[1], col[2], 0.95);
    }

    // overlays (moving averages) as thin segments
    for (const ov of this.overlays) {
      const [r, g, b] = ov.rgb;
      for (let i = Math.max(1, i0); i <= i1; i++) {
        const a = ov.values[i], p = ov.values[i - 1];
        if (a == null || p == null) continue;
        const x0 = xOf(i - 1), y0 = yOf(p), x1 = xOf(i), y1 = yOf(a);
        // segment as two triangles (quad-ish) with 1.6px thickness
        const t = 1.6;
        const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy) || 1;
        const nx = -dy / len * t, ny = dx / len * t;
        verts.push(x0 + nx, y0 + ny, r, g, b, 0.95, x1 + nx, y1 + ny, r, g, b, 0.95, x0 - nx, y0 - ny, r, g, b, 0.95,
                   x0 - nx, y0 - ny, r, g, b, 0.95, x1 + nx, y1 + ny, r, g, b, 0.95, x1 - nx, y1 - ny, r, g, b, 0.95);
      }
    }

    // last price line (dashed)
    const last = this.candles[this.candles.length - 1];
    const ly = yOf(last.c);
    if (ly > plotT && ly < plotB) {
      const up = last.c >= last.o;
      const col = up ? [0.24, 0.86, 0.59] : [1, 0.37, 0.43];
      for (let x = plotL; x < plotR; x += 9) quad(x, ly - 0.5, x + 5, ly + 0.5, col[0], col[1], col[2], 0.75);
    }

    // crosshair
    if (this.hover) {
      const hx = this.hover.x, hy = Math.max(plotT, Math.min(volB, this.hover.y));
      for (let y = plotT; y < volB; y += 7) quad(hx - 0.5, y, hx, y + 3.5, 0.5, 0.64, 1, 0.55);
      for (let x = plotL; x < plotR; x += 7) quad(x, hy - 0.5, x + 3.5, hy, 0.5, 0.64, 1, 0.55);
    }

    gl.useProgram(this.prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf);
    const data = new Float32Array(verts);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
    const stride = 6 * 4;
    gl.enableVertexAttribArray(this.aPos);
    gl.vertexAttribPointer(this.aPos, 2, gl.FLOAT, false, stride, 0);
    gl.enableVertexAttribArray(this.aCol);
    gl.vertexAttribPointer(this.aCol, 4, gl.FLOAT, false, stride, 8);
    gl.uniform2f(this.uRes, this.w, this.h);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.drawArrays(gl.TRIANGLES, 0, data.length / 6);

    // axis labels (HTML)
    if (this.opts.axisY) {
      let html = '';
      for (let k = 0; k <= 5; k++) {
        const price = max - (max - min) * (k / 5);
        const y = plotT + (plotB - plotT) * (k / 5);
        html += `<span style="top:${y.toFixed(1)}px">${this.opts.fmtPrice(price)}</span>`;
      }
      if (ly > plotT && ly < plotB) html += `<span style="top:${ly.toFixed(1)}px;color:#3ddc97">${this.opts.fmtPrice(last.c)}</span>`;
      this.opts.axisY.innerHTML = html;
    }
    if (this.opts.axisX) {
      const n = Math.max(3, Math.floor((plotR - plotL) / 95));
      let html = '';
      for (let k = 0; k <= n; k++) {
        const i = Math.round(v.i0 + (v.i1 - v.i0) * (k / n));
        const c = this.candles[Math.max(0, Math.min(this.candles.length - 1, i))];
        if (!c) continue;
        const x = xOf(Math.max(i0, Math.min(i1, i)));
        if (x < plotL + 24 || x > plotR - 24) continue; // never clip an edge label
        html += `<span style="left:${x.toFixed(1)}px">${this.opts.fmtTime(c.t)}</span>`;
      }
      this.opts.axisX.innerHTML = html;
    }
    this._geom = { plotL, plotR, plotT, plotB, min, max, xOf, yOf, i0, i1 };
  }

  geom() { return this._geom; }
}

window.GLChart = GLChart;
