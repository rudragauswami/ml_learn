"""
Hand Pichkari v4.0 — Competitive Holi Edition (Final)
======================================================
Features:
  • Threaded MediaPipe hand detection with frame-skip
  • Pygame.mixer audio (synthesized WAV tones) + background music
  • Difficulty selection (Easy / Medium / Hard) + Time Trial mode
  • Lives system, combo multiplier, progressive levels
  • Special targets: Normal, Gold (3x), Frozen (2-hit), Bomb
  • Power-ups: Big Spray, Slow-Mo, Shield
  • Particle gravity (dripping color), persistent paint stains
  • Screen shake, combo flash, rainbow trail, dynamic border
  • Smooth hand tracking (EMA filter), FPS counter, accuracy %
  • High score persistence, external settings.json config
  • Professional Python logging

Requirements:
    pip install opencv-python mediapipe numpy
    pip install pygame          # optional — for better audio

Controls:
    - Move hand to aim the pichkari
    - Pinch (thumb + index finger) to spray color
    - Press 'q' / ESC to quit
    - Press 'r' to restart mid-game
    - Press SPACE on title / game-over to start / replay
    - Press 1/2/3 on title screen to pick difficulty
    - Press 'T' on title screen to toggle Time Trial mode
"""

import cv2
import mediapipe as mp
import numpy as np
import random
import math
import time
import os
import json
import threading
import logging
import struct
import wave
import io

# ─────────────────────── Logging Setup ───────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("HandPichkari")

# ─────────────────── Settings Loader ─────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")


def load_settings():
    """Load external settings.json; return dict or empty dict on failure."""
    try:
        with open(SETTINGS_FILE, "r") as f:
            cfg = json.load(f)
            log.info("Loaded settings from %s", SETTINGS_FILE)
            return cfg
    except FileNotFoundError:
        log.warning("settings.json not found — using defaults")
        return {}
    except json.JSONDecodeError as e:
        log.warning("settings.json parse error: %s — using defaults", e)
        return {}


_CFG = load_settings()


def cfg(section, key, default):
    """Read a config value with fallback to default."""
    return _CFG.get(section, {}).get(key, default)

# ─────────────────── Audio System (pygame) ───────────────────────────

_AUDIO_OK = False

try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.mixer.init()
    _AUDIO_OK = True
    log.info("pygame.mixer initialized — audio enabled")
except Exception:
    log.warning("pygame not available — falling back to winsound / silent")


def _generate_tone_wav(freq, duration_ms, volume=0.5, fade_out=True):
    """Generate a WAV tone in memory and return a pygame Sound (or None)."""
    if not _AUDIO_OK:
        return None
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            t = i / sample_rate
            fade = 1.0
            if fade_out:
                fade = max(0.0, 1.0 - i / n_samples)
            val = int(volume * 32767 * fade * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack("<h", max(-32768, min(32767, val))))
    buf.seek(0)
    return pygame.mixer.Sound(buf)


# Pre-generate sound effects
_SND = {}
if _AUDIO_OK:
    _SND["hit"]     = _generate_tone_wav(1200, 80, 0.4)
    _SND["gold"]    = _generate_tone_wav(1800, 120, 0.5)
    _SND["bomb"]    = _generate_tone_wav(250, 250, 0.6)
    _SND["miss"]    = _generate_tone_wav(350, 150, 0.3)
    _SND["powerup"] = _generate_tone_wav(1600, 100, 0.4)
    _SND["levelup"] = _generate_tone_wav(1400, 150, 0.5)
    _SND["gameover"]= _generate_tone_wav(300, 400, 0.5)
    log.info("Sound effects generated")


def _play(name):
    snd = _SND.get(name)
    if snd:
        snd.play()


# Background music — a simple looping low-volume festive tone
_BG_MUSIC = None
if _AUDIO_OK:
    try:
        _BG_MUSIC = _generate_tone_wav(440, 3000, 0.08, fade_out=False)
        log.info("Background music tone generated")
    except Exception:
        pass

# ── Winsound fallback (if no pygame) ────────────────────────────────
_USE_WINSOUND = False
if not _AUDIO_OK:
    try:
        import winsound
        _USE_WINSOUND = True

        def _beep(freq, dur):
            threading.Thread(target=winsound.Beep, args=(freq, dur), daemon=True).start()
    except ImportError:
        pass


def sfx_hit():
    if _AUDIO_OK: _play("hit")
    elif _USE_WINSOUND: _beep(1200, 60)

def sfx_gold():
    if _AUDIO_OK: _play("gold")
    elif _USE_WINSOUND: _beep(1800, 100)

def sfx_bomb():
    if _AUDIO_OK: _play("bomb")
    elif _USE_WINSOUND: _beep(300, 200)

def sfx_miss():
    if _AUDIO_OK: _play("miss")
    elif _USE_WINSOUND: _beep(400, 120)

def sfx_powerup():
    if _AUDIO_OK: _play("powerup")
    elif _USE_WINSOUND: _beep(1500, 80)

def sfx_levelup():
    if _AUDIO_OK: _play("levelup")
    elif _USE_WINSOUND: _beep(1400, 80)

def sfx_gameover():
    if _AUDIO_OK: _play("gameover")
    elif _USE_WINSOUND: _beep(400, 200)


def start_bg_music():
    """Start looping background music (low volume)."""
    if _BG_MUSIC:
        _BG_MUSIC.play(loops=-1)
        log.info("Background music started")

def stop_bg_music():
    if _BG_MUSIC:
        _BG_MUSIC.stop()


