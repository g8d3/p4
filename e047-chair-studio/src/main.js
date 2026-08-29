import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import GUI from "lil-gui";
import { GENERATORS, CATALOG, mulberry32 } from "./generators.js";

const app = document.getElementById("app");

/* ------------------------------------------------------------------ */
/*  Renderer / scene                                                   */
/* ------------------------------------------------------------------ */
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x111318, 12, 34);

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.01, 200);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 0.4;
controls.maxDistance = 40;
controls.maxPolarAngle = Math.PI * 0.52;

/* ------------------------------------------------------------------ */
/*  Lighting + ground                                                  */
/* ------------------------------------------------------------------ */
scene.add(new THREE.HemisphereLight(0xffffff, 0x3a3a44, 0.5));
const key = new THREE.DirectionalLight(0xfff2e0, 2.3);
key.position.set(2.6, 3.6, 2.2);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 0.5;
key.shadow.camera.far = 30;
key.shadow.camera.left = -6;
key.shadow.camera.right = 6;
key.shadow.camera.top = 6;
key.shadow.camera.bottom = -4;
key.shadow.bias = -0.0005;
scene.add(key);
const fill = new THREE.DirectionalLight(0x8fa6ff, 0.5);
fill.position.set(-2.4, 1.6, -2.2);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 0.8);
rim.position.set(0, 2.4, -3.6);
scene.add(rim);

