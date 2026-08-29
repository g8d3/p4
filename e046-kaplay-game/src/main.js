// e046 — Pixel-art platformer built with Kaplay.
//
// The point of this experiment: you write declarative code and the library
// does the heavy lifting (gravity, physics, collisions, camera, scenes,
// sprite-sheet animation). The hero was generated procedurally (see
// bin/gen_hero.py) with ZERO AI credits — you can drop in an AI-generated
// sprite later for the "write a human, get a human" pipeline.

import kaplay from "kaplay";

// Reliable touch detection: presence of touch events OR a small screen decides
// whether we show mobile copy. `k.isTouchscreen()` is not always accurate.
const IS_TOUCH = ("ontouchstart" in window) ||
    (navigator.maxTouchPoints && navigator.maxTouchPoints > 0) ||
    (window.matchMedia && window.matchMedia("(pointer: coarse)").matches);

// Explicit context handle (global:false keeps the global namespace clean).
// This is a side-scrolling platformer, so the world is ALWAYS landscape 480x270
// (16:9). On a portrait/phone screen `stretch`+`letterbox` scale it to fit, with
// letterbox bars top/bottom. Forcing portrait resolution would break the world
// layout, so we never do that.
const GAME_W = 480;
const GAME_H = 270;

const k = kaplay({
    width: GAME_W,
    height: GAME_H,
    canvas: document.querySelector("#game"),
    background: [20, 20, 34],
    global: false,
    maxFPS: 60,
    crisp: true,
    // Scale the game to fill the screen (with letterbox bars), so the game
    // works on phones / tablets and laptops alike.
    stretch: true,
    letterbox: true,
});

// ---------------------------------------------------------------------------
// Assets — the sprite sheet is a single row of 7 frames:
//   [idle, run0, run1, run2, run3, jump, fall]  (each 18x26 px)
// ---------------------------------------------------------------------------
await k.loadSprite("hero", "assets/hero.png", {
    sliceX: 7,
    sliceY: 1,
    anims: {
        idle: { from: 0, to: 0, speed: 8, loop: true },
        run: { from: 1, to: 4, speed: 10, loop: true },
        jump: { from: 5, to: 5, speed: 8, loop: false },
        fall: { from: 6, to: 6, speed: 8, loop: false },
    },
});

// Simple tile texture so the level reads as solid ground (kept bright enough to be visible on the dark background).
await k.loadSprite("tile", (() => {
    const c = document.createElement("canvas");
    c.width = c.height = 32;
    const g = c.getContext("2d");
    // base: warm cobblestone-ish so it stands out
    g.fillStyle = "#4a5d8c";
    g.fillRect(0, 0, 32, 32);
    g.fillStyle = "#5a70a8";
    g.fillRect(0, 0, 32, 6);
    g.fillStyle = "#2b3556";
    g.fillRect(0, 6, 32, 2);
    g.fillStyle = "#3c4a76";
    g.fillRect(0, 14, 32, 2);
    g.fillStyle = "#2b3556";
    g.fillRect(0, 22, 32, 2);
    // subtle vertical seams
    g.fillStyle = "#33406a";
    g.fillRect(15, 0, 2, 32);
    return c;
})());

k.loadSound("coin", "assets/coin.mp3").catch(() => {});
k.loadSound("jump", "assets/jump.mp3").catch(() => {});
k.loadSound("hit", "assets/hit.mp3").catch(() => {});

// ---------------------------------------------------------------------------
// Helpers (Kaplay exposes vec2 on the context handle)
// ---------------------------------------------------------------------------
const v = k.vec2;

// ---------------------------------------------------------------------------
// Scene: "start"
// ---------------------------------------------------------------------------
k.scene("start", () => {
    // Center the menu based on the current game size.
    const cx = GAME_W / 2;
    k.add([
        k.text("e046 — Kaplay", { size: 28, font: "sans-serif" }),
        k.pos(cx, GAME_H * 0.30),
        k.anchor("center"),
        k.color(240, 240, 255),
    ]);
    k.add([
        k.text("ARROWS / WASD or buttons", { size: 18, font: "sans-serif" }),
        k.pos(cx, GAME_H * 0.42 - 18),
        k.anchor("center"),
        k.color(170, 180, 210),
    ]);
    // On touch devices the buttons are shown; on desktop press SPACE.
    const startHint = IS_TOUCH
        ? "Tap or use the buttons to play"
        : "Press SPACE to start";
    k.add([
        k.text(startHint, { size: 22, font: "sans-serif" }),
        k.pos(cx, GAME_H * 0.56),
        k.anchor("center"),
        k.color(255, 205, 120),
        "startLbl",
    ]);
    const goGame = () => k.go("game");
    k.onKeyPress("space", goGame);
    k.onKeyPress("enter", goGame);
    k.onClick(goGame); // touchToMouse converts taps to clicks
});

