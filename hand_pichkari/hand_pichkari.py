"""
Hand Pichkari v2.0 — Competitive Holi Edition
================================================
A feature-rich, hand-gesture controlled Holi game with:
  • Lives system & Game Over screen
  • Combo multiplier for rapid hits
  • Progressive difficulty (speed, count, spawn rate escalate)
  • Special targets: Gold (3x points) and Bomb (lose a life!)
  • Power-ups: Big Spray, Slow-Mo, Shield
  • Persistent paint stains on the background
  • Screen-shake on hits
  • Enhanced particle effects & HUD

Requirements:
    pip install opencv-python mediapipe numpy

Controls:
    - Move hand to aim the pichkari
    - Pinch (thumb + index finger) to spray color
    - Press 'q' / ESC to quit
    - Press 'r' to restart
    - Press SPACE on Game Over to play again
"""

import cv2
import mediapipe as mp
import numpy as np
import random
import math
import time

# ─────────────────────────── Configuration ───────────────────────────

WINDOW_NAME = "Hand Pichkari v2 - Competitive Holi"
CAM_WIDTH, CAM_HEIGHT = 1280, 720

# Starting difficulty
BASE_MAX_TARGETS = 5
BASE_SPAWN_INTERVAL = 1.8
BASE_SPEED_RANGE = (1.5, 3.0)
BASE_RADIUS_RANGE = (28, 52)

# Difficulty scaling (per level)
LEVEL_UP_SCORE = 8               # points per level-up
MAX_LEVEL = 15

# Lives
MAX_LIVES = 5

# Pinch / spray
PINCH_THRESHOLD = 42
BASE_SPRAY_RADIUS = 55
SPRAY_PARTICLE_COUNT = 16

# Combo
COMBO_TIMEOUT = 2.0              # seconds to keep combo alive

# Splash
SPLASH_DURATION = 0.6

# Power-up durations (seconds)
POWERUP_DURATION = 6.0
POWERUP_SPAWN_CHANCE = 0.12      # per-target spawn chance

# Stains
MAX_STAINS = 60

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SMALL = cv2.FONT_HERSHEY_PLAIN

# Bright Holi colors (BGR)
HOLI_COLORS = [
    (0, 255, 0),       # green
    (255, 0, 255),     # magenta
    (0, 255, 255),     # yellow
    (255, 0, 128),     # pink-purple
    (0, 165, 255),     # orange
    (255, 255, 0),     # cyan
    (50, 50, 255),     # red
    (180, 50, 255),    # hot pink
    (0, 220, 180),     # teal-ish
]

# Target types
TYPE_NORMAL = "normal"
TYPE_GOLD   = "gold"
TYPE_BOMB   = "bomb"


# ─────────────────────────── Helper Classes ──────────────────────────

class PaintStain:
    """Persistent paint splat on the background."""
    def __init__(self, x, y, color, radius):
        self.x = int(x)
        self.y = int(y)
        self.color = color
        self.radius = radius
        self.alpha = 0.45

    def draw(self, overlay):
        cv2.circle(overlay, (self.x, self.y), self.radius, self.color, -1)