const ground = new THREE.Mesh(
  new THREE.CircleGeometry(18, 64),
  new THREE.MeshStandardMaterial({ color: 0x111318, roughness: 1, metalness: 0 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.002;
ground.receiveShadow = true;
scene.add(ground);

const platform = new THREE.Mesh(
  new THREE.CylinderGeometry(0.78, 0.82, 0.05, 64),
  new THREE.MeshStandardMaterial({ color: 0x181b22, roughness: 0.75, metalness: 0.25 })
);
platform.position.y = -0.025;
platform.receiveShadow = platform.castShadow = true;
scene.add(platform);

const ring = new THREE.Mesh(
  new THREE.TorusGeometry(0.84, 0.008, 16, 96),
  new THREE.MeshStandardMaterial({ color: 0xff6b35, roughness: 0.4, metalness: 0.6 })
);
ring.rotation.x = Math.PI / 2;
ring.position.y = 0.001;
scene.add(ring);

/* ------------------------------------------------------------------ */
/*  State                                                              */
/* ------------------------------------------------------------------ */
const sceneSettings = { background: "#111318", autoRotate: false };
const seedState = { value: 42 };
let genre = "chair";
let params = { ...GENERATORS[genre].defaults };
let gui = null;
let mode = "single";        // 'single' | 'batch'
let focused = 0;
let items = [];             // batch items { root, object, ring, label, params, seed }
const batchSeeds = [];

const objectRoot = new THREE.Group();
scene.add(objectRoot);
const batchRoot = new THREE.Group();
scene.add(batchRoot);

function disposeObject(obj, deep = true) {
  obj.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    const mats = child.material ? (Array.isArray(child.material) ? child.material : [child.material]) : [];
    mats.forEach((m) => {
      if (m.map) m.map.dispose();
      m.dispose();
    });
  });
  while (obj.children.length) obj.remove(obj.children[0]);
}

function makeLabel(text) {
  const c = document.createElement("canvas");
  c.width = 160; c.height = 72;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "rgba(14,16,22,0.85)";
  ctx.beginPath();
  ctx.roundRect(4, 4, 152, 64, 12);
  ctx.fill();
  ctx.fillStyle = "#ff6b35";
  ctx.font = "bold 30px ui-sans-serif, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("#" + text, 80, 38);
  const tex = new THREE.CanvasTexture(c);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(0.55, 0.25, 1);
  sprite.renderOrder = 10;
  return sprite;
}

/* ------------------------------------------------------------------ */
/*  Camera                                                             */
/* ------------------------------------------------------------------ */
function applyCamera() {
  const g = GENERATORS[genre];
  camera.position.set(...g.camera);
  controls.target.set(...g.target);
  controls.update();
}

function applyBatchCamera() {
  const g = GENERATORS[genre];
  const cols = 4, rows = 2;
  const halfW = ((cols - 1) / 2) * g.spacing;
  const halfD = ((rows - 1) / 2) * g.spacing;
  const dist = Math.max(halfW, halfD) * 1.9 + 1.5;
  camera.position.set(0, dist * 0.7, dist);
  controls.target.set(0, g.labelY * 0.5, 0);
  controls.update();
}

/* ------------------------------------------------------------------ */
/*  Rebuild                                                            */
/* ------------------------------------------------------------------ */
function rebuildSingle() {
  disposeObject(objectRoot);
  objectRoot.add(GENERATORS[genre].build(params));
  scene.background = new THREE.Color(sceneSettings.background);
  controls.autoRotate = sceneSettings.autoRotate;
}

function rebuildObjectOf(item) {
  const root = item.root;
  // rebuild just the object child (index 0), keep ring + label
  if (item.object) {
    root.remove(item.object);
    disposeObject(item.object);
  }
  item.object = GENERATORS[genre].build(item.params || params);
  item.object.castShadow = item.object.receiveShadow = true;
  root.add(item.object);
}

function onParamsChanged() {
  if (mode === "batch") {
    items[focused].params = { ...params };
    if (items[focused].label) items[focused].label.visible = params; // keep label visible always
    rebuildObjectOf(items[focused]);
  } else {
    rebuildSingle();
  }
  scene.background = new THREE.Color(sceneSettings.background);
  controls.autoRotate = sceneSettings.autoRotate;
}

/* ------------------------------------------------------------------ */
/*  Batch                                                              */
/* ------------------------------------------------------------------ */
const COLS = 4, ROWS = 2, COUNT = COLS * ROWS;

function buildBatch() {
  mode = "batch";
  batchSeeds.length = 0;
  batchSeeds.push(seedState.value);          // keep current as the "hero"
  while (batchSeeds.length < COUNT) batchSeeds.push(Math.floor(Math.random() * 1e6));

  disposeObject(batchRoot);
  items = [];
  const sp = GENERATORS[genre].spacing;

  for (let i = 0; i < COUNT; i++) {
    const s = batchSeeds[i];
    const p = GENERATORS[genre].sample(mulberry32(s));
    const obj = GENERATORS[genre].build(p);

    const root = new THREE.Group();
    root.userData.idx = i;
    root.position.set((i % COLS - (COLS - 1) / 2) * sp, 0, (Math.floor(i / COLS) - (ROWS - 1) / 2) * sp);
    root.add(obj);

    const selectRing = new THREE.Mesh(
      new THREE.TorusGeometry(sp * 0.3, 0.02, 8, 48),
      new THREE.MeshBasicMaterial({ color: 0xff6b35 })
    );
    selectRing.rotation.x = Math.PI / 2;
    selectRing.position.y = 0.03;
    selectRing.visible = false;
    root.add(selectRing);

    const label = makeLabel(String(s));
    label.position.set(0, GENERATORS[genre].labelY, 0);
    root.add(label);

    batchRoot.add(root);
    items.push({ root, object: obj, ring: selectRing, label, params: p, seed: s });
  }

  objectRoot.visible = false;
  batchRoot.visible = true;
  platform.visible = false;
  ring.visible = false;
  applyBatchCamera();

  focused = 0;
  Object.assign(params, items[0].params);
  seedState.value = items[0].seed;
  syncGUI();
  seedDisplay.textContent = String(seedState.value);
  highlight();
}

function selectVariant(i) {
  focused = i;
  seedState.value = items[i].seed;
  Object.assign(params, items[i].params);
  syncGUI();
  seedDisplay.textContent = String(seedState.value);
  highlight();
}

function highlight() {
  items.forEach((it, idx) => (it.ring.visible = idx === focused));
}

function exitBatch() {
  mode = "single";
  batchRoot.visible = false;
  objectRoot.visible = true;
  platform.visible = true;
  ring.visible = true;
  rebuildSingle();
  applyCamera();
  syncButtons();
}

/* ------------------------------------------------------------------ */
/*  GUI                                                                */
/* ------------------------------------------------------------------ */
function buildGUI() {
  if (gui) gui.destroy();
  gui = new GUI({ title: GENERATORS[genre].label + " Tuning" });

  const gen = gui.addFolder("Generation");
  gen.add(seedState, "value").name("Seed").onChange((v) => reseed(Math.floor(v)));
  gen.add({ randomize: () => reseed(Math.floor(Math.random() * 1e6)) }, "randomize").name("🎲 Randomize (new seed)");
  gen.add({ batch: buildBatch }, "batch").name("🎲 Batch ×" + COUNT);
  gen.add({ defaults: resetToDefaults }, "defaults").name("↺ Defaults");
  gen.open();

  const f = gui.addFolder("Parameters");
  for (const spec of GENERATORS[genre].gui) {
    if (spec.type === "color") f.addColor(params, spec.key).name(spec.label).onChange(onParamsChanged);
    else if (spec.type === "bool") f.add(params, spec.key).name(spec.label).onChange(onParamsChanged);
    else f.add(params, spec.key, spec.min, spec.max, spec.step).name(spec.label).onChange(onParamsChanged);
  }
  f.open();

  const s = gui.addFolder("Scene");
  s.addColor(sceneSettings, "background").name("Background").onChange(onParamsChanged);
  s.add(sceneSettings, "autoRotate").name("Auto-rotate").onChange(onParamsChanged);
  s.open();
}

function syncGUI() {
  if (gui) gui.controllers.forEach((c) => c.updateDisplay());
}

function reseed(v) {
  seedState.value = v;
  Object.assign(params, GENERATORS[genre].sample(mulberry32(v)));
  if (mode === "batch") {
    items[focused].seed = v;
    items[focused].params = { ...params };
    // relabel
    if (items[focused].label) {
      items[focused].root.remove(items[focused].label);
      const nl = makeLabel(String(v));
      nl.position.set(0, GENERATORS[genre].labelY, 0);
      items[focused].root.add(nl);
      items[focused].label = nl;
    }
    rebuildObjectOf(items[focused]);
    batchSeeds[focused] = v;
  } else {
    rebuildSingle();
  }
  syncGUI();
  seedDisplay.textContent = String(seedState.value);
}

function resetToDefaults() {
  Object.assign(params, GENERATORS[genre].defaults);
  syncGUI();
  onParamsChanged();
  showToast("Defaults restored");
}

/* ------------------------------------------------------------------ */
/*  Genre / DOM                                                        */
/* ------------------------------------------------------------------ */
const seedDisplay = document.getElementById("seed-display");
document.querySelectorAll(".genre-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    genre = btn.dataset.genre;
    Object.assign(params, GENERATORS[genre].sample(mulberry32(seedState.value)));
    buildGUI();
    mode = "single";
    batchRoot.visible = false;
    objectRoot.visible = true;
    platform.visible = true;
    ring.visible = true;
    rebuildSingle();
    applyCamera();
    seedDisplay.textContent = String(seedState.value);
    document.querySelectorAll(".genre-btn").forEach((b) => b.classList.toggle("active", b.dataset.genre === genre));
    syncButtons();
  });
});