// ---------------------------------------------------------------------------
// Scene: "game"
// ---------------------------------------------------------------------------
k.scene("game", () => {
    const GRAVITY = 2000;
    const SPEED = 220;
    const JUMP = 560;
    let coins = 0;
    const coinMax = 7;

    k.setGravity(GRAVITY);

    // UI
    const scoreText = k.add([
        k.text(`Coins: 0/${coinMax}`, { size: 24, font: "sans-serif" }),
        k.pos(12, 12),
        k.color(255, 230, 120),
        k.fixed(),
        k.z(100),
    ]);

    // --- Level: ground blocks + platforms (a literal level map, ASCII) ---
    // '@' = hero spawn, '=' = ground, '-' = platform, 'o' = coin, '*' = spike, 'G' = goal
    const levelMap = [
        "................................................................",
        "..........oo......oo...........oo...................oo....",
        ".....--------------...........-----------------............",
        "..................................................................",
        "...................................................oo.........",
        "..............................-.................-...........",
        ".............oo..................oo..............................",
        "....====......===......=====........=====.......====..==......",
        "===============@===============......................==......===",
    ];

    const charWidth = 24;
    const charHeight = 24;

    const hero = k.add([
        k.sprite("hero", { anim: "idle" }),
        k.pos(0, 0),
        k.area(),
        k.body({ drag: 0 }),
        k.anchor("center"),
        k.scale(2),
        "hero",
    ]);

    // Place the hero resting on the solid ground of the bottom (last) row, at
    // the '@' marker in the map so it does NOT spawn inside a fence of blocks.
    // The '@' column is a gap in the ground, so the hero is free to move left
    // and right without being stuck inside solid tiles.
    const groundRow = levelMap.length - 1;
    const heroHalfH = (26 * 2) / 2; // 26
    const atIdx = levelMap[groundRow].indexOf("@");
    const spawnX = (atIdx >= 0 ? atIdx : 3) * charWidth + charWidth / 2;
    const spawn = v(spawnX, groundRow * charHeight - heroHalfH);
    for (let row = 0; row < levelMap.length; row++) {
        for (let col = 0; col < levelMap[row].length; col++) {
            const c = levelMap[row][col];
            if (c === " ") continue;
            const x = col * charWidth + charWidth / 2;
            const y = row * charHeight + charHeight / 2;
            if (c === "=") {
                k.add([
                    k.sprite("tile"),
                    k.pos(x, y),
                    k.area(),
                    k.body({ isStatic: true }),
                    k.anchor("center"),
                    "ground",
                ]);
            } else if (c === "-") {
                k.add([
                    k.sprite("tile"),
                    k.pos(x, y),
                    k.area(),
                    k.body({ isStatic: true }),
                    k.anchor("center"),
                    k.scale(0.55, 0.3),
                    "ground",
                ]);
            } else if (c === "o") {
                k.add([
                    k.circle(8),
                    k.pos(x, y),
                    k.area(),
                    k.color(255, 220, 90),
                    k.anchor("center"),
                    "coin",
                ]);
            } else if (c === "*") {
                k.add([
                    k.rect(charWidth * 0.5, charHeight * 0.6),
                    k.pos(x, y + charHeight * 0.2),
                    k.color(220, 60, 60),
                    k.anchor("center"),
                    k.area(),
                    k.body({ isStatic: true }),
                    "spike",
                ]);
            }
        }
    }

    // --- Goal flag (a single, discrete object at the end of the world) ---
    const goalX = levelMap[0].length * charWidth - charWidth;
    k.add([
        k.rect(12, 70),
        k.pos(goalX, groundRow * charHeight - 70 + 35),
        k.color(120, 240, 160),
        k.anchor("center"),
        k.area(),
        "goal",
    ]);

    hero.pos = spawn;

    // --- Diagnostic hook (debugging only; harmless in production) ---
    window.__e046 = { hero, input: null, isGrounded: () => hero.isGrounded(), cam: () => k.getCamPos() };

    // --- Input state shared by keyboard and touch buttons ---
    const input = { left: false, right: false };
    window.__e046.input = input;

    const bindKeys = () => {
        const left = () => (input.left = true);
        const leftUp = () => (input.left = false);
        const right = () => (input.right = true);
        const rightUp = () => (input.right = false);
        k.onKeyDown("left", left);
        k.onKeyDown("a", left);
        k.onKeyRelease("left", leftUp);
        k.onKeyRelease("a", leftUp);
        k.onKeyDown("right", right);
        k.onKeyDown("d", right);
        k.onKeyRelease("right", rightUp);
        k.onKeyRelease("d", rightUp);
        const jump = () => hero.jump(JUMP);
        k.onKeyPress("space", jump);
        k.onKeyPress("up", jump);
        k.onKeyPress("w", jump);
    };

    // --- Touch controls (mobile) ---
    // We track touches at the DOCUMENT level (not per-button), so the input
    // NEVER sticks: if the finger slides off a button mid-press, we still see
    // the touchend/move on the document and clear the flag. Each active touch
    // is tagged with which logical control it started on.
    const bindTouch = () => {
        const controls = { btnLeft: "left", btnRight: "right", btnJump: "jump" };
        const active = new Map(); // touchId -> controlKey

        const onStart = (e) => {
            for (const t of e.changedTouches) {
                const el = document.elementFromPoint(t.clientX, t.clientY);
                const btn = el && el.closest ? el.closest(".btn") : null;
                const key = btn && controls[btn.id];
                if (!key) continue;
                active.set(t.identifier, key);
                if (key === "left") input.left = true;
                else if (key === "right") input.right = true;
                else if (key === "jump") hero.jump(JUMP);
            }
        };
        const onEnd = (e) => {
            for (const t of e.changedTouches) {
                const key = active.get(t.identifier);
                if (!key) continue;
                if (key === "left") input.left = false;
                else if (key === "right") input.right = false;
                active.delete(t.identifier);
            }
        };

        document.addEventListener("touchstart", onStart, { passive: false });
        document.addEventListener("touchend", onEnd, { passive: false });
        document.addEventListener("touchcancel", onEnd, { passive: false });
    };

    bindKeys();
    bindTouch();

    // Apply the shared input every frame (works for keyboard + touch).
    // With a body() we set vel.x DIRECTLY each frame so the hero's drag (default
    // decays velocity) can't fight the input and stop the hero from moving.
    k.onUpdate(() => {
        let vx = 0;
        if (input.left) vx -= SPEED;
        if (input.right) vx += SPEED;
        hero.vel.x = vx;
    });

    // --- Camera follows hero ---
    // Follow the hero horizontally; vertically anchor to a fixed height so the
    // ground stays in view and the camera does not fly up when the hero jumps
    // or drop when it falls. We place the ground near the bottom of the view.
    const groundCamY = groundRow * charHeight - GAME_H * 0.45;
    k.onUpdate(() => {
        k.setCamPos(hero.pos.x, groundCamY);
    });

    // --- Animation state machine (only switch anim when it changes, so we
    // don't re-trigger play() every frame — cheaper and it keeps the run cycle
    // advancing instead of resetting) ---
    hero.onUpdate(() => {
        const onGround = hero.isGrounded();
        let target;
        if (!onGround) {
            target = hero.vel.y > 0 ? "fall" : "jump";
        } else {
            const moving = input.left || input.right || Math.abs(hero.vel.x) > 1;
            target = moving ? "run" : "idle";
        }
        if (hero.getCurAnim()?.name !== target) hero.play(target);
    });

    // --- Pickups ---
    hero.onCollide("coin", (c) => {
        k.destroy(c);
        coins++;
        scoreText.text = `Coins: ${coins}/${coinMax}`;
        k.play("coin", { volume: 0.5 });
    });

    // --- Hazards ---
    hero.onCollide("spike", () => {
        k.play("hit");
        // Simple respawn: back to spawn, reset coins
        hero.pos = spawn;
        coins = 0;
        scoreText.text = `Coins: 0/${coinMax}`;
    });

    // --- Goal ---
    hero.onCollide("goal", () => {
        k.go("win", { coins, coinMax });
    });

    // --- Respawn if fall into pit ---
    hero.onUpdate(() => {
        if (hero.pos.y > 400) {
            hero.pos = spawn;
            coins = 0;
            scoreText.text = `Coins: 0/${coinMax}`;
        }
    });
});

// ---------------------------------------------------------------------------
// Scene: "win"
// ---------------------------------------------------------------------------
k.scene("win", ({ coins, coinMax }) => {
    const all = coins >= coinMax;
    const cx = GAME_W / 2;
    k.add([
        k.text(all ? "PERFECT!" : `You got ${coins}/${coinMax} coins`, {
            size: 26,
            font: "sans-serif",
        }),
        k.pos(cx, GAME_H * 0.40),
        k.anchor("center"),
        k.color(160, 255, 180),
    ]);
    const hint = IS_TOUCH
        ? "Tap to play again"
        : "Press SPACE to play again";
    k.add([
        k.text(hint, { size: 20, font: "sans-serif" }),
        k.pos(cx, GAME_H * 0.56),
        k.anchor("center"),
        k.color(205, 215, 235),
    ]);
    const again = () => k.go("game");
    k.onKeyPress("space", again);
    k.onKeyPress("enter", again);
    k.onClick(again); // touchToMouse converts taps to clicks
});

// ---------------------------------------------------------------------------
// Launch
// ---------------------------------------------------------------------------
k.go("start");
