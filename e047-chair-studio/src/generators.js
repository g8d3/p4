import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

/* ================================================================== */
/*  Random utilities (seeded, reproducible)                            */
/* ================================================================== */

// mulberry32 — tiny, deterministic PRNG seedable by an integer.
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const range = (rng, a, b) => a + rng() * (b - a);
const pick = (rng, arr) => arr[Math.floor(rng() * arr.length)];
const chance = (rng, p) => rng() < p;

// Curated palettes so no random variant breaks the style.
const UPHOLSTERY = ["#d97b4f", "#e0b356", "#6f8f6b", "#7d6b93", "#c0504d", "#4d7ba8", "#b6b6bc", "#8a6f52"];
const FRAME = ["#2a2b31", "#3a3f4a", "#1e2128", "#5a4633", "#4a5078"];
const PAINT = ["#c0392b", "#2c3e50", "#1f6f6b", "#d4a24e", "#5b6c8a", "#a8a8ad", "#7a3b2e", "#3b5b3f"];
const WHEEL = ["#1a1a1e", "#22262c", "#15161a"];
const WALL = ["#e8e0d2", "#d9c7a7", "#b0c4b8", "#cdb0a0", "#e3c28e", "#b8bcc4", "#9aa88f"];
const ROOF = ["#7a5a41", "#5a5f66", "#8a3d2e", "#3f4a3f", "#6b6b6b", "#8f7f5a"];
const GLASS = ["#1c2b3a", "#24303b", "#182430", "#2a3844", "#101820"];

/* ================================================================== */
/*  CHAIR                                                              */
/* ================================================================== */

function buildChair(p) {
  const group = new THREE.Group();

  const cushion = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.cushionColor),
    roughness: p.cushionRoughness,
    metalness: 0.0,
  });
  const frame = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.frameColor),
    roughness: p.frameRoughness,
    metalness: p.frameMetalness,
  });

  const add = (mesh) => {
    mesh.castShadow = mesh.receiveShadow = true;
    group.add(mesh);
    return mesh;
  };

  // seat
  const seat = add(
    new THREE.Mesh(
      new RoundedBoxGeometry(p.seatWidth, p.seatThickness, p.seatDepth, 4, p.seatBevel),
      cushion
    )
  );
  seat.position.y = p.seatHeight - p.seatThickness / 2;

  // backrest (hinged at the back of the seat)
  const hinge = new THREE.Group();
  hinge.position.set(
    0,
    p.seatHeight - p.seatThickness * 0.25,
    -p.seatDepth / 2 + p.backThickness * 0.35
  );
  hinge.rotation.x = -p.backAngle * (Math.PI / 180);
  const back = new THREE.Mesh(
    new RoundedBoxGeometry(p.backWidth, p.backHeight, p.backThickness, 4, 0.02),
    cushion
  );
  back.position.y = p.backHeight / 2;
  back.castShadow = back.receiveShadow = true;
  hinge.add(back);
  group.add(hinge);

  // legs (touch the seat bottom)
  const legHeight = Math.max(0.05, p.seatHeight - p.seatThickness - 0.005);
  const legGeo = new THREE.CylinderGeometry(
    p.legThickness * 0.8,
    p.legThickness,
    legHeight,
    24
  );
  const halfX = p.legSpreadX / 2;
  const halfZ = p.legSpreadZ / 2;
  for (const sx of [-1, 1])
    for (const sz of [-1, 1])
      add(new THREE.Mesh(legGeo, frame)).position.set(sx * halfX, legHeight / 2, sz * halfZ);

  // armrests
  if (p.armrest) {
    const armX = p.seatWidth / 2 - p.armrestInset;
    const startZ = -p.seatDepth * 0.12;
    for (const side of [-1, 1]) {
      const g = new THREE.Group();
      const post = new THREE.Mesh(
        new RoundedBoxGeometry(p.armrestThickness, p.armrestHeight, p.armrestThickness, 2, p.armrestThickness * 0.25),
        frame
      );
      post.position.y = p.armrestHeight / 2;
      post.castShadow = true;
      g.add(post);
      const bar = new THREE.Mesh(
        new RoundedBoxGeometry(p.armrestThickness * 1.5, p.armrestThickness, p.armrestLength, 2, p.armrestThickness * 0.35),
        frame
      );
      bar.position.set(0, p.armrestHeight, p.armrestLength / 2);
      bar.castShadow = true;
      g.add(bar);
      g.position.set(side * armX, p.seatHeight - p.seatThickness * 0.2, startZ);
      group.add(g);
    }
  }

  return group;
}