class Target:
    """A floating target — Normal (white), Gold (shiny), or Bomb (red/black)."""

    def __init__(self, w, h, level=1, target_type=TYPE_NORMAL):
        self.type = target_type
        self.hit = False
        self.hit_time = 0.0
        self.hit_color = (255, 255, 255)
        self.escaped = False

        # Appearance by type
        if self.type == TYPE_GOLD:
            self.radius = random.randint(22, 38)
            self.color = (0, 215, 255)           # gold
            self.outline = (0, 180, 255)
            self.points = 3
        elif self.type == TYPE_BOMB:
            self.radius = random.randint(30, 45)
            self.color = (30, 30, 30)            # dark
            self.outline = (0, 0, 200)           # red outline
            self.points = 0
        else:
            min_r = max(18, BASE_RADIUS_RANGE[0] - level)
            max_r = max(25, BASE_RADIUS_RANGE[1] - level)
            self.radius = random.randint(min_r, max_r)
            self.color = (255, 255, 255)
            self.outline = (200, 200, 200)
            self.points = 1

        # Speed scales with level
        speed_lo = BASE_SPEED_RANGE[0] + level * 0.15
        speed_hi = BASE_SPEED_RANGE[1] + level * 0.2
        speed = random.uniform(speed_lo, speed_hi)

        # Wobble (sine-wave movement)
        self.wobble_amp = random.uniform(0.3, 1.5) if random.random() < 0.4 else 0
        self.wobble_freq = random.uniform(0.04, 0.08)
        self.age = 0

        # Spawn from random edge
        side = random.choice(["left", "right", "top", "bottom"])

        if side == "left":
            self.x = float(-self.radius)
            self.y = float(random.randint(self.radius + 70, h - self.radius))
            angle = random.uniform(-math.pi / 4, math.pi / 4)
        elif side == "right":
            self.x = float(w + self.radius)
            self.y = float(random.randint(self.radius + 70, h - self.radius))
            angle = random.uniform(3 * math.pi / 4, 5 * math.pi / 4)
        elif side == "top":
            self.x = float(random.randint(self.radius, w - self.radius))
            self.y = float(-self.radius)
            angle = random.uniform(math.pi / 4, 3 * math.pi / 4)
        else:
            self.x = float(random.randint(self.radius, w - self.radius))
            self.y = float(h + self.radius)
            angle = random.uniform(-3 * math.pi / 4, -math.pi / 4)

        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)

    def update(self):
        self.age += 1
        wobble = self.wobble_amp * math.sin(self.age * self.wobble_freq)
        self.x += self.vx + wobble
        self.y += self.vy

    def is_off_screen(self, w, h):
        margin = self.radius + 80
        return (self.x < -margin or self.x > w + margin or
                self.y < -margin or self.y > h + margin)

    def draw(self, frame, now):
        cx, cy = int(self.x), int(self.y)
        if self.hit:
            elapsed = now - self.hit_time
            alpha = max(0.0, 1.0 - elapsed / SPLASH_DURATION)
            if alpha <= 0:
                return
            overlay = frame.copy()
            cv2.circle(overlay, (cx, cy), self.radius + 12, self.hit_color, -1)
            cv2.addWeighted(overlay, alpha * 0.7, frame, 1 - alpha * 0.7, 0, frame)
        else:
            # Outer glow
            cv2.circle(frame, (cx, cy), self.radius + 5, self.outline, -1)
            cv2.circle(frame, (cx, cy), self.radius, self.color, -1)

            if self.type == TYPE_GOLD:
                # Sparkle effect
                for _ in range(3):
                    sx = cx + random.randint(-self.radius, self.radius)
                    sy = cy + random.randint(-self.radius, self.radius)
                    cv2.circle(frame, (sx, sy), 2, (255, 255, 255), -1)
                # Star label
                cv2.putText(frame, "*", (cx - 6, cy + 6),
                            FONT, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            elif self.type == TYPE_BOMB:
                # Skull / X marker
                cv2.line(frame, (cx - 8, cy - 8), (cx + 8, cy + 8), (0, 0, 255), 3)
                cv2.line(frame, (cx + 8, cy - 8), (cx - 8, cy + 8), (0, 0, 255), 3)
                # Pulsing red ring
                pulse = int(4 * abs(math.sin(self.age * 0.1)))
                cv2.circle(frame, (cx, cy), self.radius + pulse,
                           (0, 0, 255), 2)

    def finished_fading(self, now):
        return self.hit and (now - self.hit_time) > SPLASH_DURATION


class SprayParticle:
    """A single spray / splash particle."""

    def __init__(self, x, y, color, speed_range=(4, 12)):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.life = 1.0
        self.decay = random.uniform(0.025, 0.06)
        self.size = random.randint(3, 8)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.91
        self.vy *= 0.91
        self.life -= self.decay

    def draw(self, frame):
        if self.life <= 0:
            return
        alpha = max(0.0, self.life)
        r = max(1, int(self.size * alpha))
        c = tuple(int(v * alpha) for v in self.color)
        cv2.circle(frame, (int(self.x), int(self.y)), r, c, -1)


class SplashEffect:
    """Radial color-splash burst on target hit."""

    def __init__(self, x, y, color, count=30):
        self.particles = [SprayParticle(x, y, color, (5, 16)) for _ in range(count)]

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, frame):
        for p in self.particles:
            p.draw(frame)

    @property
    def alive(self):
        return len(self.particles) > 0