# ─────────────────────────── Configuration ───────────────────────────

WINDOW_NAME = "Hand Pichkari v4 - Competitive Holi"
CAM_WIDTH = cfg("camera", "width", 1280)
CAM_HEIGHT = cfg("camera", "height", 720)
CAM_DEVICE = cfg("camera", "device_index", 0)

# Save file for high scores (next to the script)
SAVE_FILE = os.path.join(SCRIPT_DIR, "highscores.json")

# ── Difficulty presets (loaded from settings.json or defaults) ──────
def _build_difficulty():
    """Build difficulty dict — merge settings.json overrides with defaults."""
    defaults = {
        "Easy": {
            "base_max_targets": 4, "base_spawn_interval": 2.2,
            "base_speed": (1.2, 2.5), "base_radius": (32, 58),
            "level_up_score": 10, "max_lives": 7, "bomb_chance": 0.05,
            "label_color": (0, 255, 0),
        },
        "Medium": {
            "base_max_targets": 5, "base_spawn_interval": 1.8,
            "base_speed": (1.5, 3.0), "base_radius": (28, 52),
            "level_up_score": 8, "max_lives": 5, "bomb_chance": 0.08,
            "label_color": (0, 200, 255),
        },
        "Hard": {
            "base_max_targets": 7, "base_spawn_interval": 1.3,
            "base_speed": (2.0, 4.0), "base_radius": (20, 42),
            "level_up_score": 6, "max_lives": 3, "bomb_chance": 0.12,
            "label_color": (0, 0, 255),
        },
    }
    diff_cfg = _CFG.get("difficulty", {})
    for name, defs in defaults.items():
        overrides = diff_cfg.get(name, {})
        if overrides:
            defs["base_max_targets"] = overrides.get("base_max_targets", defs["base_max_targets"])
            defs["base_spawn_interval"] = overrides.get("base_spawn_interval", defs["base_spawn_interval"])
            defs["base_speed"] = (overrides.get("base_speed_min", defs["base_speed"][0]),
                                  overrides.get("base_speed_max", defs["base_speed"][1]))
            defs["base_radius"] = (overrides.get("base_radius_min", defs["base_radius"][0]),
                                   overrides.get("base_radius_max", defs["base_radius"][1]))
            defs["level_up_score"] = overrides.get("level_up_score", defs["level_up_score"])
            defs["max_lives"] = overrides.get("max_lives", defs["max_lives"])
            defs["bomb_chance"] = overrides.get("bomb_chance", defs["bomb_chance"])
    return defaults


DIFFICULTY = _build_difficulty()
MAX_LEVEL = cfg("gameplay", "max_level", 15)

# Pinch / spray
PINCH_THRESHOLD = cfg("hand_tracking", "pinch_threshold", 42)
BASE_SPRAY_RADIUS = cfg("spray", "base_radius", 55)
SPRAY_PARTICLE_COUNT = cfg("spray", "particle_count", 16)
PARTICLE_GRAVITY = cfg("spray", "particle_gravity", 0.15)

# Combo
COMBO_TIMEOUT = cfg("gameplay", "combo_timeout", 2.0)

# Splash
SPLASH_DURATION = cfg("gameplay", "splash_duration", 0.6)

# Power-ups
POWERUP_DURATION = cfg("powerup", "duration", 6.0)
POWERUP_SPAWN_CHANCE = cfg("powerup", "spawn_chance", 0.12)

# Stains
MAX_STAINS = cfg("gameplay", "max_stains", 60)

# Trail
TRAIL_LENGTH = cfg("gameplay", "trail_length", 14)

# Time trial
TIME_TRIAL_SECONDS = cfg("gameplay", "time_trial_seconds", 60)

# Smoothing
SMOOTH_FACTOR = cfg("hand_tracking", "smooth_factor", 0.45)

# Frame skip for threaded tracker
FRAME_SKIP = cfg("hand_tracking", "frame_skip", 2)

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SMALL = cv2.FONT_HERSHEY_PLAIN

# Bright Holi colors (BGR)
_color_cfg = _CFG.get("colors", {}).get("holi_bgr", None)
if _color_cfg:
    HOLI_COLORS = [tuple(c) for c in _color_cfg]
else:
    HOLI_COLORS = [
        (0, 255, 0), (255, 0, 255), (0, 255, 255), (255, 0, 128),
        (0, 165, 255), (255, 255, 0), (50, 50, 255), (180, 50, 255),
        (0, 220, 180),
    ]

# Target types
TYPE_NORMAL = "normal"
TYPE_GOLD   = "gold"
TYPE_BOMB   = "bomb"
TYPE_FROZEN = "frozen"


# ────────────────── High Score Persistence ───────────────────────────

def load_high_scores():
    """Load high scores from JSON file."""
    try:
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"Easy": 0, "Medium": 0, "Hard": 0,
                "Easy_tt": 0, "Medium_tt": 0, "Hard_tt": 0}


def save_high_scores(scores):
    """Save high scores to JSON file."""
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(scores, f, indent=2)
        log.debug("High scores saved")
    except OSError as e:
        log.warning("Failed to save high scores: %s", e)


# ─────────────────────────── Helper Classes ──────────────────────────

class PaintStain:
    """Persistent paint splat on the background."""
    def __init__(self, x, y, color, radius):
        self.x = int(x)
        self.y = int(y)
        self.color = color
        self.radius = radius

    def draw(self, overlay):
        cv2.circle(overlay, (self.x, self.y), self.radius, self.color, -1)


