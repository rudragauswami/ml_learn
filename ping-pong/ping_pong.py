"""
Ping Pong
=========
A 2D ping pong game controlled by hand gestures via webcam.
Uses OpenCV for video capture, MediaPipe for real-time hand tracking.

Controls:
  - Move your RIGHT hand's index finger left/right to move the paddle.
  - Press 'q' to quit.
  - Press 'r' to restart after game over.
"""

import cv2
import numpy as np
import mediapipe as mp
import random
import math
import time

# ──────────────────────── Constants ────────────────────────
WINDOW_NAME = "Ping Pong"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Paddle
PADDLE_WIDTH = 130
PADDLE_MIN_WIDTH = 70         # paddle shrinks as score rises
PADDLE_HEIGHT = 16
PADDLE_Y_OFFSET = 60          # distance from bottom
PADDLE_COLOR = (0, 255, 200)  # bright cyan-green
PADDLE_BORDER = (255, 255, 255)
PADDLE_RADIUS = 8

# Ball
BALL_RADIUS = 13
BALL_COLOR = (0, 180, 255)    # orange
BALL_OUTLINE = (255, 255, 255)
BALL_SPEED = 10               # faster starting speed
BALL_SPEED_INCREMENT = 0.6    # ramps up quicker per hit
BALL_MAX_SPEED = 24           # much higher ceiling

# Trail (ghosting effect)
TRAIL_LENGTH = 10
TRAIL_ALPHA_STEP = 25

# Particles
PARTICLE_COUNT = 18
PARTICLE_LIFETIME = 18

# Combo system
COMBO_TIMEOUT = 90            # frames to keep combo alive
COMBO_COLORS = [
    (0, 255, 200),   # 1x - cyan
    (0, 255, 100),   # 2x - green
    (0, 200, 255),   # 3x - blue
    (255, 200, 0),   # 4x - gold
    (255, 100, 0),   # 5x+ - orange-red
]

# UI Colors
SCORE_COLOR = (255, 255, 255)
GAMEOVER_COLOR = (0, 0, 255)
OVERLAY_COLOR = (0, 0, 0)


# ──────────────────────── Helper classes ────────────────────────
class Particle:
    """A simple particle for collision effects."""
    def __init__(self, x, y, color):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.lifetime = PARTICLE_LIFETIME
        self.color = color
        self.radius = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self, frame):
        if self.lifetime > 0:
            alpha = max(0, self.lifetime / PARTICLE_LIFETIME)
            r = max(1, int(self.radius * alpha))
            cv2.circle(frame, (int(self.x), int(self.y)), r, self.color, -1)


class Ball:
    """The bouncing ball with trail effect."""
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.trail = []
        self.reset()

    def reset(self):
        self.x = self.w // 2
        self.y = self.h // 3
        self.speed = BALL_SPEED
        # Random direction, avoiding too-horizontal launches
        angle = random.uniform(math.pi / 6, 5 * math.pi / 6)
        if random.random() > 0.5:
            angle = -angle
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.trail.clear()

    def update(self):
        # Normalise velocity to current speed
        mag = math.hypot(self.vx, self.vy)
        if mag != 0:
            self.vx = (self.vx / mag) * self.speed
            self.vy = (self.vy / mag) * self.speed

        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > TRAIL_LENGTH:
            self.trail.pop(0)

        self.x += self.vx
        self.y += self.vy

    def bounce_x(self):
        self.vx = -self.vx

    def bounce_y(self):
        self.vy = -self.vy

    def speed_up(self):
        self.speed = min(self.speed + BALL_SPEED_INCREMENT, BALL_MAX_SPEED)

    def draw(self, frame):
        # Draw trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int((i / TRAIL_LENGTH) * 180)
            r = max(3, int(BALL_RADIUS * (i / TRAIL_LENGTH)))
            overlay = frame.copy()
            cv2.circle(overlay, (tx, ty), r, BALL_COLOR, -1)
            cv2.addWeighted(overlay, alpha / 255, frame, 1 - alpha / 255, 0, frame)

        # Main ball
        cv2.circle(frame, (int(self.x), int(self.y)), BALL_RADIUS, BALL_OUTLINE, 2)
        cv2.circle(frame, (int(self.x), int(self.y)), BALL_RADIUS - 2, BALL_COLOR, -1)

        # Small shine
        shine_x = int(self.x) - 4
        shine_y = int(self.y) - 4
        cv2.circle(frame, (shine_x, shine_y), 3, (255, 255, 255), -1)