const toast = document.getElementById("toast");
let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2400);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* --- actions --- */
document.getElementById("btn-export").addEventListener("click", () => {
  const exporter = new GLTFExporter();
  exporter.parse(
    objectRoot,
    (result) => {
      downloadBlob(new Blob([result], { type: "model/gltf-binary" }), `${genre}-seed${seedState.value}.glb`);
      downloadBlob(new Blob([JSON.stringify({ genre, seed: seedState.value, params }, null, 2)], { type: "application/json" }), `${genre}-seed${seedState.value}.json`);
      showToast("Exported GLB+JSON ✓");
    },
    (err) => { console.error(err); showToast("Export failed"); },
    { binary: true }
  );
});

document.getElementById("btn-batch").addEventListener("click", () => {
  buildBatch();
  syncButtons();
  showToast("Showing " + COUNT + " variations — click one to focus");
});

document.getElementById("btn-download-batch").addEventListener("click", () => {
  const exporter = new GLTFExporter();
  let done = 0;
  items.forEach((item, idx) => {
    exporter.parse(item.object, (glb) => {
      downloadBlob(new Blob([glb], { type: "model/gltf-binary" }), `${genre}-v${idx}-seed${item.seed}.glb`);
      done++;
      if (done === items.length) showToast("Downloaded " + items.length + " GLBs ✓");
    }, (e) => console.error(e), { binary: true });
  });
  // stagger the downloads a bit so the browser accepts them all
  // (downloadBlob is already async-safe; the loop above triggers them in order)
});

document.getElementById("btn-single").addEventListener("click", exitBatch);

document.getElementById("btn-shot").addEventListener("click", () => {
  renderer.render(scene, camera);
  const a = document.createElement("a");
  a.href = renderer.domElement.toDataURL("image/png");
  a.download = `${genre}-seed${seedState.value}.png`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  showToast("Snapshot saved ✓");
});

function syncButtons() {
  const batch = mode === "batch";
  document.getElementById("btn-download-batch").style.display = batch ? "" : "none";
  document.getElementById("btn-single").style.display = batch ? "" : "none";
}

/* --- catalog modal --- */
const catalogModal = document.getElementById("catalog");
const catalogList = document.getElementById("catalog-list");
CATALOG.forEach((item) => {
  const a = document.createElement("a");
  a.href = item.url; a.target = "_blank"; a.rel = "noopener";
  a.className = "cat-item";
  a.innerHTML = `<b>${item.name}</b><span>${item.what}</span>`;
  catalogList.appendChild(a);
});
document.getElementById("btn-catalog").addEventListener("click", () => catalogModal.classList.add("open"));
document.getElementById("catalog-close").addEventListener("click", () => catalogModal.classList.remove("open"));
catalogModal.addEventListener("click", (e) => { if (e.target === catalogModal) catalogModal.classList.remove("open"); });

/* --- raycast selection --- */
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let downX = 0, downY = 0;
renderer.domElement.addEventListener("pointerdown", (e) => { downX = e.clientX; downY = e.clientY; });
renderer.domElement.addEventListener("pointerup", (e) => {
  if (Math.hypot(e.clientX - downX, e.clientY - downY) > 6) return; // was a drag
  if (mode !== "batch") return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(batchRoot.children, true);
  if (hits.length) {
    let obj = hits[0].object;
    while (obj && obj.userData.idx === undefined) obj = obj.parent;
    if (obj) selectVariant(obj.userData.idx);
  }
});

/* ------------------------------------------------------------------ */
/*  Resize + loop                                                      */
/* ------------------------------------------------------------------ */
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

buildGUI();
rebuildSingle();
applyCamera();
syncButtons();
document.querySelectorAll(".genre-btn").forEach((b) => b.classList.toggle("active", b.dataset.genre === genre));

renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
});