class Target:
    """A floating target — Normal, Gold, Frozen, or Bomb."""

    def __init__(self, w, h, level, target_type, diff):
        self.type = target_type
        self.hit = False
        self.hit_time = 0.0
        self.hit_color = (255, 255, 255)
        self.escaped = False
        self.hp = 1                   # hits needed

        base_radius = diff["base_radius"]
        base_speed = diff["base_speed"]

        if self.type == TYPE_GOLD:
            self.radius = random.randint(22, 38)
            self.color = (0, 215, 255)
            self.outline = (0, 180, 255)
            self.points = 3
        elif self.type == TYPE_BOMB:
            self.radius = random.randint(30, 45)
            self.color = (30, 30, 30)
            self.outline = (0, 0, 200)
            self.points = 0
        elif self.type == TYPE_FROZEN:
            self.radius = random.randint(28, 44)
            self.color = (230, 200, 160)         # ice-blue
            self.outline = (255, 220, 180)
            self.points = 2
            self.hp = 2                            # needs two hits
            self.cracked = False
        else:
            min_r = max(18, base_radius[0] - level)
            max_r = max(25, base_radius[1] - level)
            self.radius = random.randint(min_r, max_r)
            self.color = (255, 255, 255)
            self.outline = (200, 200, 200)
            self.points = 1

        speed_lo = base_speed[0] + level * 0.15
        speed_hi = base_speed[1] + level * 0.2
        speed = random.uniform(speed_lo, speed_hi)

        self.wobble_amp = random.uniform(0.3, 1.5) if random.random() < 0.4 else 0
        self.wobble_freq = random.uniform(0.04, 0.08)
        self.age = 0

        side = random.choice(["left", "right", "top", "bottom"])
        if side == "left":
            self.x = float(-self.radius)
            self.y = float(random.randint(self.radius + 80, h - self.radius))
            angle = random.uniform(-math.pi / 4, math.pi / 4)
        elif side == "right":
            self.x = float(w + self.radius)
            self.y = float(random.randint(self.radius + 80, h - self.radius))
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

    def take_hit(self):
        """Returns True if the target is destroyed."""
        self.hp -= 1
        if self.type == TYPE_FROZEN and self.hp > 0:
            self.cracked = True
            # Visual crack: change outline
            self.outline = (180, 180, 255)
            self.color = (200, 180, 140)
            return False
        return True

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
            cv2.circle(frame, (cx, cy), self.radius + 5, self.outline, -1)
            cv2.circle(frame, (cx, cy), self.radius, self.color, -1)

            if self.type == TYPE_GOLD:
                for _ in range(3):
                    sx = cx + random.randint(-self.radius, self.radius)
                    sy = cy + random.randint(-self.radius, self.radius)
                    cv2.circle(frame, (sx, sy), 2, (255, 255, 255), -1)
                cv2.putText(frame, "*", (cx - 6, cy + 6),
                            FONT, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            elif self.type == TYPE_BOMB:
                cv2.line(frame, (cx - 8, cy - 8), (cx + 8, cy + 8), (0, 0, 255), 3)
                cv2.line(frame, (cx + 8, cy - 8), (cx - 8, cy + 8), (0, 0, 255), 3)
                pulse = int(4 * abs(math.sin(self.age * 0.1)))
                cv2.circle(frame, (cx, cy), self.radius + pulse, (0, 0, 255), 2)
            elif self.type == TYPE_FROZEN:
                # Ice crystal lines
                for angle_deg in (0, 60, 120):
                    rad = math.radians(angle_deg)
                    dx = int(self.radius * 0.6 * math.cos(rad))
                    dy = int(self.radius * 0.6 * math.sin(rad))
                    cv2.line(frame, (cx - dx, cy - dy), (cx + dx, cy + dy),
                             (255, 255, 255), 1)
                if self.cracked:
                    # Crack lines
                    cv2.line(frame, (cx - 6, cy - 8), (cx + 4, cy + 10),
                             (100, 100, 200), 2)
                    cv2.line(frame, (cx + 3, cy - 5), (cx - 5, cy + 7),
                             (100, 100, 200), 2)
                cv2.putText(frame, "ICE", (cx - 14, cy + 5),
                            FONT_SMALL, 1.0, (80, 50, 20), 2, cv2.LINE_AA)

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
        self.vy += PARTICLE_GRAVITY  # gravity — particles drip down
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
        "big_spray": (255, 180, 0),
        "slow_mo":   (200, 200, 0),
        "shield":    (0, 255, 100),
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
        pulse = int(4 * abs(math.sin(self.age * 0.08)))
        cv2.circle(frame, (cx, cy), self.radius + pulse + 3, self.color, 2)
        cv2.circle(frame, (cx, cy), self.radius, self.color, -1)
        cv2.circle(frame, (cx, cy), self.radius, (255, 255, 255), 2)
        cv2.putText(frame, self.label, (cx - 14, cy + 5),
                    FONT_SMALL, 1.2, (0, 0, 0), 2, cv2.LINE_AA)


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


class HandSmoother:
    """Exponential moving average smoother for hand position."""

    def __init__(self, factor=SMOOTH_FACTOR):
        self.factor = factor
        self.sx = None
        self.sy = None

    def update(self, x, y):
        if self.sx is None:
            self.sx, self.sy = x, y
        else:
            self.sx = self.sx * self.factor + x * (1 - self.factor)
            self.sy = self.sy * self.factor + y * (1 - self.factor)
        return self.sx, self.sy

    def reset(self):
        self.sx = self.sy = None


class ThreadedHandTracker:
    """Runs MediaPipe hand detection in a background thread with frame-skip."""

    def __init__(self):
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=cfg("hand_tracking", "detection_confidence", 0.7),
            min_tracking_confidence=cfg("hand_tracking", "tracking_confidence", 0.6),
        )
        self._lock = threading.Lock()
        self._result = None
        self._frame_count = 0
        self._thread = None
        self._running = True
        log.info("ThreadedHandTracker initialised (frame_skip=%d)", FRAME_SKIP)

    def process_async(self, frame_rgb):
        """Submit a frame — only actually processes every Nth frame."""
        self._frame_count += 1
        if self._frame_count % FRAME_SKIP != 0:
            return  # skip — reuse last result
        # If a previous detection is still running, skip
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._detect, args=(frame_rgb.copy(),), daemon=True)
        self._thread.start()

    def _detect(self, rgb):
        result = self._hands.process(rgb)
        with self._lock:
            self._result = result

    @property
    def result(self):
        with self._lock:
            return self._result

    def close(self):
        self._running = False
        self._hands.close()