class FloatingText:
    """Animated floating score / combo text."""

    def __init__(self, x, y, text, color, scale=0.8):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.scale = scale
        self.life = 1.0
        self.vy = -2.5

    def update(self):
        self.y += self.vy
        self.life -= 0.025

    def draw(self, frame):
        if self.life <= 0:
            return
        alpha = max(0.0, self.life)
        c = tuple(int(v * alpha) for v in self.color)
        cv2.putText(frame, self.text, (int(self.x), int(self.y)),
                    FONT, self.scale, c, 2, cv2.LINE_AA)

    @property
    def alive(self):
        return self.life > 0


class PowerUp:
    """Collectible power-up that floats across the screen."""
    TYPES = ["big_spray", "slow_mo", "shield"]
    COLORS = {
        "big_spray": (255, 180, 0),    # blue-ish
        "slow_mo":   (200, 200, 0),    # cyan
        "shield":    (0, 255, 100),    # green
    }
    LABELS = {
        "big_spray": "BIG",
        "slow_mo":   "SLO",
        "shield":    "SHD",
    }

    def __init__(self, w, h):
        self.kind = random.choice(self.TYPES)
        self.radius = 22
        self.color = self.COLORS[self.kind]
        self.label = self.LABELS[self.kind]
        self.collected = False

        # Float from left or right
        if random.random() < 0.5:
            self.x = float(-self.radius)
            self.vx = random.uniform(1.5, 2.5)
        else:
            self.x = float(w + self.radius)
            self.vx = -random.uniform(1.5, 2.5)

        self.y = float(random.randint(80, h - 80))
        self.vy = random.uniform(-0.5, 0.5)
        self.age = 0

    def update(self):
        self.age += 1
        self.x += self.vx
        self.y += self.vy + 0.5 * math.sin(self.age * 0.06)

    def is_off_screen(self, w, h):
        return self.x < -60 or self.x > w + 60

    def draw(self, frame):
        cx, cy = int(self.x), int(self.y)
        # Outer pulsing ring
        pulse = int(4 * abs(math.sin(self.age * 0.08)))
        cv2.circle(frame, (cx, cy), self.radius + pulse + 3, self.color, 2)
        cv2.circle(frame, (cx, cy), self.radius, self.color, -1)
        cv2.circle(frame, (cx, cy), self.radius, (255, 255, 255), 2)
        # Label
        cv2.putText(frame, self.label, (cx - 14, cy + 5),
                    FONT_SMALL, 1.2, (0, 0, 0), 2, cv2.LINE_AA)


# ───────────────────── Drawing Helpers ────────────────────────────────