const chairDefaults = {
  cushionColor: "#d97b4f",
  cushionRoughness: 0.9,
  frameColor: "#2a2b31",
  frameMetalness: 0.45,
  frameRoughness: 0.42,
  seatWidth: 0.48,
  seatDepth: 0.46,
  seatHeight: 0.47,
  seatThickness: 0.09,
  seatBevel: 0.035,
  backHeight: 0.56,
  backWidth: 0.44,
  backThickness: 0.07,
  backAngle: 12,
  legThickness: 0.024,
  legSpreadX: 0.4,
  legSpreadZ: 0.37,
  armrest: true,
  armrestHeight: 0.2,
  armrestThickness: 0.03,
  armrestLength: 0.28,
  armrestInset: 0.04,
};

const chairGUI = [
  { key: "cushionColor", type: "color", label: "Seat Color" },
  { key: "cushionRoughness", type: "number", label: "Seat Rough", min: 0.05, max: 1, step: 0.01 },
  { key: "frameColor", type: "color", label: "Frame Color" },
  { key: "frameMetalness", type: "number", label: "Frame Metal", min: 0, max: 1, step: 0.01 },
  { key: "seatWidth", type: "number", label: "Seat Width", min: 0.3, max: 0.7, step: 0.005 },
  { key: "seatDepth", type: "number", label: "Seat Depth", min: 0.3, max: 0.7, step: 0.005 },
  { key: "seatHeight", type: "number", label: "Seat Height", min: 0.35, max: 0.62, step: 0.005 },
  { key: "backHeight", type: "number", label: "Back Height", min: 0.3, max: 0.95, step: 0.005 },
  { key: "backAngle", type: "number", label: "Back Tilt °", min: -12, max: 45, step: 0.5 },
  { key: "legThickness", type: "number", label: "Leg Thick", min: 0.012, max: 0.06, step: 0.002 },
  { key: "legSpreadX", type: "number", label: "Leg Spread X", min: 0.25, max: 0.62, step: 0.005 },
  { key: "legSpreadZ", type: "number", label: "Leg Spread Z", min: 0.25, max: 0.62, step: 0.005 },
  { key: "armrest", type: "bool", label: "Armrests" },
  { key: "armrestHeight", type: "number", label: "Arm Height", min: 0.05, max: 0.35, step: 0.005 },
];

function sampleChair(rng) {
  return {
    cushionColor: pick(rng, UPHOLSTERY),
    cushionRoughness: range(rng, 0.55, 1),
    frameColor: pick(rng, FRAME),
    frameMetalness: range(rng, 0.1, 0.8),
    frameRoughness: range(rng, 0.2, 0.7),
    seatWidth: range(rng, 0.42, 0.58),
    seatDepth: range(rng, 0.4, 0.55),
    seatHeight: range(rng, 0.4, 0.55),
    seatThickness: range(rng, 0.07, 0.12),
    seatBevel: range(rng, 0.02, 0.05),
    backHeight: range(rng, 0.42, 0.72),
    backWidth: range(rng, 0.36, 0.52),
    backThickness: range(rng, 0.05, 0.1),
    backAngle: range(rng, 5, 25),
    legThickness: range(rng, 0.018, 0.04),
    legSpreadX: range(rng, 0.34, 0.5),
    legSpreadZ: range(rng, 0.32, 0.46),
    armrest: chance(rng, 0.6),
    armrestHeight: range(rng, 0.12, 0.26),
    armrestThickness: range(rng, 0.02, 0.05),
    armrestLength: range(rng, 0.18, 0.36),
    armrestInset: range(rng, 0.03, 0.08),
  };
}

/* ================================================================== */
/*  CAR                                                                */
/* ================================================================== */

