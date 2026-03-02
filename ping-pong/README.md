# 🏓  Ping Pong

A 2D ping pong game controlled by **hand gestures** via your webcam. Uses **OpenCV** for video capture and **MediaPipe** for real-time hand tracking — no keyboard or mouse needed!

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Hand Tracking** | Control the paddle with your right hand's index finger |
| **Combo System** | Chain hits for score multipliers (x2, x3, x4…) with color-coded effects |
| **Adaptive Difficulty** | Ball speed increases and paddle shrinks as your score rises |
| **Visual Effects** | Ball trail, particle explosions on hits, paddle glow, and speed bar |
| **Mirrored View** | Camera feed is mirrored for intuitive left/right control |

---

## 📦 Prerequisites

- **Python 3.7+**
- A working **webcam**

### Install Dependencies

```bash
pip install opencv-python mediapipe numpy
```

---

## 🚀 Quick Start

### Option 1 — Shortcut Command (Windows)

If you've added the game to your PATH, simply open any terminal and type:

```bash
pingpong
```

### Option 2 — Run Directly

```bash
py ping_pong.py
```



## 🎮 Controls

| Key / Action | Effect |
|---|---|
| **Move right hand** | Move paddle left / right (index finger tracked) |
| `R` | Restart after game over |
| `Q` | Quit the game |

---

## 🕹️ How to Play

1. **Launch the game** — the webcam feed appears with a start screen.
2. **Show your right hand** to the camera — the game begins automatically.
3. **Move your index finger left/right** to control the paddle at the bottom.
4. **Keep the ball in play** — it bounces off the top and side walls.
5. **Score points** each time the ball hits the paddle. Chain consecutive hits for **combo multipliers**!
6. **Game over** when the ball falls past the paddle. Press `R` to restart.

---

## 📊 HUD Elements

- **Score** — displayed top-left
- **Best Score** — displayed top-right
- **Combo Counter** — appears below the score when chaining hits
- **Speed Bar** — top-right bar showing current ball speed
- **Hand Indicator** — green dot (top-right) = hand detected, red = no hand

---

## ⚙️ Configuration

All game constants are defined at the top of `ping_pong.py` and can be tweaked:

```python
# Ball
BALL_SPEED = 10           # starting speed
BALL_MAX_SPEED = 24       # max speed cap
BALL_SPEED_INCREMENT = 0.6

# Paddle
PADDLE_WIDTH = 130        # starting width
PADDLE_MIN_WIDTH = 70     # minimum width at high scores

# Combo
COMBO_TIMEOUT = 90        # frames before combo resets

# Window
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
```

---

## 🗂️ Project Structure

```
ping-pong/
├── ping_pong.py   # Main game script
├── pingpong.bat               # Windows shortcut to launch the game
└── README.md                  # This file
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `Cannot open webcam` | Check camera connection; close other apps using the camera |
| `'python' is not recognized` | Use `py` instead of `python`, or add Python to your PATH |
| Paddle not responding | Ensure your **right hand** is clearly visible to the camera |
| Laggy tracking | Improve lighting; reduce background clutter |

---

## 📄 License

This project is open source. Feel free to modify and share!