# ───────────────── Dynamic Border & Watermark ────────────────────────

def draw_dynamic_border(frame, tick, w, h, thickness=6):
    """Draw a cycling Holi-colored border around the frame."""
    idx = (tick // 8) % len(HOLI_COLORS)
    c = HOLI_COLORS[idx]
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), c, thickness)


def draw_watermark(frame, w, h):
    """Draw a small 'Holi Hai!' watermark in the bottom-left."""
    overlay = frame.copy()
    cv2.putText(overlay, "Holi Hai!", (15, h - 18),
                FONT, 0.7, (0, 200, 255), 2, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)


# ───────────────────── Drawing Helpers ────────────────────────────────

def draw_pichkari(frame, cx, cy, is_spraying, color, big_mode=False):
    """Draw a pichkari (nozzle) icon at the given position."""
    cx, cy = int(cx), int(cy)
    scale = 1.4 if big_mode else 1.0

    body_w = int(40 * scale)
    body_h = int(18 * scale)
    tip_len = int(22 * scale)

    tl = (cx - body_w // 2, cy - body_h // 2)
    br = (cx + body_w // 2, cy + body_h // 2)
    cv2.rectangle(frame, tl, br, color, -1)
    cv2.rectangle(frame, tl, br, (255, 255, 255), 2)

    tip_pts = np.array([
        [cx + body_w // 2, cy - int(7 * scale)],
        [cx + body_w // 2 + tip_len, cy],
        [cx + body_w // 2, cy + int(7 * scale)],
    ], np.int32)
    cv2.fillPoly(frame, [tip_pts], color)
    cv2.polylines(frame, [tip_pts], True, (255, 255, 255), 2)

    hw = int(12 * scale)
    hl = int(5 * scale)
    cv2.rectangle(frame,
                  (cx - body_w // 2 - hw, cy - hl),
                  (cx - body_w // 2, cy + hl),
                  (180, 180, 180), -1)

    if is_spraying:
        n_lines = 7 if big_mode else 5
        for _ in range(n_lines):
            length = random.randint(25, int(65 * scale))
            spread = random.randint(int(-25 * scale), int(25 * scale))
            end_x = cx + body_w // 2 + tip_len + length
            end_y = cy + spread
            cv2.line(frame, (cx + body_w // 2 + tip_len, cy),
                     (end_x, end_y), color, random.randint(1, 3))

    cv2.circle(frame, (cx, cy), 3, (0, 0, 0), -1)
    cv2.circle(frame, (cx, cy), 3, (255, 255, 255), 1)

    if big_mode:
        cv2.circle(frame, (cx, cy), int(50 * scale), (255, 200, 0), 2)


def draw_trail(frame, trail, color_idx):
    """Draw a fading rainbow trail behind the pichkari."""
    n = len(trail)
    for i in range(1, n):
        alpha = i / n
        r = max(1, int(6 * alpha))
        c_idx = (color_idx + i) % len(HOLI_COLORS)
        c = tuple(int(v * alpha * 0.6) for v in HOLI_COLORS[c_idx])
        pt = (int(trail[i][0]), int(trail[i][1]))
        cv2.circle(frame, pt, r, c, -1)


def draw_hud(frame, score, lives, max_lives, level, combo, best_combo,
             current_color, is_spraying, w, active_powers, slow_factor,
             fps, accuracy, diff_name, high_score):
    """Draw the game HUD bar."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 70), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    # Title + difficulty
    cv2.putText(frame, "HAND PICHKARI", (12, 35),
                FONT, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    diff_color = DIFFICULTY[diff_name]["label_color"]
    cv2.putText(frame, diff_name.upper(), (12, 55),
                FONT_SMALL, 1.1, diff_color, 2, cv2.LINE_AA)

    # Level
    cv2.putText(frame, f"Lv.{level}", (230, 35),
                FONT, 0.65, (0, 200, 255), 2, cv2.LINE_AA)

    # Combo
    if combo > 1:
        cv2.putText(frame, f"x{combo} COMBO!", (310, 35),
                    FONT, 0.65, (0, 255, 255), 2, cv2.LINE_AA)

    # Status
    status = "SPRAYING!" if is_spraying else "Pinch to spray"
    status_color = (0, 255, 0) if is_spraying else (150, 150, 150)
    cv2.putText(frame, status, (w // 2 - 70, 35),
                FONT, 0.55, status_color, 2, cv2.LINE_AA)

    # Active power-up indicators
    px = w // 2 + 90
    for pwr, end_time in active_powers.items():
        remaining = max(0, end_time - time.time())
        if remaining > 0:
            pcolor = PowerUp.COLORS.get(pwr, (200, 200, 200))
            plabel = PowerUp.LABELS.get(pwr, "?")
            cv2.rectangle(frame, (px, 6), (px + 46, 48), pcolor, -1)
            cv2.putText(frame, plabel, (px + 4, 32),
                        FONT_SMALL, 1.1, (0, 0, 0), 2, cv2.LINE_AA)
            frac = remaining / POWERUP_DURATION
            bar_h = int(36 * frac)
            cv2.rectangle(frame, (px + 38, 48 - bar_h), (px + 46, 48),
                          (255, 255, 255), -1)
            px += 52

    # Slow-mo indicator
    if slow_factor < 1.0:
        cv2.putText(frame, "SLOW-MO", (w // 2 - 40, 62),
                    FONT_SMALL, 1.0, (200, 200, 0), 1, cv2.LINE_AA)

    # Score & high score
    cv2.putText(frame, f"Score: {score}", (w - 260, 30),
                FONT, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Best: {high_score}", (w - 260, 55),
                FONT_SMALL, 1.1, (180, 180, 180), 1, cv2.LINE_AA)

    # Color swatch
    cv2.rectangle(frame, (w - 55, 8), (w - 10, 48), current_color, -1)
    cv2.rectangle(frame, (w - 55, 8), (w - 10, 48), (255, 255, 255), 2)

    # Lives (hearts)
    for i in range(max_lives):
        hx = 12 + i * 26
        hy = 62
        if i < lives:
            cv2.circle(frame, (hx + 4, hy), 5, (0, 0, 255), -1)
            cv2.circle(frame, (hx + 13, hy), 5, (0, 0, 255), -1)
            tri = np.array([[hx - 1, hy + 2], [hx + 18, hy + 2],
                            [hx + 9, hy + 12]], np.int32)
            cv2.fillPoly(frame, [tri], (0, 0, 255))
        else:
            cv2.circle(frame, (hx + 4, hy), 5, (80, 80, 80), 1)
            cv2.circle(frame, (hx + 13, hy), 5, (80, 80, 80), 1)

    # Bottom-right: FPS + Accuracy
    cv2.putText(frame, f"FPS: {fps}", (w - 110, frame.shape[0] - 15),
                FONT_SMALL, 1.0, (150, 150, 150), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Acc: {accuracy}%", (w - 110, frame.shape[0] - 35),
                FONT_SMALL, 1.0, (150, 150, 150), 1, cv2.LINE_AA)


def draw_stains(frame, stains):
    """Draw persistent paint stains."""
    if not stains:
        return
    overlay = frame.copy()
    for s in stains:
        s.draw(overlay)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)


def draw_combo_flash(frame, combo, w, h):
    """Brief colored screen-edge flash at high combos."""
    if combo < 3:
        return
    intensity = min(80, combo * 12)
    color = HOLI_COLORS[combo % len(HOLI_COLORS)]
    c = tuple(min(255, int(v * intensity / 80)) for v in color)
    overlay = frame.copy()
    # Flash borders
    cv2.rectangle(overlay, (0, 0), (w, 8), c, -1)
    cv2.rectangle(overlay, (0, h - 8), (w, h), c, -1)
    cv2.rectangle(overlay, (0, 0), (8, h), c, -1)
    cv2.rectangle(overlay, (w - 8, 0), (w, h), c, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)


def draw_game_over(frame, score, best_combo, accuracy, diff_name,
                   high_score, is_new_record, w, h):
    """Draw Game Over screen with stats."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    cv2.putText(frame, "GAME OVER", (w // 2 - 200, h // 2 - 80),
                FONT, 2.0, (0, 0, 255), 4, cv2.LINE_AA)

    if is_new_record:
        cv2.putText(frame, "NEW HIGH SCORE!", (w // 2 - 170, h // 2 - 40),
                    FONT, 1.0, (0, 255, 255), 3, cv2.LINE_AA)

    # Stats table
    stats = [
        (f"Score: {score}", (0, 255, 255)),
        (f"High Score: {high_score}", (255, 200, 0)),
        (f"Best Combo: x{best_combo}", (0, 255, 0)),
        (f"Accuracy: {accuracy}%", (200, 200, 200)),
        (f"Difficulty: {diff_name}", DIFFICULTY[diff_name]["label_color"]),
    ]
    for i, (txt, col) in enumerate(stats):
        cv2.putText(frame, txt, (w // 2 - 130, h // 2 + 10 + i * 35),
                    FONT, 0.7, col, 2, cv2.LINE_AA)

    cv2.putText(frame, "SPACE = Play Again  |  Q = Quit",
                (w // 2 - 220, h // 2 + 200),
                FONT, 0.6, (180, 180, 180), 2, cv2.LINE_AA)

    # Decorative splatters
    for _ in range(6):
        cv2.circle(frame, (random.randint(40, w - 40), random.randint(40, h - 40)),
                   random.randint(12, 35), random.choice(HOLI_COLORS), -1)


def draw_start_screen(frame, w, h, selected_diff, high_scores, time_trial=False):
    """Draw the start / title screen with difficulty selection."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    cv2.putText(frame, "HAND PICHKARI", (w // 2 - 280, h // 2 - 110),
                FONT, 2.5, (0, 255, 255), 5, cv2.LINE_AA)
    cv2.putText(frame, "Competitive Holi Edition v4", (w // 2 - 200, h // 2 - 60),
                FONT, 0.8, (255, 200, 0), 2, cv2.LINE_AA)

    # Difficulty selection
    diffs = list(DIFFICULTY.keys())
    for i, d in enumerate(diffs):
        key_num = i + 1
        is_sel = (d == selected_diff)
        color = DIFFICULTY[d]["label_color"] if is_sel else (120, 120, 120)
        prefix = "> " if is_sel else "  "
        hs_key = f"{d}_tt" if time_trial else d
        hs = high_scores.get(hs_key, 0)
        txt = f"{prefix}[{key_num}] {d}  (Best: {hs})"
        cv2.putText(frame, txt, (w // 2 - 180, h // 2 - 10 + i * 40),
                    FONT, 0.7, color, 2, cv2.LINE_AA)

    # Time trial toggle
    tt_label = "[T] Time Trial: ON" if time_trial else "[T] Time Trial: OFF"
    tt_color = (0, 255, 255) if time_trial else (120, 120, 120)
    cv2.putText(frame, tt_label, (w // 2 - 120, h // 2 + 115),
                FONT, 0.65, tt_color, 2, cv2.LINE_AA)

    # Instructions
    instructions = [
        "Show hand to camera | Pinch to SPRAY",
        "Hit targets, avoid bombs, collect power-ups!",
        "",
        "1/2/3 = Difficulty | T = Time Trial | SPACE = Start | Q = Quit",
    ]
    base_y = h // 2 + 150
    for i, line in enumerate(instructions):
        c = (180, 180, 180) if line else (0, 0, 0)
        cv2.putText(frame, line, (w // 2 - 280, base_y + i * 30),
                    FONT, 0.52, c, 1, cv2.LINE_AA)

    # Decorative circles
    for _ in range(10):
        cv2.circle(frame, (random.randint(20, w - 20), random.randint(20, h - 20)),
                   random.randint(6, 25), random.choice(HOLI_COLORS), -1)


# ──────────────────────────── Main Game ──────────────────────────────

def main():
    tracker = ThreadedHandTracker()

    cap = cv2.VideoCapture(CAM_DEVICE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    if not cap.isOpened():
        log.error("Cannot open webcam (device %d).", CAM_DEVICE)
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    log.info("Camera opened: %dx%d (device %d)", w, h, CAM_DEVICE)

    high_scores = load_high_scores()

    # ── Game state ──────────────────────────────────────────────────
    def reset_game(diff_name="Medium", time_trial=False):
        diff = DIFFICULTY[diff_name]
        lives = 999 if time_trial else diff["max_lives"]
        return {
            "score": 0,
            "lives": lives,
            "level": 1,
            "combo": 0,
            "best_combo": 0,
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
            "smoother": HandSmoother(),
            "trail": [],
            "diff_name": diff_name,
            "diff": diff,
            "prev_level": 1,
            "total_sprays": 0,
            "total_hits": 0,
            "is_new_record": False,
            "fps_time": time.time(),
            "fps_count": 0,
            "fps": 0,
            "time_trial": time_trial,
            "game_start_time": 0.0,
            "tick": 0,
        }

    selected_diff = "Medium"
    time_trial_on = False
    gs = reset_game(selected_diff, time_trial_on)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        now = time.time()

        # ── FPS counter ─────────────────────────────────────────────
        gs["fps_count"] += 1
        if now - gs["fps_time"] >= 1.0:
            gs["fps"] = gs["fps_count"]
            gs["fps_count"] = 0
            gs["fps_time"] = now

        # ── Hand detection (threaded) ────────────────────────────────
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tracker.process_async(rgb)
        results = tracker.result

        pichkari_x, pichkari_y = -100.0, -100.0
        is_pinching = False

        if results and results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            idx_tip = hand.landmark[8]
            thumb_tip = hand.landmark[4]

            ix, iy = int(idx_tip.x * w), int(idx_tip.y * h)
            tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)

            raw_x = (ix + tx) / 2.0
            raw_y = (iy + ty) / 2.0

            pichkari_x, pichkari_y = gs["smoother"].update(raw_x, raw_y)

            dist = math.hypot(ix - tx, iy - ty)
            is_pinching = dist < PINCH_THRESHOLD

            cv2.circle(frame, (ix, iy), 5, (100, 255, 100), -1)
            cv2.circle(frame, (tx, ty), 5, (100, 100, 255), -1)
            cv2.line(frame, (ix, iy), (tx, ty), (200, 200, 200), 1)
        else:
            gs["smoother"].reset()

        # ── Start screen ────────────────────────────────────────────
        if not gs["started"]:
            draw_start_screen(frame, w, h, selected_diff, high_scores, time_trial_on)
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                gs = reset_game(selected_diff, time_trial_on)
                gs["started"] = True
                gs["game_start_time"] = time.time()
                start_bg_music()
                log.info("Game started: %s, time_trial=%s", selected_diff, time_trial_on)
            elif key == ord('1'):
                selected_diff = "Easy"
            elif key == ord('2'):
                selected_diff = "Medium"
            elif key == ord('3'):
                selected_diff = "Hard"
            elif key in (ord('t'), ord('T')):
                time_trial_on = not time_trial_on
            elif key in (ord('q'), 27):
                break
            continue

        # ── Game Over screen ────────────────────────────────────────
        if gs["game_over"]:
            stop_bg_music()
            draw_stains(frame, gs["stains"])
            accuracy = _calc_accuracy(gs)
            hs_key = f"{gs['diff_name']}_tt" if gs["time_trial"] else gs["diff_name"]
            draw_game_over(frame, gs["score"], gs["best_combo"], accuracy,
                           gs["diff_name"], high_scores.get(hs_key, 0),
                           gs["is_new_record"], w, h)
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                gs = reset_game(selected_diff, time_trial_on)
                gs["started"] = True
                gs["game_start_time"] = time.time()
                start_bg_music()
            elif key in (ord('q'), 27):
                break
            continue

        diff = gs["diff"]

        # ── Active power-ups ────────────────────────────────────────
        active = gs["active_powers"]
        big_spray = active.get("big_spray", 0) > now
        slow_mo = active.get("slow_mo", 0) > now
        shield = active.get("shield", 0) > now
        slow_factor = 0.5 if slow_mo else 1.0
        spray_radius = int(BASE_SPRAY_RADIUS * (1.8 if big_spray else 1.0))

        # ── Color switching ─────────────────────────────────────────
        if is_pinching and not gs["was_pinching"]:
            gs["color_idx"] = (gs["color_idx"] + 1) % len(HOLI_COLORS)

        # Track spray attempts (each new pinch = 1 spray)
        if is_pinching and not gs["was_pinching"]:
            gs["total_sprays"] += 1

        gs["was_pinching"] = is_pinching
        current_color = HOLI_COLORS[gs["color_idx"]]

        # ── Level ───────────────────────────────────────────────────
        gs["level"] = min(MAX_LEVEL, 1 + gs["score"] // diff["level_up_score"])
        level = gs["level"]

        # Level-up notification
        if level > gs["prev_level"]:
            gs["prev_level"] = level
            gs["floats"].append(
                FloatingText(w // 2 - 60, h // 2, f"LEVEL {level}!",
                             (0, 255, 255), 1.2))
            threading.Thread(target=sfx_levelup, daemon=True).start()

        # ── Trail ───────────────────────────────────────────────────
        if pichkari_x > 0:
            gs["trail"].append((pichkari_x, pichkari_y))
            if len(gs["trail"]) > TRAIL_LENGTH:
                gs["trail"].pop(0)
        else:
            gs["trail"].clear()

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
        spawn_interval = max(0.4, diff["base_spawn_interval"] - level * 0.08)
        max_targets = min(14, diff["base_max_targets"] + level // 2)

        if (now - gs["last_spawn"] > spawn_interval and
                len(gs["targets"]) < max_targets):
            roll = random.random()
            bomb_thresh = diff["bomb_chance"] + level * 0.005
            if roll < bomb_thresh:
                ttype = TYPE_BOMB
            elif roll < bomb_thresh + 0.10:
                ttype = TYPE_GOLD
            elif roll < bomb_thresh + 0.16 and level >= 3:
                ttype = TYPE_FROZEN
            else:
                ttype = TYPE_NORMAL
            gs["targets"].append(Target(w, h, level, ttype, diff))
            gs["last_spawn"] = now

        # ── Spawn power-ups ─────────────────────────────────────────
        if (now - gs["last_powerup_spawn"] > 8.0 and
                len(gs["powerups"]) < 2 and random.random() < POWERUP_SPAWN_CHANCE):
            gs["powerups"].append(PowerUp(w, h))
            gs["last_powerup_spawn"] = now

        # ── Draw stains ─────────────────────────────────────────────
        draw_stains(frame, gs["stains"])

        # ── Draw trail ──────────────────────────────────────────────
        if len(gs["trail"]) > 1:
            draw_trail(frame, gs["trail"], gs["color_idx"])

        # ── Update & check targets ──────────────────────────────────
        escaped_count = 0
        for t in gs["targets"]:
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
                        if not shield:
                            gs["lives"] -= 1
                            gs["floats"].append(
                                FloatingText(int(t.x), int(t.y) - 20,
                                             "BOOM! -1 Life", (0, 0, 255), 0.9))
                            gs["shake"].trigger(12, 0.2)
                            sfx_bomb()
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
                        destroyed = t.take_hit()
                        if destroyed:
                            t.hit = True
                            t.hit_time = now
                            t.hit_color = current_color

                            # Combo
                            if now - gs["last_hit_time"] < COMBO_TIMEOUT:
                                gs["combo"] += 1
                            else:
                                gs["combo"] = 1
                            gs["last_hit_time"] = now
                            gs["best_combo"] = max(gs["best_combo"], gs["combo"])

                            points = t.points * gs["combo"]
                            gs["score"] += points
                            gs["total_hits"] += 1

                            # Floating text
                            txt = f"+{points}"
                            if gs["combo"] > 1:
                                txt += f" x{gs['combo']}"
                            if t.type == TYPE_GOLD:
                                txt += " GOLD!"
                            elif t.type == TYPE_FROZEN:
                                txt += " ICE!"
                            gs["floats"].append(
                                FloatingText(int(t.x) - 20, int(t.y) - 20,
                                             txt, current_color, 0.9))

                            gs["splashes"].append(
                                SplashEffect(int(t.x), int(t.y), current_color, 35))
                            gs["stains"].append(
                                PaintStain(t.x, t.y, current_color,
                                           t.radius + random.randint(5, 20)))
                            if len(gs["stains"]) > MAX_STAINS:
                                gs["stains"].pop(0)

                            gs["shake"].trigger(6, 0.1)

                            if t.type == TYPE_GOLD:
                                sfx_gold()
                            else:
                                sfx_hit()
                        else:
                            # Frozen: cracked but not destroyed
                            gs["floats"].append(
                                FloatingText(int(t.x) - 15, int(t.y) - 15,
                                             "CRACK!", (200, 200, 255), 0.7))
                            gs["splashes"].append(
                                SplashEffect(int(t.x), int(t.y),
                                             (200, 220, 255), 15))
                            sfx_hit()

            if not t.hit and t.is_off_screen(w, h):
                if t.type == TYPE_NORMAL:
                    t.escaped = True
                    escaped_count += 1

            t.draw(frame, now)

        # Escaped targets
        if escaped_count > 0:
            gs["lives"] -= escaped_count
            gs["combo"] = 0
            sfx_miss()

        gs["targets"] = [t for t in gs["targets"]
                         if not t.finished_fading(now)
                         and not t.escaped
                         and not (t.is_off_screen(w, h) and t.type != TYPE_NORMAL)]

        # ── Power-ups ───────────────────────────────────────────────
        for pu in gs["powerups"]:
            pu.update()
            if is_pinching and pichkari_x > 0 and not pu.collected:
                d = math.hypot(pu.x - pichkari_x, pu.y - pichkari_y)
                if d < pu.radius + spray_radius:
                    pu.collected = True
                    gs["active_powers"][pu.kind] = now + POWERUP_DURATION
                    gs["floats"].append(
                        FloatingText(int(pu.x), int(pu.y) - 20,
                                     f"POWER: {pu.label}!", pu.color, 0.9))
                    gs["shake"].trigger(4, 0.08)
                    sfx_powerup()
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

        # ── Combo flash ─────────────────────────────────────────────
        draw_combo_flash(frame, gs["combo"], w, h)

        # ── Pichkari ────────────────────────────────────────────────
        if pichkari_x > 0:
            draw_pichkari(frame, pichkari_x, pichkari_y,
                          is_pinching, current_color, big_spray)

        # ── Shield ring ─────────────────────────────────────────────
        if shield and pichkari_x > 0:
            cv2.circle(frame, (int(pichkari_x), int(pichkari_y)),
                       70, (0, 255, 100), 2)

        # ── HUD ─────────────────────────────────────────────────────
        accuracy = _calc_accuracy(gs)
        hs_key = f"{gs['diff_name']}_tt" if gs["time_trial"] else gs["diff_name"]
        draw_hud(frame, gs["score"], gs["lives"], diff["max_lives"], level,
                 gs["combo"], gs["best_combo"], current_color, is_pinching, w,
                 gs["active_powers"], slow_factor, gs["fps"], accuracy,
                 gs["diff_name"], high_scores.get(hs_key, 0))

        # ── Time trial timer ────────────────────────────────────────
        if gs["time_trial"]:
            elapsed = now - gs["game_start_time"]
            remaining = max(0.0, TIME_TRIAL_SECONDS - elapsed)
            mins = int(remaining) // 60
            secs = int(remaining) % 60
            timer_color = (0, 0, 255) if remaining < 10 else (0, 255, 255)
            cv2.putText(frame, f"TIME: {mins}:{secs:02d}", (w // 2 - 70, h - 20),
                        FONT, 0.9, timer_color, 2, cv2.LINE_AA)
            cv2.putText(frame, "TIME TRIAL", (w // 2 - 65, h - 45),
                        FONT_SMALL, 1.0, (0, 255, 255), 1, cv2.LINE_AA)

        # ── Combo timeout ───────────────────────────────────────────
        if now - gs["last_hit_time"] > COMBO_TIMEOUT:
            gs["combo"] = 0

        # ── Dynamic border & watermark ──────────────────────────────
        gs["tick"] += 1
        draw_dynamic_border(frame, gs["tick"], w, h)
        draw_watermark(frame, w, h)

        # ── Screen shake ────────────────────────────────────────────
        frame = gs["shake"].apply(frame)

        # ── Game over check ─────────────────────────────────────────
        game_over_triggered = False
        if gs["time_trial"]:
            elapsed = now - gs["game_start_time"]
            if elapsed >= TIME_TRIAL_SECONDS:
                game_over_triggered = True
        else:
            if gs["lives"] <= 0:
                game_over_triggered = True

        if game_over_triggered and not gs["game_over"]:
            gs["game_over"] = True
            dn = f"{gs['diff_name']}_tt" if gs["time_trial"] else gs["diff_name"]
            if gs["score"] > high_scores.get(dn, 0):
                high_scores[dn] = gs["score"]
                gs["is_new_record"] = True
                save_high_scores(high_scores)
            sfx_gameover()
            log.info("Game over: score=%d, diff=%s, time_trial=%s",
                     gs["score"], gs["diff_name"], gs["time_trial"])

        # ── Show ────────────────────────────────────────────────────
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord('r'):
            stop_bg_music()
            gs = reset_game(gs["diff_name"], time_trial_on)
            gs["started"] = True
            gs["game_start_time"] = time.time()
            start_bg_music()

    stop_bg_music()
    cap.release()
    cv2.destroyAllWindows()
    tracker.close()
    log.info("Game ended. Final score: %d", gs["score"])


def _calc_accuracy(gs):
    """Calculate accuracy percentage."""
    if gs["total_sprays"] == 0:
        return 0
    return int(gs["total_hits"] / gs["total_sprays"] * 100)


if __name__ == "__main__":
    main()
