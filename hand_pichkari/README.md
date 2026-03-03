# 🎨 Hand Pichkari — Competitive Holi Edition

A hand-gesture controlled Holi game built with **OpenCV** and **MediaPipe**. Spray color at floating targets using a pinch gesture, avoid bombs, collect power-ups, and chase high scores!

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- A working webcam

### Installation

```bash
pip install opencv-python mediapipe numpy
```

### Run

```bash
python hand_pichkari.py
```

Press **SPACE** on the title screen to begin.

---

## 🎮 How to Play

| Action | Gesture / Key |
|---|---|
| **Aim** | Move your hand — the pichkari follows the midpoint of your thumb & index finger |
| **Spray** | Pinch thumb + index finger together |
| **Switch color** | Each new pinch automatically cycles to the next Holi color |
| **Restart** | Press `R` (in-game) or `SPACE` (on Game Over screen) |
| **Quit** | Press `Q` or `ESC` |

---

## 🎯 Targets

| Target | Appearance | Effect |
|---|---|---|
| **Normal** | ⚪ White circle | +1 point × combo. **Costs a life if it escapes!** |
| **Gold** | 🌟 Golden with sparkles | **3× points** × combo |
| **Bomb** | 💣 Black with red pulsing ✕ | **−1 life** if sprayed. Avoid these! |

---

## ⚡ Power-Ups

Power-ups float across the screen — spray them to collect. Each lasts **6 seconds**.

| Power-Up | Label | Effect |
|---|---|---|
| **Big Spray** | `BIG` | 1.8× spray radius + more particles |
| **Slow-Mo** | `SLO` | All targets move at half speed |
| **Shield** | `SHD` | Immune to bomb damage (green ring indicator) |

---

## 📈 Competitive Mechanics

### Lives
You start with **5 lives** (❤️). You lose a life when:
- A **normal target escapes** off-screen without being hit
- You **spray a bomb** (unless shielded)

Game ends at 0 lives.

### Combo System
Hit targets within **2 seconds** of each other to build combos:
- 1st hit → ×1
- 2nd hit → ×2
- 3rd hit → ×3 … and so on!

Missing a target or letting the timer expire resets your combo.

### Progressive Difficulty
Every **8 points** increases the level (max Lv.15):
- Targets spawn **faster** and move **quicker**
- Targets get **smaller**
- **More targets** on screen simultaneously
- Higher chance of **bombs** and **gold** targets

---

## 🎨 Visual Features

- **Mirrored camera feed** as the game background
- **Persistent paint stains** — hit targets leave colorful splatters
- **Screen shake** on impacts and bomb explosions
- **Floating score text** — animated "+3 ×2 GOLD!" on hits
- **Wobbling targets** — some move in sine-wave patterns
- **Particle spray** and **radial splash** effects
- **9 vibrant Holi colors** cycle with each pinch

---

## 🛠️ Configuration

Key settings at the top of `hand_pichkari.py`:

| Setting | Default | Description |
|---|---|---|
| `CAM_WIDTH / CAM_HEIGHT` | 1280 × 720 | Camera resolution |
| `PINCH_THRESHOLD` | 42 px | Pinch sensitivity (lower = harder to trigger) |
| `MAX_LIVES` | 5 | Starting lives |
| `LEVEL_UP_SCORE` | 8 | Points needed per level |
| `COMBO_TIMEOUT` | 2.0 s | Time window to maintain combo |
| `POWERUP_DURATION` | 6.0 s | How long power-ups last |
| `BASE_SPRAY_RADIUS` | 55 px | Normal spray hit radius |

---

## 📁 Project Structure

```
hand_pichkari/
├── hand_pichkari.py   # Complete game script
└── README.md          # This file
```

---

## 🧰 Tech Stack

- **[OpenCV](https://opencv.org/)** — Camera capture, drawing, display
- **[MediaPipe](https://mediapipe.dev/)** — Real-time hand landmark detection
- **[NumPy](https://numpy.org/)** — Array operations for screen shake & polygon drawing

---

## 📜 License

This project is open source. Feel free to modify and share!

---

> **Happy Holi! 🎉** Spray responsibly (in-game, at least).