function buildCar(p) {
  const group = new THREE.Group();
  const DEG = Math.PI / 180;

  const bodyMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.bodyColor),
    roughness: p.bodyRoughness,
    metalness: p.bodyMetalness,
  });
  const glassMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.glassColor),
    roughness: 0.2,
    metalness: 0.2,
  });
  const wheelMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.wheelColor),
    roughness: 0.85,
    metalness: 0.1,
  });
  const lightMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    emissive: new THREE.Color(p.lightColor),
    emissiveIntensity: 1.6,
    roughness: 0.3,
  });

  const add = (mesh) => {
    mesh.castShadow = mesh.receiveShadow = true;
    group.add(mesh);
    return mesh;
  };

  const wheelRad = p.wheelRadius;
  const groundY = wheelRad; // body rests on wheels
  const bodyCenterY = groundY + p.bodyHeight / 2 + p.clearance;

  // main body
  const body = add(new THREE.Mesh(new RoundedBoxGeometry(p.bodyLength, p.bodyHeight, p.bodyWidth, 4, p.bodyBevel), bodyMat));
  body.position.set(0, bodyCenterY, 0);

  // cabin (offset toward rear, -X = back)
  const cabinLen = p.cabinLength;
  const cabin = add(new THREE.Mesh(new RoundedBoxGeometry(cabinLen, p.cabinHeight, p.bodyWidth * 0.86, 4, 0.05), glassMat));
  cabin.position.set(-p.bodyLength * 0.18, bodyCenterY + p.bodyHeight / 2 + p.cabinHeight / 2, 0);

  // windshield strip highlight
  const windshield = add(new THREE.Mesh(new RoundedBoxGeometry(cabinLen * 0.95, p.cabinHeight * 0.9, p.bodyWidth * 0.84, 2, 0.02), glassMat));
  windshield.position.copy(cabin.position);

  // wheels
  const wheelGeo = new THREE.CylinderGeometry(wheelRad, wheelRad, p.wheelWidth, 24);
  const axleX = p.bodyLength * 0.32;
  const axleZ = p.bodyWidth / 2 - p.wheelWidth * 0.35;
  for (const sx of [-1, 1])
    for (const sz of [-1, 1]) {
      const w = add(new THREE.Mesh(wheelGeo, wheelMat));
      w.rotation.x = 90 * DEG;
      w.position.set(sx * axleX, groundY, sz * axleZ);
    }

  // lights (front = +X)
  const lightGeo = new THREE.BoxGeometry(0.04, p.bodyHeight * 0.28, 0.16);
  for (const sz of [-0.8, 0.8]) {
    const hl = add(new THREE.Mesh(lightGeo, lightMat));
    hl.position.set(p.bodyLength / 2 - 0.01, bodyCenterY + p.bodyHeight * 0.15, sz * p.bodyWidth / 2 * 0.85);
  }

  return group;
}

const carDefaults = {
  bodyColor: "#c0392b",
  bodyMetalness: 0.55,
  bodyRoughness: 0.35,
  glassColor: "#1c2b3a",
  wheelColor: "#1a1a1e",
  lightColor: "#ffd27a",
  bodyLength: 1.9,
  bodyWidth: 0.82,
  bodyHeight: 0.42,
  bodyBevel: 0.06,
  cabinHeight: 0.34,
  cabinLength: 0.85,
  wheelRadius: 0.24,
  wheelWidth: 0.2,
  clearance: 0.02,
};

const carGUI = [
  { key: "bodyColor", type: "color", label: "Paint" },
  { key: "bodyMetalness", type: "number", label: "Metalness", min: 0, max: 1, step: 0.01 },
  { key: "bodyRoughness", type: "number", label: "Roughness", min: 0.05, max: 1, step: 0.01 },
  { key: "glassColor", type: "color", label: "Glass" },
  { key: "bodyLength", type: "number", label: "Length", min: 1.4, max: 2.6, step: 0.01 },
  { key: "bodyWidth", type: "number", label: "Width", min: 0.65, max: 1.1, step: 0.01 },
  { key: "bodyHeight", type: "number", label: "Height", min: 0.3, max: 0.6, step: 0.01 },
  { key: "cabinHeight", type: "number", label: "Cabin H", min: 0.22, max: 0.5, step: 0.01 },
  { key: "cabinLength", type: "number", label: "Cabin L", min: 0.6, max: 1.1, step: 0.01 },
  { key: "wheelRadius", type: "number", label: "Wheel R", min: 0.18, max: 0.3, step: 0.01 },
  { key: "wheelWidth", type: "number", label: "Wheel W", min: 0.14, max: 0.26, step: 0.01 },
];