class Paddle:
    """Paddle that tracks the index finger."""
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.base_width = PADDLE_WIDTH
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.x = w // 2  # center x of paddle
        self.y = h - PADDLE_Y_OFFSET
        self.target_x = self.x
        self.smoothing = 0.4  # slightly more responsive

    def shrink_for_score(self, score):
        """Paddle gets narrower as score increases — harder over time."""
        shrink = score * 3  # lose 3px width per point
        self.width = max(PADDLE_MIN_WIDTH, self.base_width - shrink)

    def update(self, finger_x=None):
        if finger_x is not None:
            self.target_x = finger_x

        # Smooth interpolation
        self.x += (self.target_x - self.x) * self.smoothing

        # Clamp to screen
        half = self.width // 2
        self.x = max(half, min(self.w - half, self.x))

    @property
    def rect(self):
        """Return (x1, y1, x2, y2) of the paddle."""
        half = self.width // 2
        return (
            int(self.x - half),
            int(self.y - self.height // 2),
            int(self.x + half),
            int(self.y + self.height // 2),
        )

    def draw(self, frame):
        x1, y1, x2, y2 = self.rect
        # Glow
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1 - 4, y1 - 4), (x2 + 4, y2 + 4), PADDLE_COLOR, -1)
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
        # Main paddle (rounded rect via two rects + circles)
        cv2.rectangle(frame, (x1 + PADDLE_RADIUS, y1), (x2 - PADDLE_RADIUS, y2), PADDLE_COLOR, -1)
        cv2.rectangle(frame, (x1, y1 + PADDLE_RADIUS), (x2, y2 - PADDLE_RADIUS), PADDLE_COLOR, -1)
        cv2.circle(frame, (x1 + PADDLE_RADIUS, y1 + PADDLE_RADIUS), PADDLE_RADIUS, PADDLE_COLOR, -1)
        cv2.circle(frame, (x2 - PADDLE_RADIUS, y1 + PADDLE_RADIUS), PADDLE_RADIUS, PADDLE_COLOR, -1)
        cv2.circle(frame, (x1 + PADDLE_RADIUS, y2 - PADDLE_RADIUS), PADDLE_RADIUS, PADDLE_COLOR, -1)
        cv2.circle(frame, (x2 - PADDLE_RADIUS, y2 - PADDLE_RADIUS), PADDLE_RADIUS, PADDLE_COLOR, -1)
        # Border
        cv2.rectangle(frame, (x1, y1), (x2, y2), PADDLE_BORDER, 2, cv2.LINE_AA)


# ──────────────────────── UI Drawing ────────────────────────