def draw_pichkari(frame, cx, cy, is_spraying, color, big_mode=False):
    """Draw a pichkari (nozzle) icon at the given position."""
    cx, cy = int(cx), int(cy)
    scale = 1.4 if big_mode else 1.0

    body_w = int(40 * scale)
    body_h = int(18 * scale)
    tip_len = int(22 * scale)

    # Body
    tl = (cx - body_w // 2, cy - body_h // 2)
    br = (cx + body_w // 2, cy + body_h // 2)
    cv2.rectangle(frame, tl, br, color, -1)
    cv2.rectangle(frame, tl, br, (255, 255, 255), 2)

    # Nozzle tip
    tip_pts = np.array([
        [cx + body_w // 2, cy - int(7 * scale)],
        [cx + body_w // 2 + tip_len, cy],
        [cx + body_w // 2, cy + int(7 * scale)],
    ], np.int32)
    cv2.fillPoly(frame, [tip_pts], color)
    cv2.polylines(frame, [tip_pts], True, (255, 255, 255), 2)

    # Handle
    hw = int(12 * scale)
    hl = int(5 * scale)
    cv2.rectangle(frame,
                  (cx - body_w // 2 - hw, cy - hl),
                  (cx - body_w // 2, cy + hl),
                  (180, 180, 180), -1)

    # Spray lines when active
    if is_spraying:
        n_lines = 7 if big_mode else 5
        for _ in range(n_lines):
            length = random.randint(25, int(65 * scale))
            spread = random.randint(int(-25 * scale), int(25 * scale))
            end_x = cx + body_w // 2 + tip_len + length
            end_y = cy + spread
            cv2.line(frame, (cx + body_w // 2 + tip_len, cy),
                     (end_x, end_y), color, random.randint(1, 3))

    # Center dot
    cv2.circle(frame, (cx, cy), 3, (0, 0, 0), -1)
    cv2.circle(frame, (cx, cy), 3, (255, 255, 255), 1)

    # Big mode indicator ring
    if big_mode:
        cv2.circle(frame, (cx, cy), int(50 * scale),
                   (255, 200, 0), 2)


def draw_hud(frame, score, lives, level, combo, current_color, is_spraying,
             w, active_powers, slow_factor):
    """Draw the game HUD bar."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 65), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    # Title
    cv2.putText(frame, "HAND PICHKARI", (12, 42),
                FONT, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

    # Level
    cv2.putText(frame, f"Lv.{level}", (260, 42),
                FONT, 0.75, (0, 200, 255), 2, cv2.LINE_AA)

    # Combo
    if combo > 1:
        combo_text = f"x{combo} COMBO!"
        cv2.putText(frame, combo_text, (340, 42),
                    FONT, 0.75, (0, 255, 255), 2, cv2.LINE_AA)

    # Status
    status = "SPRAYING!" if is_spraying else "Pinch to spray"
    status_color = (0, 255, 0) if is_spraying else (150, 150, 150)
    cv2.putText(frame, status, (w // 2 - 70, 42),
                FONT, 0.6, status_color, 2, cv2.LINE_AA)

    # Active power-up indicators
    px = w // 2 + 100
    for pwr, end_time in active_powers.items():
        remaining = max(0, end_time - time.time())
        if remaining > 0:
            pcolor = PowerUp.COLORS.get(pwr, (200, 200, 200))
            plabel = PowerUp.LABELS.get(pwr, "?")
            cv2.rectangle(frame, (px, 8), (px + 50, 55), pcolor, -1)
            cv2.putText(frame, plabel, (px + 5, 38),
                        FONT_SMALL, 1.2, (0, 0, 0), 2, cv2.LINE_AA)
            # Timer bar
            frac = remaining / POWERUP_DURATION
            bar_h = int(40 * frac)
            cv2.rectangle(frame, (px + 42, 55 - bar_h), (px + 50, 55),
                          (255, 255, 255), -1)
            px += 58

    # Slow-mo indicator
    if slow_factor < 1.0:
        cv2.putText(frame, "SLOW-MO", (w // 2 - 40, 60),
                    FONT_SMALL, 1.0, (200, 200, 0), 1, cv2.LINE_AA)

    # Score
    cv2.putText(frame, f"Score: {score}", (w - 230, 42),
                FONT, 0.9, (0, 255, 255), 2, cv2.LINE_AA)

    # Color swatch
    cv2.rectangle(frame, (w - 60, 10), (w - 10, 55), current_color, -1)
    cv2.rectangle(frame, (w - 60, 10), (w - 10, 55), (255, 255, 255), 2)

    # Lives (hearts)
    for i in range(MAX_LIVES):
        hx = 12 + i * 28
        hy = 58
        if i < lives:
            # Filled heart - draw as small circle pair + triangle
            cv2.circle(frame, (hx + 5, hy), 6, (0, 0, 255), -1)
            cv2.circle(frame, (hx + 15, hy), 6, (0, 0, 255), -1)
            tri = np.array([[hx - 1, hy + 2], [hx + 21, hy + 2],
                            [hx + 10, hy + 14]], np.int32)
            cv2.fillPoly(frame, [tri], (0, 0, 255))
        else:
            cv2.circle(frame, (hx + 5, hy), 6, (80, 80, 80), 1)
            cv2.circle(frame, (hx + 15, hy), 6, (80, 80, 80), 1)


def draw_stains(frame, stains):
    """Draw persistent paint stains on a transparent overlay."""
    if not stains:
        return
    overlay = frame.copy()
    for s in stains:
        s.draw(overlay)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)


def draw_game_over(frame, score, w, h):
    """Draw Game Over screen."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, "GAME OVER", (w // 2 - 200, h // 2 - 40),
                FONT, 2.0, (0, 0, 255), 4, cv2.LINE_AA)

    cv2.putText(frame, f"Final Score: {score}", (w // 2 - 150, h // 2 + 30),
                FONT, 1.2, (0, 255, 255), 3, cv2.LINE_AA)

    cv2.putText(frame, "Press SPACE to play again  |  Q to quit",
                (w // 2 - 260, h // 2 + 90),
                FONT, 0.7, (200, 200, 200), 2, cv2.LINE_AA)

    # Decorative color splatters
    for _ in range(8):
        sx = random.randint(50, w - 50)
        sy = random.randint(50, h - 50)
        sc = random.choice(HOLI_COLORS)
        sr = random.randint(15, 40)
        cv2.circle(frame, (sx, sy), sr, sc, -1)


def draw_start_screen(frame, w, h):
    """Draw the start / title screen."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Colorful title
    title = "HAND PICHKARI"
    cv2.putText(frame, title, (w // 2 - 280, h // 2 - 80),
                FONT, 2.5, (0, 255, 255), 5, cv2.LINE_AA)

    sub = "Competitive Holi Edition"
    cv2.putText(frame, sub, (w // 2 - 180, h // 2 - 30),
                FONT, 0.9, (255, 200, 0), 2, cv2.LINE_AA)

    # Instructions
    instructions = [
        "Show your hand to the camera",
        "Pinch thumb + index finger to SPRAY",
        "Hit white targets for points",
        "Avoid BOMBS (red X markers)!",
        "Catch golden targets for 3x points",
        "",
        "Press SPACE to start  |  Q to quit",
    ]
    for i, line in enumerate(instructions):
        color = (200, 200, 200) if line else (0, 0, 0)
        cv2.putText(frame, line, (w // 2 - 220, h // 2 + 30 + i * 35),
                    FONT, 0.6, color, 1, cv2.LINE_AA)

    # Decorative color circles
    for _ in range(12):
        sx = random.randint(30, w - 30)
        sy = random.randint(30, h - 30)
        sc = random.choice(HOLI_COLORS)
        sr = random.randint(8, 30)
        cv2.circle(frame, (sx, sy), sr, sc, -1)


# ────────────────────── Screen Shake Helper ──────────────────────────

class ScreenShake:
    """Brief screen-shake effect."""

    def __init__(self):
        self.intensity = 0
        self.duration = 0
        self.start = 0

    def trigger(self, intensity=8, duration=0.15):
        self.intensity = intensity
        self.duration = duration
        self.start = time.time()

    def apply(self, frame):
        elapsed = time.time() - self.start
        if elapsed > self.duration or self.intensity == 0:
            return frame
        frac = 1.0 - elapsed / self.duration
        dx = int(random.uniform(-self.intensity, self.intensity) * frac)
        dy = int(random.uniform(-self.intensity, self.intensity) * frac)
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))


# ──────────────────────────── Main Game ──────────────────────────────

def main():
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] Cannot open webcam.")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Camera: {w}x{h}. Show your hand to play!")

    # ── Game state initialization ───────────────────────────────────
    def reset_game():
        return {
            "score": 0,
            "lives": MAX_LIVES,
            "level": 1,
            "combo": 0,
            "last_hit_time": 0.0,
            "targets": [],
            "splashes": [],
            "spray_particles": [],
            "floats": [],
            "powerups": [],
            "stains": [],
            "active_powers": {},
            "last_spawn": time.time(),
            "last_powerup_spawn": time.time(),
            "was_pinching": False,
            "color_idx": 0,
            "game_over": False,
            "started": False,
            "shake": ScreenShake(),
        }

    gs = reset_game()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        now = time.time()

        # ── Hand detection (always active) ──────────────────────────
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        pichkari_x, pichkari_y = -100.0, -100.0
        is_pinching = False

        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            idx_tip = hand.landmark[8]
            thumb_tip = hand.landmark[4]

            ix, iy = int(idx_tip.x * w), int(idx_tip.y * h)
            tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)

            pichkari_x = (ix + tx) / 2.0
            pichkari_y = (iy + ty) / 2.0

            dist = math.hypot(ix - tx, iy - ty)
            is_pinching = dist < PINCH_THRESHOLD

            # Finger dots & line
            cv2.circle(frame, (ix, iy), 5, (100, 255, 100), -1)
            cv2.circle(frame, (tx, ty), 5, (100, 100, 255), -1)
            cv2.line(frame, (ix, iy), (tx, ty), (200, 200, 200), 1)

        # ── Start screen ────────────────────────────────────────────
        if not gs["started"]:
            draw_start_screen(frame, w, h)
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                gs = reset_game()
                gs["started"] = True
            elif key in (ord('q'), 27):
                break
            continue

        # ── Game Over screen ────────────────────────────────────────
        if gs["game_over"]:
            draw_stains(frame, gs["stains"])
            draw_game_over(frame, gs["score"], w, h)
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                gs = reset_game()
                gs["started"] = True
            elif key in (ord('q'), 27):
                break
            continue

        # ── Active power-up checks ──────────────────────────────────
        active = gs["active_powers"]
        big_spray = active.get("big_spray", 0) > now
        slow_mo = active.get("slow_mo", 0) > now
        shield = active.get("shield", 0) > now
        slow_factor = 0.5 if slow_mo else 1.0
        spray_radius = int(BASE_SPRAY_RADIUS * (1.8 if big_spray else 1.0))

        # ── Color switching on new pinch ────────────────────────────
        if is_pinching and not gs["was_pinching"]:
            gs["color_idx"] = (gs["color_idx"] + 1) % len(HOLI_COLORS)
        gs["was_pinching"] = is_pinching
        current_color = HOLI_COLORS[gs["color_idx"]]

        # ── Level computation ───────────────────────────────────────
        gs["level"] = min(MAX_LEVEL, 1 + gs["score"] // LEVEL_UP_SCORE)
        level = gs["level"]

        # ── Spray particles ─────────────────────────────────────────
        if is_pinching and pichkari_x > 0:
            count = int(SPRAY_PARTICLE_COUNT * (1.5 if big_spray else 1.0))
            spread = 12 if big_spray else 8
            for _ in range(count):
                px = pichkari_x + random.randint(-spread, spread)
                py = pichkari_y + random.randint(-spread, spread)
                gs["spray_particles"].append(SprayParticle(px, py, current_color))

        for p in gs["spray_particles"]:
            p.update()
            p.draw(frame)
        gs["spray_particles"] = [p for p in gs["spray_particles"] if p.life > 0]

        # ── Spawn targets ───────────────────────────────────────────
        spawn_interval = max(0.5, BASE_SPAWN_INTERVAL - level * 0.08)
        max_targets = min(12, BASE_MAX_TARGETS + level // 2)

        if (now - gs["last_spawn"] > spawn_interval and
                len(gs["targets"]) < max_targets):
            # Decide target type
            roll = random.random()
            if roll < 0.08 + level * 0.005:
                ttype = TYPE_BOMB
            elif roll < 0.18 + level * 0.005:
                ttype = TYPE_GOLD
            else:
                ttype = TYPE_NORMAL
            gs["targets"].append(Target(w, h, level, ttype))
            gs["last_spawn"] = now

        # ── Spawn power-ups ─────────────────────────────────────────
        if (now - gs["last_powerup_spawn"] > 8.0 and
                len(gs["powerups"]) < 2 and random.random() < POWERUP_SPAWN_CHANCE):
            gs["powerups"].append(PowerUp(w, h))
            gs["last_powerup_spawn"] = now

        # ── Draw stains (behind everything) ─────────────────────────
        draw_stains(frame, gs["stains"])

        # ── Update & check targets ──────────────────────────────────
        escaped_count = 0
        for t in gs["targets"]:
            # Apply slow-mo to target speed
            if slow_mo:
                orig_vx, orig_vy = t.vx, t.vy
                t.vx *= slow_factor
                t.vy *= slow_factor
            t.update()
            if slow_mo:
                t.vx, t.vy = orig_vx, orig_vy

            # Spray collision
            if is_pinching and not t.hit and pichkari_x > 0:
                d = math.hypot(t.x - pichkari_x, t.y - pichkari_y)
                if d < t.radius + spray_radius:
                    if t.type == TYPE_BOMB:
                        # Bomb hit — lose a life (unless shielded)
                        if not shield:
                            gs["lives"] -= 1
                            gs["floats"].append(
                                FloatingText(int(t.x), int(t.y) - 20,
                                             "BOOM! -1 Life", (0, 0, 255), 0.9))
                            gs["shake"].trigger(12, 0.2)
                        else:
                            gs["floats"].append(
                                FloatingText(int(t.x), int(t.y) - 20,
                                             "SHIELDED!", (0, 255, 100), 0.9))
                        t.hit = True
                        t.hit_time = now
                        t.hit_color = (0, 0, 200)
                        gs["splashes"].append(
                            SplashEffect(int(t.x), int(t.y), (0, 0, 200), 25))
                    else:
                        # Normal / Gold hit
                        t.hit = True
                        t.hit_time = now
                        t.hit_color = current_color

                        # Combo logic
                        if now - gs["last_hit_time"] < COMBO_TIMEOUT:
                            gs["combo"] += 1
                        else:
                            gs["combo"] = 1
                        gs["last_hit_time"] = now

                        points = t.points * gs["combo"]
                        gs["score"] += points

                        # Floating text
                        txt = f"+{points}"
                        if gs["combo"] > 1:
                            txt += f" x{gs['combo']}"
                        if t.type == TYPE_GOLD:
                            txt += " GOLD!"
                        gs["floats"].append(
                            FloatingText(int(t.x) - 20, int(t.y) - 20,
                                         txt, current_color, 0.9))

                        # Splash + stain
                        gs["splashes"].append(
                            SplashEffect(int(t.x), int(t.y), current_color, 35))
                        gs["stains"].append(
                            PaintStain(t.x, t.y, current_color,
                                       t.radius + random.randint(5, 20)))
                        if len(gs["stains"]) > MAX_STAINS:
                            gs["stains"].pop(0)

                        gs["shake"].trigger(6, 0.1)

            # Check if target escaped (off-screen without being hit)
            if not t.hit and t.is_off_screen(w, h):
                if t.type == TYPE_NORMAL:
                    t.escaped = True
                    escaped_count += 1

            t.draw(frame, now)

        # Lose lives for escaped normal targets
        gs["lives"] -= escaped_count
        if escaped_count > 0:
            gs["combo"] = 0       # reset combo on miss

        # Remove finished targets
        gs["targets"] = [t for t in gs["targets"]
                         if not t.finished_fading(now)
                         and not t.escaped
                         and not (t.is_off_screen(w, h) and t.type != TYPE_NORMAL)]

        # ── Update power-ups ────────────────────────────────────────
        for pu in gs["powerups"]:
            pu.update()
            # Collect on pinch proximity
            if is_pinching and pichkari_x > 0 and not pu.collected:
                d = math.hypot(pu.x - pichkari_x, pu.y - pichkari_y)
                if d < pu.radius + spray_radius:
                    pu.collected = True
                    gs["active_powers"][pu.kind] = now + POWERUP_DURATION
                    gs["floats"].append(
                        FloatingText(int(pu.x), int(pu.y) - 20,
                                     f"POWER: {pu.label}!", pu.color, 0.9))
                    gs["shake"].trigger(4, 0.08)
            if not pu.collected:
                pu.draw(frame)
        gs["powerups"] = [pu for pu in gs["powerups"]
                          if not pu.collected and not pu.is_off_screen(w, h)]

        # ── Splashes ────────────────────────────────────────────────
        for s in gs["splashes"]:
            s.update()
            s.draw(frame)
        gs["splashes"] = [s for s in gs["splashes"] if s.alive]

        # ── Floating texts ──────────────────────────────────────────
        for ft in gs["floats"]:
            ft.update()
            ft.draw(frame)
        gs["floats"] = [ft for ft in gs["floats"] if ft.alive]

        # ── Pichkari ────────────────────────────────────────────────
        if pichkari_x > 0:
            draw_pichkari(frame, pichkari_x, pichkari_y,
                          is_pinching, current_color, big_spray)

        # ── HUD ─────────────────────────────────────────────────────
        draw_hud(frame, gs["score"], gs["lives"], level,
                 gs["combo"], current_color, is_pinching, w,
                 gs["active_powers"], slow_factor)

        # ── Combo timeout reset ─────────────────────────────────────
        if now - gs["last_hit_time"] > COMBO_TIMEOUT:
            gs["combo"] = 0

        # ── Shield visual indicator ─────────────────────────────────
        if shield and pichkari_x > 0:
            cv2.circle(frame, (int(pichkari_x), int(pichkari_y)),
                       70, (0, 255, 100), 2)

        # ── Screen shake ────────────────────────────────────────────
        frame = gs["shake"].apply(frame)

        # ── Game over check ─────────────────────────────────────────
        if gs["lives"] <= 0:
            gs["game_over"] = True

        # ── Show ────────────────────────────────────────────────────
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord('r'):
            gs = reset_game()
            gs["started"] = True

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print(f"\n[GAME OVER] Final Score: {gs['score']}")


if __name__ == "__main__":
    main()
