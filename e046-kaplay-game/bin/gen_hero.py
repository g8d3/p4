#!/usr/bin/env python3
"""Generate a pixel-art hero sprite sheet for the Kaplay platformer.

Procedurally draws a small humanoid hero with a few animation frames:
  idle, run (walk cycle), jump, fall.

Output: assets/hero.png (a row of frames).
No AI credits required — pure PIL.
"""
from PIL import Image, ImageDraw

# ---- Palette (pixel art) ----
TRANSPARENT = (0, 0, 0, 0)
OUTLINE     = (26, 26, 46, 255)
SKIN        = (255, 205, 158, 255)
SKIN_SHADE  = (231, 172, 128, 255)
HAIR        = (92, 64, 51, 255)
SHIRT       = (225, 84, 84, 255)      # red shirt
SHIRT_DARK  = (187, 55, 55, 255)
PANTS       = (61, 90, 128, 255)      # blue jeans
PANTS_DARK  = (42, 62, 92, 255)
SHOE        = (92, 64, 51, 255)       # brown shoes
EYE         = (30, 30, 30, 255)

# Frame size (logical pixels). The game will scale this up.
FW, FH = 18, 26


class Hero:
    def __init__(self, w=FW, h=FH):
        self.img = Image.new("RGBA", (w, h), TRANSPARENT)
        self.d = ImageDraw.Draw(self.img)

    def px(self, x, y, c):
        if 0 <= x < FW and 0 <= y < FH:
            self.d.point((x, y), c)

    def rect(self, x0, y0, x1, y1, c):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                self.px(x, y, c)

    # ---- parts ----
    def head(self):
        # hair
        self.rect(5, 1, 12, 3, HAIR)
        self.rect(4, 3, 5, 5, HAIR)
        self.rect(12, 3, 13, 5, HAIR)
        # face
        self.rect(5, 3, 12, 9, SKIN)
        self.rect(6, 4, 6, 4, SKIN_SHADE)
        # eyes
        self.px(6, 6, EYE)
        self.px(7, 6, EYE)
        self.px(10, 6, EYE)
        self.px(11, 6, EYE)

    def torso(self, lean=0):
        x0 = 4 + lean
        self.rect(x0, 9, x0 + 9, 15, SHIRT)
        self.rect(x0, 9, x0 + 9, 9, SHIRT_DARK)  # collar shadow
        # belt
        self.rect(x0, 15, x0 + 9, 15, PANTS_DARK)

    def leg_swing(self, phase):
        """phase: angle-ish 0..3 for run cycle, or 'idle', 'jump', 'fall'."""
        xb = 4
        if phase == "idle":
            self.rect(xb + 1, 16, xb + 3, 22, PANTS)
            self.rect(xb + 6, 16, xb + 8, 22, PANTS)
            self.rect(xb + 1, 22, xb + 4, 23, SHOE)
            self.rect(xb + 6, 22, xb + 9, 23, SHOE)
        elif phase == "jump":
            # knees up
            self.rect(xb + 2, 16, xb + 4, 18, PANTS)
            self.rect(xb + 5, 16, xb + 7, 18, PANTS)
            self.rect(xb + 2, 18, xb + 5, 20, PANTS_DARK)
            self.rect(xb + 5, 18, xb + 8, 20, PANTS_DARK)
        elif phase == "fall":
            self.rect(xb + 0, 16, xb + 3, 20, PANTS)
            self.rect(xb + 6, 16, xb + 9, 20, PANTS)
            self.rect(xb + 0, 20, xb + 4, 21, SHOE)
            self.rect(xb + 5, 20, xb + 9, 21, SHOE)
        else:
            n = int(phase)
            # walk cycle: legs scissor
            if n == 0:
                self.rect(xb + 1, 16, xb + 3, 22, PANTS)
                self.rect(xb + 6, 16, xb + 8, 22, PANTS)
                self.rect(xb + 1, 22, xb + 4, 23, SHOE)
                self.rect(xb + 6, 22, xb + 9, 23, SHOE)
            elif n == 1:
                self.rect(xb + 2, 16, xb + 4, 22, PANTS)
                self.rect(xb + 6, 16, xb + 7, 21, PANTS)
                self.rect(xb + 2, 22, xb + 6, 23, SHOE)  # front, stride
                self.rect(xb + 6, 21, xb + 8, 22, SHOE)
            elif n == 2:
                self.rect(xb + 1, 16, xb + 3, 22, PANTS)
                self.rect(xb + 6, 16, xb + 8, 22, PANTS)
                self.rect(xb + 1, 22, xb + 4, 23, SHOE)
                self.rect(xb + 6, 22, xb + 9, 23, SHOE)
            elif n == 3:
                self.rect(xb + 1, 16, xb + 2, 21, PANTS)
                self.rect(xb + 6, 16, xb + 8, 22, PANTS)
                self.rect(xb + 0, 21, xb + 3, 22, SHOE)
                self.rect(xb + 6, 22, xb + 9, 23, SHOE)

    def arm(self, side, phase):
        xb = 4
        if phase == "idle" or phase == "fall":
            col = SC = SHIRT
            if side == "L":
                self.rect(xb - 1, 10, xb - 1, 13, col)
            else:
                self.rect(xb + 10, 10, xb + 10, 13, col)
        elif phase == "jump":
            if side == "L":
                self.rect(xb - 1, 9, xb - 1, 12, SHIRT)
            else:
                self.rect(xb + 10, 9, xb + 10, 12, SHIRT)
        else:
            n = int(phase)
            if side == "L":
                y = 10 + (n % 2)
                self.rect(xb - 1, y, xb - 1, y + 3, SHIRT)
            else:
                y = 10 + ((n + 1) % 2)
                self.rect(xb + 10, y, xb + 10, y + 3, SHIRT)


def render_frame(pose):
    h = Hero()
    lean = 0
    if isinstance(pose, int) and pose in (1,):
        lean = 1
    h.torso(lean)
    h.leg_swing(pose)
    h.arm("L", pose)
    h.arm("R", pose)
    h.head()
    return h.img


def main():
    # Frames order (1 row): idle, run0, run1, run2, run3, jump, fall
    poses = ["idle", 0, 1, 2, 3, "jump", "fall"]
    frames = [render_frame(p) for p in poses]
    sheet = Image.new("RGBA", (FW * len(frames), FH), TRANSPARENT)
    for i, f in enumerate(frames):
        sheet.paste(f, (i * FW, 0))

    out = "assets/hero.png"
    sheet.save(out)
    print(f"OK -> {out}  ({len(frames)} frames, {FW}x{FH} each, sheet {sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