def draw_score(frame, score, best, combo=0, combo_timer=0):
    """Draw score, best score, and combo on screen."""
    # Semi-transparent banner at top
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 56), OVERLAY_COLOR, -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    text = f"SCORE: {score}"
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                SCORE_COLOR, 3, cv2.LINE_AA)

    # Combo display
    if combo > 1 and combo_timer > 0:
        combo_idx = min(combo - 1, len(COMBO_COLORS) - 1)
        combo_color = COMBO_COLORS[combo_idx]
        scale = 1.0 + combo * 0.1  # text grows with combo
        combo_text = f"x{combo} COMBO!"
        cv2.putText(frame, combo_text, (20, 85), cv2.FONT_HERSHEY_SIMPLEX,
                    min(scale, 1.8), combo_color, 3, cv2.LINE_AA)

    best_text = f"BEST: {best}"
    tw = cv2.getTextSize(best_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0][0]
    cv2.putText(frame, best_text, (frame.shape[1] - tw - 20, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)


def draw_speed_bar(frame, speed):
    """Show a speed indicator bar."""
    ratio = (speed - BALL_SPEED) / (BALL_MAX_SPEED - BALL_SPEED)
    ratio = max(0.0, min(1.0, ratio))
    bar_w = 180
    bar_h = 10
    x = frame.shape[1] - bar_w - 20
    y = 58
    cv2.rectangle(frame, (x, y), (x + bar_w, y + bar_h), (80, 80, 80), -1)
    filled = int(bar_w * ratio)
    color = (
        int(255 * ratio),
        int(255 * (1 - ratio)),
        0,
    )
    if filled > 0:
        cv2.rectangle(frame, (x, y), (x + filled, y + bar_h), color, -1)
    cv2.rectangle(frame, (x, y), (x + bar_w, y + bar_h), (180, 180, 180), 1)
    cv2.putText(frame, "SPEED", (x, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (180, 180, 180), 1, cv2.LINE_AA)


def draw_game_over(frame, score, best):
    """Draw game over overlay."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    cx, cy = frame.shape[1] // 2, frame.shape[0] // 2

    # Title
    title = "GAME OVER"
    ts = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 2.2, 4)[0]
    cv2.putText(frame, title, (cx - ts[0] // 2, cy - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 2.2, GAMEOVER_COLOR, 4, cv2.LINE_AA)

    # Score
    stxt = f"Score: {score}    Best: {best}"
    ss = cv2.getTextSize(stxt, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
    cv2.putText(frame, stxt, (cx - ss[0] // 2, cy + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, SCORE_COLOR, 2, cv2.LINE_AA)

    # Restart hint
    hint = "Press 'R' to restart  |  'Q' to quit"
    hs = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    cv2.putText(frame, hint, (cx - hs[0] // 2, cy + 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2, cv2.LINE_AA)


def draw_start_screen(frame):
    """Draw a start/waiting overlay."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    cx, cy = frame.shape[1] // 2, frame.shape[0] // 2

    title = "PING PONG"
    ts = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.6, 3)[0]
    cv2.putText(frame, title, (cx - ts[0] // 2, cy - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 200), 3, cv2.LINE_AA)

    hint = "Show your RIGHT hand to start!"
    hs = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
    cv2.putText(frame, hint, (cx - hs[0] // 2, cy + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

    sub = "Control the paddle with your index finger"
    ss = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
    cv2.putText(frame, sub, (cx - ss[0] // 2, cy + 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1, cv2.LINE_AA)


def draw_walls(frame):
    """Draw subtle border lines on top, left, right edges."""
    h, w = frame.shape[:2]
    color = (100, 255, 200)
    thickness = 2
    cv2.line(frame, (0, 0), (w, 0), color, thickness)         # top
    cv2.line(frame, (0, 0), (0, h), color, thickness)         # left
    cv2.line(frame, (w - 1, 0), (w - 1, h), color, thickness) # right


def draw_finger_indicator(frame, fx, fy):
    """Draw a small crosshair at the detected finger tip."""
    ix, iy = int(fx), int(fy)
    size = 12
    color = (0, 255, 0)
    cv2.line(frame, (ix - size, iy), (ix + size, iy), color, 1, cv2.LINE_AA)
    cv2.line(frame, (ix, iy - size), (ix, iy + size), color, 1, cv2.LINE_AA)
    cv2.circle(frame, (ix, iy), 4, color, -1)


# ──────────────────────── Main game loop ────────────────────────

def main():
    # Initialise MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )

    # Initialise webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] Cannot open webcam. Please check your camera connection.")
        return

    # Read one frame to get actual dimensions
    ret, test_frame = cap.read()
    if not ret:
        print("[ERROR] Cannot read from webcam.")
        cap.release()
        return
    actual_h, actual_w = test_frame.shape[:2]

    # Game objects
    ball = Ball(actual_w, actual_h)
    paddle = Paddle(actual_w, actual_h)
    particles = []

    score = 0
    best_score = 0
    combo = 0
    combo_timer = 0
    game_over = False
    game_started = False
    hand_detected = False

    print(f"[INFO] Game window: {actual_w}x{actual_h}")
    print("[INFO] Show your RIGHT hand to start. Press 'Q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Mirror the frame for intuitive control
        frame = cv2.flip(frame, 1)

        # ── Hand detection ──
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        finger_x = None
        finger_y = None
        hand_detected = False

        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                # After mirroring, MediaPipe's "Right" label = user's right hand
                label = handedness.classification[0].label
                if label == "Right":
                    hand_detected = True
                    # Index finger tip = landmark 8
                    tip = hand_landmarks.landmark[8]
                    finger_x = tip.x * actual_w
                    finger_y = tip.y * actual_h

                    if not game_started:
                        game_started = True
                    break

        # ── Darken the background slightly for better contrast ──
        frame = cv2.addWeighted(frame, 0.75, np.zeros_like(frame), 0.25, 0)

        # ── Game states ──
        if not game_started:
            draw_walls(frame)
            if finger_x is not None:
                draw_finger_indicator(frame, finger_x, finger_y)
            draw_start_screen(frame)

        elif game_over:
            paddle.update(finger_x)
            draw_walls(frame)
            paddle.draw(frame)
            if finger_x is not None:
                draw_finger_indicator(frame, finger_x, finger_y)
            draw_game_over(frame, score, best_score)

        else:
            # ── Update ──
            paddle.update(finger_x)
            ball.update()

            # Wall collisions
            # Left wall
            if ball.x - BALL_RADIUS <= 0:
                ball.x = BALL_RADIUS
                ball.bounce_x()
                particles += [Particle(ball.x, ball.y, (100, 255, 200)) for _ in range(8)]

            # Right wall
            if ball.x + BALL_RADIUS >= actual_w:
                ball.x = actual_w - BALL_RADIUS
                ball.bounce_x()
                particles += [Particle(ball.x, ball.y, (100, 255, 200)) for _ in range(8)]

            # Top wall
            if ball.y - BALL_RADIUS <= 0:
                ball.y = BALL_RADIUS
                ball.bounce_y()
                particles += [Particle(ball.x, ball.y, (100, 255, 200)) for _ in range(8)]

            # Combo timer countdown
            if combo_timer > 0:
                combo_timer -= 1
            else:
                combo = 0

            # Paddle shrinks with score
            paddle.shrink_for_score(score)

            # Paddle collision
            px1, py1, px2, py2 = paddle.rect
            if (ball.vy > 0 and
                ball.y + BALL_RADIUS >= py1 and
                ball.y - BALL_RADIUS <= py2 and
                ball.x >= px1 and
                ball.x <= px2):

                ball.y = py1 - BALL_RADIUS
                # Angle depends on where ball hits paddle
                hit_pos = (ball.x - paddle.x) / (paddle.width / 2)  # -1 to 1
                hit_pos = max(-0.9, min(0.9, hit_pos))
                angle = -math.pi / 2 + hit_pos * (math.pi / 3)
                ball.vx = math.cos(angle) * ball.speed
                ball.vy = math.sin(angle) * ball.speed
                # Ensure ball goes upward
                if ball.vy > 0:
                    ball.vy = -ball.vy

                ball.speed_up()
                combo += 1
                combo_timer = COMBO_TIMEOUT
                points = combo  # combo multiplier!
                score += points
                best_score = max(best_score, score)

                # More particles for higher combos
                pcount = PARTICLE_COUNT + combo * 3
                combo_idx = min(combo - 1, len(COMBO_COLORS) - 1)
                particles += [Particle(ball.x, ball.y, COMBO_COLORS[combo_idx]) for _ in range(pcount)]

            # Bottom wall → game over
            if ball.y - BALL_RADIUS > actual_h:
                game_over = True
                combo = 0
                combo_timer = 0
                particles += [Particle(ball.x, actual_h, GAMEOVER_COLOR) for _ in range(25)]

            # ── Draw ──
            draw_walls(frame)
            ball.draw(frame)
            paddle.draw(frame)

            if finger_x is not None:
                draw_finger_indicator(frame, finger_x, finger_y)

            draw_score(frame, score, best_score, combo, combo_timer)
            draw_speed_bar(frame, ball.speed)

        # ── Particles ──
        for p in particles:
            p.update()
            p.draw(frame)
        particles = [p for p in particles if p.lifetime > 0]

        # ── Hand status indicator ──
        indicator_color = (0, 255, 0) if hand_detected else (0, 0, 200)
        cv2.circle(frame, (actual_w - 30, 40), 8, indicator_color, -1)
        status = "HAND OK" if hand_detected else "NO HAND"
        cv2.putText(frame, status, (actual_w - 120, 46), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, indicator_color, 1, cv2.LINE_AA)

        # ── Show frame ──
        cv2.imshow(WINDOW_NAME, frame)

        # ── Key handling ──
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break
        if key == ord('r') or key == ord('R'):
            if game_over:
                game_over = False
                score = 0
                combo = 0
                combo_timer = 0
                paddle.width = paddle.base_width  # reset paddle size
                ball.reset()
                particles.clear()

    # Cleanup
    hands.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