function sampleCar(rng) {
  return {
    bodyColor: pick(rng, PAINT),
    bodyMetalness: range(rng, 0.3, 0.9),
    bodyRoughness: range(rng, 0.2, 0.5),
    glassColor: pick(rng, GLASS),
    wheelColor: pick(rng, WHEEL),
    lightColor: pick(rng, ["#ffd27a", "#ffffff", "#ffe9b0", "#9fd8ff"]),
    bodyLength: range(rng, 1.7, 2.3),
    bodyWidth: range(rng, 0.72, 1.0),
    bodyHeight: range(rng, 0.34, 0.52),
    bodyBevel: range(rng, 0.05, 0.09),
    cabinHeight: range(rng, 0.26, 0.42),
    cabinLength: range(rng, 0.7, 1.0),
    wheelRadius: range(rng, 0.2, 0.28),
    wheelWidth: range(rng, 0.16, 0.24),
    clearance: range(rng, 0.0, 0.04),
  };
}

/* ================================================================== */
/*  HOUSE                                                              */
/* ================================================================== */

function buildHouse(p) {
  const group = new THREE.Group();

  const wallMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.wallColor),
    roughness: 0.85,
    metalness: 0.05,
  });
  const roofMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.roofColor),
    roughness: 0.7,
    metalness: 0.1,
  });
  const trimMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.doorColor),
    roughness: 0.6,
    metalness: 0.2,
  });
  const glassMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.windowColor),
    roughness: 0.3,
    metalness: 0.3,
  });

  const add = (mesh) => {
    mesh.castShadow = mesh.receiveShadow = true;
    group.add(mesh);
    return mesh;
  };

  // body
  const body = add(new THREE.Mesh(new THREE.BoxGeometry(p.width, p.height, p.depth), wallMat));
  body.position.y = p.height / 2;

  // gable roof via extruded triangle profile (ridge along Z)
  const tri = new THREE.Shape();
  tri.moveTo(-p.width / 2 - p.roofOverhang, 0);
  tri.lineTo(p.width / 2 + p.roofOverhang, 0);
  tri.lineTo(0, p.roofHeight);
  tri.closePath();
  const roofGeo = new THREE.ExtrudeGeometry(tri, { depth: p.depth + p.roofOverhang * 2, bevelEnabled: false });
  const roof = add(new THREE.Mesh(roofGeo, roofMat));
  roof.position.set(0, p.height, -(p.depth + p.roofOverhang * 2) / 2);
  roof.castShadow = roof.receiveShadow = true;

  // door (front, +Z)
  const door = add(new THREE.Mesh(new THREE.BoxGeometry(p.doorWidth, p.doorHeight, 0.06), trimMat));
  door.position.set(0, p.doorHeight / 2, p.depth / 2 + 0.02);

  // windows (front face)
  const winGeo = new THREE.BoxGeometry(p.windowWidth, p.windowHeight, 0.06);
  if (p.windows) {
    for (let i = -1; i <= 1; i += 2) {
      const win = add(new THREE.Mesh(winGeo, glassMat));
      win.position.set(i * p.width * 0.28, p.height * 0.55, p.depth / 2 + 0.02);
    }
    // side windows
    for (const sx of [-1, 1]) {
      const win = add(new THREE.Mesh(new THREE.BoxGeometry(0.06, p.windowHeight, p.windowWidth), glassMat));
      win.position.set(sx * (p.width / 2 + 0.02), p.height * 0.55, 0);
    }
  }

  // chimney
  if (p.chimney) {
    const ch = add(new THREE.Mesh(new THREE.BoxGeometry(0.22, p.chimneyHeight, 0.22), trimMat));
    ch.position.set(p.width * 0.22, p.height + p.roofHeight * 0.7, p.depth * 0.15);
  }

  return group;
}

const houseDefaults = {
  wallColor: "#e8e0d2",
  roofColor: "#7a5a41",
  roofHeight: 0.8,
  doorColor: "#6b4a3a",
  windowColor: "#1c2b3a",
  width: 2.4,
  depth: 2.2,
  height: 2.0,
  roofOverhang: 0.15,
  doorWidth: 0.7,
  doorHeight: 1.2,
  windowWidth: 0.5,
  windowHeight: 0.6,
  windows: true,
  chimney: true,
  chimneyHeight: 0.8,
};

