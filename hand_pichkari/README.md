# 🎨 Hand Pichkari v4 — Competitive Holi Edition

A hand-gesture controlled Holi game built with **OpenCV** and **MediaPipe**. Spray color at floating targets using pinch gestures, avoid bombs, collect power-ups, and chase high scores across three difficulty levels and a Time Trial mode!

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange)

---

## 🚀 Quick Start

```bash
pip install opencv-python mediapipe numpy
pip install pygame              # optional — for better audio & background music
python hand_pichkari.py
```

Press **1/2/3** to pick difficulty, **T** to toggle Time Trial, then **SPACE** to start.

---

## 🎮 Controls

| Action | Input |
|---|---|
| **Aim** | Move hand (tracks thumb + index midpoint) |
| **Spray** | Pinch thumb + index finger |
| **Color cycle** | Auto-switches on each pinch |
| **Difficulty** | `1` Easy · `2` Medium · `3` Hard (title screen) |
| **Time Trial** | `T` toggle (title screen) |
| **Restart** | `R` (mid-game) or `SPACE` (game over) |
| **Quit** | `Q` / `ESC` |

---

## 🎯 Targets

| Target | Look | Points | Notes |
|---|---|---|---|
| **Normal** | ⚪ White | 1× combo | Escaping costs a life |
| **Gold** | 🌟 Golden sparkle | 3× combo | High value |
| **Frozen** | 🧊 Ice-blue "ICE" | 2× combo | Needs **2 hits** to break |
| **Bomb** | 💣 Black + red ✕ | — | Spraying costs a life (avoid!) |

---

## ⚡ Power-Ups (6 seconds each)

| Power-Up | Label | Effect |
|---|---|---|
| **Big Spray** | `BIG` | 1.8× spray radius |
| **Slow-Mo** | `SLO` | Targets move at half speed |
| **Shield** | `SHD` | Immune to bombs |

---

## 📈 Competitive Features

| Feature | Details |
|---|---|
| **3 Difficulties** | Easy (7 lives) · Medium (5 lives) · Hard (3 lives) |
| **Time Trial Mode** | 60-second countdown, unlimited lives, press `T` to toggle |
| **Combo System** | Hit within 2s for ×2, ×3, ×4… multiplier + screen-edge flash |
| **Progressive Levels** | Every N points → faster, smaller, more targets + bombs |
| **High Score Persistence** | Saved per-difficulty & per-mode to `highscores.json` |
| **Accuracy Tracking** | Spray attempts vs. successful hits |
| **Best Combo** | Tracked and shown on game-over |
| **FPS Counter** | Bottom-right corner |

---

## 🔊 Audio

- **With pygame installed**: Synthesized WAV tones — pop (hit), bling (gold), boom (bomb), chime (power-up), fanfare (level-up), plus low-volume background music loop
- **Without pygame**: Falls back to Windows `winsound` beeps
- **Neither available**: Runs silently

---

## 🎨 Visual Polish

- **Threaded hand detection** — MediaPipe runs in a background thread for smooth FPS
- **Frame skipping** — processes every 2nd frame, reusing results for skipped frames
- **Smooth hand tracking** — EMA filter eliminates jitter
- **Particle gravity** — splash particles arc downward (dripping paint effect)
- **Rainbow trail** — colorful trail follows the pichkari
- **Dynamic Holi border** — cycling colored border around the frame
- **"Holi Hai!" watermark** — semi-transparent bottom-left corner text
- **Combo flash** — screen-edge glow at ×3+ combos
- **Persistent paint stains** — targets leave color splatters on the background
- **Screen shake** — on impacts and bomb explosions
- **Floating score text** — animated "+3 ×2 GOLD!" popups

---

## ⚙️ Configuration

All tunable parameters live in `settings.json` (loaded at startup, hardcoded defaults used as fallback):

| Section | Key | Default | Description |
|---|---|---|---|
| `camera` | `width` / `height` | 1280×720 | Camera resolution |
| `camera` | `device_index` | 0 | Webcam device ID |
| `hand_tracking` | `pinch_threshold` | 42 px | Pinch sensitivity |
| `hand_tracking` | `smooth_factor` | 0.45 | Position smoothing (0=none) |
| `hand_tracking` | `frame_skip` | 2 | Process every Nth frame |
| `spray` | `particle_gravity` | 0.15 | Drip effect strength |
| `gameplay` | `combo_timeout` | 2.0 s | Combo window |
| `gameplay` | `time_trial_seconds` | 60 | Time Trial duration |
| `powerup` | `duration` | 6.0 s | Power-up active time |
| `difficulty.*` | various | — | Per-difficulty speed, lives, spawn rate |

---

## 📁 Files

```
hand_pichkari/
├── hand_pichkari.py    # Game script (~1400 lines)
├── settings.json       # External config (all tunable params)
├── highscores.json     # Auto-generated high scores
└── README.md           # This file
```

---

## 🧰 Tech Stack

- **[OpenCV](https://opencv.org/)** — Camera, drawing, display
- **[MediaPipe](https://mediapipe.dev/)** — Hand landmark detection (threaded)
- **[NumPy](https://numpy.org/)** — Polygon & matrix ops
- **[Pygame](https://www.pygame.org/)** *(optional)* — Audio mixer with synthesized WAV tones
- **Python `logging`** — Professional console logging
- **Python `threading`** — Async hand detection & non-blocking sound

---

## 🧠 Technical Challenges

### 1. Real-Time Hand Tracking at High FPS
MediaPipe hand detection is compute-heavy (~30ms per frame). Running it synchronously dropped the game below 20 FPS. **Solution**: Moved detection to a daemon thread with configurable frame-skipping — the main loop reads the latest result without blocking, keeping the display at full camera FPS.

### 2. Gesture Precision
Raw hand landmark positions jump between frames, making the pichkari jittery. **Solution**: Applied an exponential moving average (EMA) filter on the hand midpoint, tunable via `smooth_factor` in `settings.json`.

### 3. Audio Without External Files
The game needed sound effects but shipping `.wav` files is fragile. **Solution**: Programmatically synthesized WAV tones in memory using `struct` + `wave` + `math.sin()`, then loaded them as `pygame.mixer.Sound` objects. No external audio files required.

### 4. Multi-Layered Rendering
Drawing stains, particles, splashes, HUD, and overlays on a live camera feed without flicker required careful layering with `cv2.addWeighted()` for semi-transparency, rendered in a specific back-to-front order.

---

## 📋 Development Phases

| Phase | Focus | Key Deliverables |
|---|---|---|
| **Phase 1: Core Logic** | Hand tracking, pinch detection, target spawning, collision | Working gesture-to-spray pipeline |
| **Phase 2: Gameplay** | Lives, combo, difficulty levels, bomb/gold/frozen targets, power-ups | Complete game mechanics |
| **Phase 3: Visual Polish** | Particles, stains, screen shake, trail, HUD, start/game-over screens | Premium visual experience |
| **Phase 4: Optimization** | Threaded detection, frame-skip, EMA smoothing, external config, logging, pygame audio, time trial | Production-ready game |

---

## 📜 License

This project is open source. Feel free to modify and share!

---

> **Happy Holi! 🎉** Spray responsibly (in-game, at least).
