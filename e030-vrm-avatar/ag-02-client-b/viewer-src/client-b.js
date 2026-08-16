import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin } from '@pixiv/three-vrm-animation';

const CLIENT_ID = 'B';

const state = {
  vrm: null,
  currentModel: null,
  idleOn: true,
  speaking: false,
  audio: null,
  mouthTimeline: null,
  mouthTimer: null,
  idleTime: 0,
  blinkPhase: 0,
  nextBlinkAt: 2,
  lookTarget: null,
  mixers: [],
  activeAnimation: null,
  renderer: null,
  scene: null,
  camera: null,
  clock: null,
  gltfLoader: null,
  container: null,
  socket: null,
};

function log(msg) {
  console.log('[client-B]', msg);
}

function makeRenderer() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setPixelRatio(1);
  return renderer;
}

function makeScene() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x11161f);

  const hemi = new THREE.HemisphereLight(0xffffff, 0x334455, 1.0);
  scene.add(hemi);

  const dir = new THREE.DirectionalLight(0xffffff, 2.4);
  dir.position.set(2, 3, 3);
  dir.castShadow = true;
  dir.shadow.mapSize.set(1024, 1024);
  dir.shadow.camera.near = 0.5;
  dir.shadow.camera.far = 15;
  dir.shadow.camera.left = -4;
  dir.shadow.camera.right = 4;
  dir.shadow.camera.top = 4;
  dir.shadow.camera.bottom = -4;
  dir.shadow.bias = -0.0004;
  scene.add(dir);

  const rim = new THREE.DirectionalLight(0x8fb8ff, 0.8);
  rim.position.set(-2, 2, -3);
  scene.add(rim);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(40, 40),
    new THREE.ShadowMaterial({ opacity: 0.28 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -1.4;
  ground.receiveShadow = true;
  scene.add(ground);

  return scene;
}

function makeCamera(aspect) {
  const camera = new THREE.PerspectiveCamera(22, aspect, 0.1, 50);
  camera.position.set(0, 1.05, 4.6);
  camera.lookAt(0, 1.05, 0);
  return camera;
}

function resize() {
  // Fixed vertical framebuffer for deterministic 608x1080 capture, regardless
  // of the headless window's reported inner size.
  const w = 608;
  const h = 1080;
  state.renderer.setSize(w, h, false);
  state.camera.aspect = w / h;
  state.camera.updateProjectionMatrix();
}

function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}`;
}

function send(msg) {
  if (state.socket && state.socket.readyState === WebSocket.OPEN) {
    state.socket.send(JSON.stringify(msg));
  }
}

function registerClient() {
  send({ type: 'register', id: CLIENT_ID, model: state.currentModel });
}

function respond(cmdId, ok, result = {}, error = null) {
  const out = { type: 'cmdResponse', cmdId, clientId: CLIENT_ID, ok };
  if (ok) {
    Object.assign(out, result);
  } else {
    out.error = error || 'unknown error';
  }
  return out;
}

function sendResponse(cmdId, ok, result = {}, error = null) {
  const msg = respond(cmdId, ok, result, error);
  send(msg);
  window.__lastCmdResponse = msg;
  log(`resp ${cmdId} ok=${ok}`);
}

function clearExpressions() {
  state.vrm?.expressionManager?.resetValues();
}

function setExpression(name, weight) {
  if (!state.vrm?.expressionManager) return { error: 'no expression manager' };
  const expr = state.vrm.expressionManager.getExpression(name);
  if (!expr) return { error: `unknown expression: ${name}` };
  const w = typeof weight === 'number' ? Math.max(0, Math.min(1, weight)) : 1;
  state.vrm.expressionManager.setValue(name, w);
  return { name, weight: w };
}

function setLookAt(x, y) {
  if (!state.vrm?.lookAt) return { error: 'no lookAt component' };
  if (!state.lookTarget) {
    state.lookTarget = new THREE.Object3D();
    state.scene.add(state.lookTarget);
  }
  const head = state.vrm.humanoid?.getNormalizedBoneNode('head');
  const headWorld = new THREE.Vector3();
  if (head) head.getWorldPosition(headWorld);
  else headWorld.set(0, 1.4, 0);
  state.lookTarget.position.set(headWorld.x + x, headWorld.y + y, headWorld.z + 1.5);
  state.vrm.lookAt.target = state.lookTarget;
  state.vrm.lookAt.autoUpdate = true;
  return { x, y };
}

function setBone(name, rotate) {
  if (!state.vrm?.humanoid) return { error: 'no humanoid' };
  const bone = state.vrm.humanoid.getNormalizedBoneNode(name);
  if (!bone) return { error: `unknown bone: ${name}` };
  const rx = Number(rotate?.[0] ?? 0);
  const ry = Number(rotate?.[1] ?? 0);
  const rz = Number(rotate?.[2] ?? 0);
  bone.rotation.set(rx, ry, rz);
  return { name, rotate: [rx, ry, rz] };
}

function listBones() {
  if (!state.vrm?.humanoid) return [];
  return Object.keys(state.vrm.humanoid.normalizedHumanBones || {}).sort();
}

function listExpressions() {
  if (!state.vrm?.expressionManager) return [];
  return state.vrm.expressionManager.expressions.map((e) => ({
    name: e.expressionName,
    weight: e.weight ?? 0,
  }));
}

function inspect() {
  if (!state.vrm) return { error: 'no model loaded' };
  const meta = state.vrm.meta || {};
  const exprs = listExpressions();
  const bones = listBones();
  return {
    model: state.currentModel,
    modelName: meta.name || null,
    metaVersion: meta.metaVersion || null,
    version: meta.version || null,
    authors: meta.authors || [],
    licenseUrl: meta.licenseUrl || null,
    bones,
    humanoid: bones.length,
    expressions: exprs,
    expressionCount: exprs.length,
    springBones: state.vrm.springBoneManager ? state.vrm.springBoneManager.joints.size : 0,
    renderer: {
      client: CLIENT_ID,
      webgl: state.renderer?.capabilities?.isWebGL2 ? 'WebGL2' : 'WebGL',
      size: state.renderer ? [state.renderer.domElement.width, state.renderer.domElement.height] : null,
    },
  };
}

function normalizeModel(model) {
  let m = String(model || '');
  if (/^https?:\/\//.test(m)) return m;
  m = m.replace(/^\/+/, '');
  m = m.replace(/^models\//, '');
  return `/models/${m}`;
}

function normalizeMedia(path) {
  if (/^https?:\/\//.test(path)) return path;
  let p = String(path || '');
  p = p.replace(/^\/+/, '');
  p = p.replace(/^media\//, '');
  return `/media/${p}`;
}

async function loadModel(model) {
  if (!model) return { error: 'model path required' };
  const url = normalizeModel(model);
  try {
    const gltf = await state.gltfLoader.loadAsync(url);
    const vrm = gltf.userData.vrm;
    if (!vrm) return { error: 'no VRM found in file' };

    if (state.vrm) {
      clearExpressions();
      state.scene.remove(state.vrm.scene);
    }
    state.vrm = vrm;
    state.currentModel = model;
    state.scene.add(vrm.scene);

    vrm.scene.position.set(0, -0.2, 0);
    const box = new THREE.Box3().setFromObject(vrm.scene);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const targetHeight = 2.8;
    const scale = targetHeight / maxDim;
    vrm.scene.scale.setScalar(scale);

    // Frame the camera on the model's actual center so the whole character
    // is visible in the vertical 608x1080 frame.
    const fovRad = THREE.MathUtils.degToRad(state.camera.fov);
    const halfH = Math.tan(fovRad / 2);
    const halfW = halfH * state.camera.aspect;
    const needDistH = (size.y * scale) / 2 / halfH;
    const needDistW = (size.x * scale) / 2 / halfW;
    const dist = Math.max(needDistH, needDistW) * 1.15 + Math.max(size.z * scale, 0.5);
    state.camera.position.set(0, center.y * scale + vrm.scene.position.y, dist);
    state.camera.lookAt(0, center.y * scale + vrm.scene.position.y, 0);
    state.camera.near = 0.1;
    state.camera.far = dist * 4 + 20;
    state.camera.updateProjectionMatrix();

    registerClient();
    setStatus(`client-B loaded ${model} (${vrm.meta?.name || 'unnamed'})`);
    return { model, name: vrm.meta?.name || null };
  } catch (err) {
    log(`load failed: ${err.message}`);
    return { error: `load failed: ${err.message}` };
  }
}

async function loadAnimation(url, loop) {
  if (!state.vrm) return { error: 'no model loaded' };
  if (!url) return { error: 'animation url required' };
  try {
    const resolved = /^https?:\/\//.test(url) ? url : normalizeMedia(url);
    const gltf = await state.gltfLoader.loadAsync(resolved);
    const vrmAnimation = gltf.userData.vrmAnimations?.[0] || gltf.userData.vrmAnimation;
    if (!vrmAnimation) return { error: 'no VRMA animation found' };
    const mod = await import('@pixiv/three-vrm-animation');
    const clip = mod.createVRMAnimationClip(vrmAnimation, state.vrm);
    clip.name = `anim:${url}`;
    const mixer = new THREE.AnimationMixer(state.vrm.scene);
    const action = mixer.clipAction(clip);
    action.reset();
    action.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce);
    action.clampWhenFinished = !loop;
    action.play();
    state.mixers.push(mixer);
    state.activeAnimation = { mixer, action, url, loop: !!loop };
    return { url, loop: !!loop };
  } catch (err) {
    return { error: `animation load failed: ${err.message}` };
  }
}

function stopAnimation() {
  if (state.activeAnimation) {
    state.activeAnimation.action.stop();
    state.activeAnimation = null;
  }
}

function stopSpeak() {
  if (state.mouthTimer) cancelAnimationFrame(state.mouthTimer);
  state.mouthTimer = null;
  if (state.audio) {
    state.audio.pause();
    state.audio = null;
  }
  state.vrm?.expressionManager?.setValue('aa', 0);
  state.speaking = false;
}

function speak(audio, mouth) {
  if (!state.vrm) return { error: 'no model loaded' };
  if (!audio) return { error: 'audio url required' };

  stopSpeak();

  const audioUrl = normalizeMedia(audio);
  const mouthUrl = mouth ? normalizeMedia(mouth) : null;
  const audioEl = new Audio(audioUrl);
  audioEl.crossOrigin = 'anonymous';
  state.audio = audioEl;

  const doStart = (timeline) => {
    state.mouthTimeline = timeline || null;
    const startedAt = performance.now();
    audioEl.play().catch((e) => log(`audio play: ${e.message}`));
    const step = () => {
      const t = performance.now() - startedAt;
      if (state.mouthTimeline && state.vrm?.expressionManager) {
        let w = 0;
        for (const [ts, weight] of state.mouthTimeline) {
          if (ts > t) break;
          w = weight;
        }
        state.vrm.expressionManager.setValue('aa', w);
      }
      if (!audioEl.ended && !audioEl.paused) {
        state.mouthTimer = requestAnimationFrame(step);
      } else {
        state.vrm?.expressionManager?.setValue('aa', 0);
        state.speaking = false;
      }
    };
    state.speaking = true;
    state.mouthTimer = requestAnimationFrame(step);
  };

  if (mouthUrl) {
    fetch(mouthUrl)
      .then((r) => r.json())
      .then((data) => doStart(Array.isArray(data) ? data : data?.timeline))
      .catch(() => doStart(null));
  } else {
    doStart(null);
  }
  return { audio };
}

function handleCommand(msg) {
  const cmdName = msg.cmd;
  const cmdId = msg.cmdId;
  let ok = true;
  let result = {};

  switch (cmdName) {
    case 'load':
      loadModel(msg.model).then((r) => {
        if (r.error) sendResponse(cmdId, false, {}, r.error);
        else sendResponse(cmdId, true, r);
      });
      return;
    case 'expression':
      result = setExpression(msg.name, msg.weight);
      ok = !result.error;
      break;
    case 'resetExpression':
      clearExpressions();
      result = {};
      break;
    case 'lookAt':
      result = setLookAt(Number(msg.x ?? 0), Number(msg.y ?? 0));
      ok = !result.error;
      break;
    case 'bone':
      result = setBone(msg.name, msg.rotate);
      ok = !result.error;
      break;
    case 'animation':
      loadAnimation(msg.url, msg.loop).then((r) => {
        if (r.error) sendResponse(cmdId, false, {}, r.error);
        else sendResponse(cmdId, true, r);
      });
      return;
    case 'stopAnimation':
      stopAnimation();
      result = {};
      break;
    case 'speak':
      result = speak(msg.audio, msg.mouth);
      ok = !result.error;
      break;
    case 'stopSpeak':
      stopSpeak();
      result = {};
      break;
    case 'setIdle':
      state.idleOn = !!msg.on;
      result = { on: state.idleOn };
      break;
    case 'inspect':
      result = inspect();
      ok = !result.error;
      break;
    case 'ping':
      result = { pong: true, client: CLIENT_ID };
      break;
    default:
      ok = false;
      result = { error: `unknown command: ${cmdName}` };
  }

  sendResponse(cmdId, ok, result, ok ? null : result.error);
}

function connectWS() {
  const ws = new WebSocket(wsUrl());
  state.socket = ws;
  ws.onopen = () => {
    log('WS connected');
    registerClient();
  };
  ws.onmessage = (ev) => {
    let data;
    try {
      data = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (data.type === 'cmd') {
      handleCommand(data);
    } else if (data.type === 'registered') {
      log(`registered as ${data.id}`);
    } else if (data.type === 'hello') {
      log(`hello ${data.server} proto ${data.protocol}`);
    }
  };
  ws.onclose = () => {
    log('WS closed, reconnecting in 1s');
    setTimeout(connectWS, 1000);
  };
  ws.onerror = () => log('WS error');
}

function idleUpdate(delta) {
  if (!state.idleOn || !state.vrm?.humanoid) return;
  state.idleTime += delta;

  const chest = state.vrm.humanoid.getNormalizedBoneNode('chest');
  if (chest) {
    const breathe = Math.sin(state.idleTime * 1.1) * 0.03;
    chest.rotation.x = breathe;
  }

  if (state.idleTime >= state.nextBlinkAt) {
    state.blinkPhase = 0.25;
    state.nextBlinkAt = state.idleTime + 2.5 + Math.random() * 3;
  }
  if (state.blinkPhase > 0) {
    state.blinkPhase = Math.max(0, state.blinkPhase - delta * 4);
    const w = Math.sin(Math.min(1, state.blinkPhase / 0.25) * Math.PI);
    state.vrm.expressionManager?.setValue('blink', Math.min(1, w * 1.2));
  } else {
    state.vrm.expressionManager?.setValue('blink', 0);
  }
}

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(state.clock.getDelta(), 0.1);
  idleUpdate(delta);
  state.vrm?.update(delta);
  for (const mixer of state.mixers) mixer.update(delta);
  state.renderer.render(state.scene, state.camera);
}

function setStatus(t) {
  const el = document.getElementById('status');
  if (el) el.innerText = t;
}

async function main() {
  state.container = document.getElementById('app') || document.body;
  state.renderer = makeRenderer();
  state.container.appendChild(state.renderer.domElement);
  state.scene = makeScene();
  state.camera = makeCamera(608 / 1080);
  state.clock = new THREE.Clock();

  state.gltfLoader = new GLTFLoader();
  state.gltfLoader.register((parser) => new VRMLoaderPlugin(parser));
  state.gltfLoader.register((parser) => new VRMAnimationLoaderPlugin(parser));

  resize();
  window.addEventListener('resize', resize);

  connectWS();
  animate();

  window.__clientB = { state, loadModel, inspect, setExpression, setLookAt, setBone, clearExpressions, speak };
  setStatus('client-B ready');
  log('ready');
}

main().catch((e) => {
  log(`init failed: ${e.message}`);
  document.body.innerText = `client-B init failed: ${e.message}`;
});
