# Microsoft Minesweeper Solver

> *Read this in [Spanish](README_es.md)*

A Python bot that plays **Microsoft Minesweeper on Windows** by reading the screen, reasoning about the board and controlling the mouse.

I started this project to combine Minesweeper logic with computer vision. It grew from a solver for manually entered boards into a player for all five daily challenge modes, with an automatic controller that moves between challenges and days.

Developed with **AI as a programming assistant**. The reasoning uses known Minesweeper rules, constraint solving and probability calculations; no neural network is required.

## Gameplay

### Classic

Reveals safe cells, flags confirmed mines and chooses a low-risk guess when deduction is exhausted.

> **GIF coming soon:** `Media/classic.gif`

<!-- Replace the line above with this block when the GIF is available:
<div align="center">
<img src="Media/classic.gif" alt="Bot solving a classic Minesweeper board" width="900">
</div>
-->

### Daily Challenges

Five modes, each with its own objective and allowed actions:

| Mode | What the bot does | GIF slot |
| --- | --- | --- |
| **Flags** | Places only deduced flags, up to the target. | `Media/flags.gif` |
| **Detonation** | Clicks confirmed mines; otherwise chooses the highest estimated mine probability. | `Media/detonation.gif` |
| **Classic** | Opens safe cells and flags mines. | `Media/classic.gif` |
| **Treasure Hunt** | Searches for treasure; considers mine rings only when no safe opening exists, using the remaining lives. | `Media/treasure.gif` |
| **Taps** | Makes safe openings without placing flags; counts only successful clicks. | `Media/taps.gif` |

> **Automatic daily run GIF coming soon:** `Media/daily-challenges.gif`

<!-- Uncomment when available:
<div align="center">
<img src="Media/daily-challenges.gif" alt="Bot completing challenges and moving to the next day" width="900">
</div>
-->

See [Media/README.md](Media/README.md) for the other ready-to-use GIF blocks.

---

## Main Features

* **Screen Reading:** OpenCV detects the grid and cell states. Number templates provide fast recognition, with Tesseract OCR as a fallback.
* **Logical Deduction:** Neighbor rules, subset subtraction and binary constraint solving identify certain moves.
* **Exact Probabilities:** Equivalent cells are grouped, intermediate states are cached and solutions are weighted by the total mine count.
* **Approximate Guesses:** When exact counting exceeds its budget, compatible configurations provide a bounded heuristic for guessing. These estimates never become certain moves.
* **Five Game Modes:** Separate objectives, counters and click restrictions for daily challenges.
* **Daily Navigation:** Opens unfinished cards from left to right, handles instructions and video ads, confirms wins and retries confirmed losses.
* **Verification and Recovery:** Checks actions against new captures, waits for delayed results and retries missing confirmed actions once.
* **Diagnostics:** Saves screenshots, readings, plans, probabilities, navigation events and timing measurements.

## How It Works

```text
Screenshot → Grid detection → Cell recognition → Deduction
                                                    ↓
                                  Certainty search / probabilities
                                                    ↓
                                     Mouse actions → Verification
```

Each number constrains its neighboring cells. For example, if `{A, B}` contains one mine and `{A, B, C}` also contains one mine, then `C` is safe. When these rules stop making progress, the solver tries to prove certainty by checking whether the opposite assumption is impossible.

Exact probabilities count compatible mine arrangements, including the initial total. The approximate fallback samples feasible arrangements through random optimization objectives. **This sampling is not uniform:** its frequencies are a guessing heuristic, not calibrated probabilities or proofs.

The bot executes known moves in batches and reuses unchanged cell readings. It waits for animations and achievement overlays before analyzing the next board.

## Installation

Requires **Windows**, **Python 3.10+**, Microsoft Minesweeper and **Tesseract OCR** installed separately. The bot checks the usual Windows location, `C:\Program Files\Tesseract-OCR\tesseract.exe`, as well as the executable search path.

From the repository directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Dependencies: OpenCV, NumPy, SciPy/HiGHS, pytesseract and PyAutoGUI.

## Run

### One Game

Open a game, run the command and bring Minesweeper to the foreground during the five-second countdown:

```powershell
python live.py --execute --loop --guess --click-delay 0.1 --output "..\live-game"
```

Omit `--guess` to stop when no certain permitted move is available. Omit `--execute` and `--loop` to inspect a plan without clicking.

### Daily Challenge Controller

Start on the **daily challenges panel**:

```powershell
python complete_challenges.py --execute --click-delay 0.1 --max-days 30 --output "..\daily-run"
```

Select September 1 manually to start a September run. `--max-days 30` limits the run to thirty processed day panels; it does not select dates. Already completed cards are skipped. After finishing a day, the bot advances with the right arrow and stops if the first card of the next day is already completed. Solver errors also stop the run.

Omit `--max-days` for no explicit day limit. Add `--no-guess` to disable guesses. Without `--execute`, the controller only inspects the panel.

Keep the game in the foreground and the window position unchanged. Move the mouse to a screen corner to trigger PyAutoGUI's fail-safe, or press `Ctrl+C` in the terminal to interrupt the process.

## Structure

| Files | Responsibility |
| --- | --- |
| `solver.py`, `certainty.py` | Deduction and certainty proofs |
| `probability.py`, `approximate_probability.py` | Exact counting and approximate guesses |
| `vision.py`, `ocr.py`, `*_templates.py` | Grid and cell recognition |
| `live.py`, `actions.py` | Game loop and mouse actions |
| `treasure.py`, `flags_mode.py`, `detonation.py` | Mode rules and counters |
| `daily.py`, `daily_vision.py`, `complete_challenges.py` | Daily navigation and entry point |
| `*_recovery.py`, `delayed_guess.py` | Action recovery and delayed verification |
| `tests/`, `assets/` | Tests, fixtures and recognition templates |

## Validation and Limitations

The automated suite has **203 tests** covering deduction, probability counting, recognition, mode rules, recovery and navigation with simulated input. Run it with:

```powershell
python -m unittest discover -s tests -v
```

The bot has been exercised on all five modes and several board sizes, including 9×9, 16×16 and 30×16. A complete uninterrupted monthly run has not yet been validated. Other themes, display scaling and occlusions can require recognition adjustments.

Guesses can lose games, and approximate estimates are biased. Confirmed losses can be retried by the daily controller; uncertain readings and solver/verification failures stop it for inspection. A click delay of `0.1` seconds has been more reliable than zero in real tests.

Detailed implementation notes and previous measurements are in [docs/development-notes.md](docs/development-notes.md). They record the project's development history and may describe earlier behavior.
