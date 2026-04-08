# 🎮 ML Learn — Hand-Gesture Game Collection 

A collection of interactive games powered by **computer vision** and **hand tracking**. Each game uses your webcam and [MediaPipe](https://mediapipe.dev/) to turn hand gestures into real-time controls — no keyboard or mouse needed!

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange)

---

## 🕹️ Games

### 🎨 [Hand Pichkari](hand_pichkari/) — Competitive Holi Edition 

A Holi-themed color-spraying game! Aim with your hand, pinch to spray color at floating targets, avoid bombs, collect power-ups, and chase high scores.

| Highlights | |
|---|---|
| **Controls** | Pinch gesture to spray, hand movement to aim |
| **Modes** | 3 difficulty levels + Time Trial |
| **Targets** | Normal, Gold (3×), Frozen (2-hit), Bomb |
| **Power-Ups** | Big Spray, Slow-Mo, Shield |
| **Extras** | Combo system, particle effects, persistent high scores, threaded hand detection |

```bash
cd hand_pichkari
pip install opencv-python mediapipe numpy pygame
python hand_pichkari.py
```

---

### 🏓 [Ping Pong](ping-pong/) — Hand-Tracked Pong

A classic 2D pong game controlled by your index finger. Features adaptive difficulty, combo scoring, and slick visual effects.

| Highlights | |
|---|---|
| **Controls** | Move right hand's index finger to control paddle |
| **Difficulty** | Ball speeds up & paddle shrinks as you score |
| **Effects** | Ball trail, particle explosions, paddle glow |
| **Scoring** | Combo multiplier system |

```bash
cd ping-pong
pip install opencv-python mediapipe numpy
python ping_pong.py
```

---

## 📦 Prerequisites

- **Python 3.8+**
- A working **webcam**
- Core dependencies:
  ```bash
  pip install opencv-python mediapipe numpy
  ```
- Optional (for audio in Hand Pichkari):
  ```bash
  pip install pygame
  ```

---

## 🗂️ Repository Structure

```
ml_learn/
├── hand_pichkari/
│   ├── hand_pichkari.py    # Holi spray game (~1400 lines)
│   ├── settings.json       # External config
│   ├── highscores.json     # Auto-generated scores
│   └── README.md           # Detailed game docs
├── ping-pong/
│   ├── ping_pong.py        # Ping pong game (~550 lines)
│   └── README.md           # Detailed game docs
└── README.md               # This file
```

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| [OpenCV](https://opencv.org/) | Camera capture, drawing, display |
| [MediaPipe](https://mediapipe.dev/) | Real-time hand landmark detection |
| [NumPy](https://numpy.org/) | Array & math operations |
| [Pygame](https://www.pygame.org/) *(optional)* | Audio mixer for sound effects |

---

## 📄 License

This project is open source. Feel free to modify and share!