const houseGUI = [
  { key: "wallColor", type: "color", label: "Walls" },
  { key: "roofColor", type: "color", label: "Roof" },
  { key: "doorColor", type: "color", label: "Door" },
  { key: "windowColor", type: "color", label: "Windows" },
  { key: "width", type: "number", label: "Width", min: 1.6, max: 4, step: 0.05 },
  { key: "depth", type: "number", label: "Depth", min: 1.6, max: 4, step: 0.05 },
  { key: "height", type: "number", label: "Height", min: 1.4, max: 3.2, step: 0.05 },
  { key: "roofHeight", type: "number", label: "Roof H", min: 0.4, max: 1.6, step: 0.05 },
  { key: "roofOverhang", type: "number", label: "Overhang", min: 0, max: 0.4, step: 0.01 },
  { key: "windows", type: "bool", label: "Windows" },
  { key: "chimney", type: "bool", label: "Chimney" },
  { key: "chimneyHeight", type: "number", label: "Chimney H", min: 0.4, max: 1.4, step: 0.05 },
];

function sampleHouse(rng) {
  return {
    wallColor: pick(rng, WALL),
    roofColor: pick(rng, ROOF),
    roofHeight: range(rng, 0.6, 1.3),
    doorColor: pick(rng, ["#6b4a3a", "#4a5a4a", "#5a5f66", "#7a3b2e"]),
    windowColor: pick(rng, GLASS),
    width: range(rng, 2.0, 3.4),
    depth: range(rng, 1.8, 3.2),
    height: range(rng, 1.8, 2.8),
    roofOverhang: range(rng, 0.08, 0.28),
    doorWidth: range(rng, 0.6, 0.85),
    doorHeight: range(rng, 1.0, 1.4),
    windowWidth: range(rng, 0.4, 0.65),
    windowHeight: range(rng, 0.5, 0.8),
    windows: chance(rng, 0.85),
    chimney: chance(rng, 0.6),
    chimneyHeight: range(rng, 0.5, 1.1),
  };
}

/* ================================================================== */
/*  Registry                                                           */
/* ================================================================== */

export const GENERATORS = {
  chair: {
    label: "Chair",
    build: buildChair,
    sample: sampleChair,
    defaults: chairDefaults,
    gui: chairGUI,
    camera: [1.45, 1.05, 1.75],
    target: [0, 0.48, 0],
    spacing: 0.85,
    labelY: 0.95,
  },
  car: {
    label: "Car",
    build: buildCar,
    sample: sampleCar,
    defaults: carDefaults,
    gui: carGUI,
    camera: [2.9, 1.3, 3.2],
    target: [0, 0.5, 0],
    spacing: 2.3,
    labelY: 0.75,
  },
  house: {
    label: "House",
    build: buildHouse,
    sample: sampleHouse,
    defaults: houseDefaults,
    gui: houseGUI,
    camera: [3.8, 1.7, 4.2],
    target: [0, 1.4, 0],
    spacing: 3.2,
    labelY: 3.6,
  },
};

export const CATALOG = [
  { name: "Sloyd", url: "https://www.sloyd.ai", what: "Generador procedural paramétrico (muebles, armas, edificios…). El más parecido a nuestro overlay." },
  { name: "Meshy", url: "https://www.meshy.ai", what: "Texto/imagen → modelo 3D." },
  { name: "Tripo3D", url: "https://www.tripo3d.ai", what: "Texto/imagen → 3D." },
  { name: "Stable Fast 3D (Stability AI)", url: "https://stability.ai", what: "Imagen → 3D rápido en el navegador." },
  { name: "Luma Genie", url: "https://lumalabs.ai/genie", what: "Texto/imagen → 3D." },
  { name: "C S M (Common Sense Machines)", url: "https://www.csm.ai", what: "Texto/imagen → 3D." },
  { name: "Poly Haven", url: "https://polyhaven.com", what: "Assets PBR libres CC0: modelos, texturas, HDRIs." },
  { name: "Kenney", url: "https://kenney.nl", what: "Assets de juegos gratuitos." },
  { name: "Three.js Editor", url: "https://threejs.org/editor", what: "Editor de escena glTF (open source)." },
  { name: "Blender", url: "https://www.blender.org", what: "DCC open source; Geometry Nodes = generador procedural visual." },
];
