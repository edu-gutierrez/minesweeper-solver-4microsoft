# Development notes

This is how the project grew from a board solver into a bot that plays Microsoft Minesweeper. The [README](../README.md) has the setup commands and gameplay recordings; these notes focus on the decisions behind the code.

## Starting with the rules

I started with a matrix rather than the game window. Numbers represented revealed cells, `?` meant unknown, `f` a known mine and `o` a safe cell waiting to be opened. Later I added `m` for a revealed mine, `b` for a hole in the board and `t` for a discovered treasure chest.

The first solver applied the usual neighbor rules: subtract known mines from a clue, then mark the remaining cells safe if no mines are missing, or mark them all as mines if every unknown cell is needed.

That was not enough for overlapping clues. I added subset subtraction: if one group is contained in another, subtracting their mine counts gives a constraint on the difference. Repeating this over newly derived groups lets the solver find moves that a single clue cannot establish.

## Turning a screenshot into a board

The next step was finding the grid with OpenCV. Canny edges and square contours locate the cells; their repeated spacing gives the row and column centers. This also lets the reader reconstruct positions where no tile exists, such as the central holes in daily challenges.

Colors worked well for covered cells and flags, but not for every number. Some digits share colors, so I added recognition of the digit shape. The reader first compares normalized number templates and falls back to Tesseract when the match is uncertain. Revealed mines and treasure chests also have shape templates.

Different board sizes exposed a geometry detail: cell spacing is not always an integer. Alternating gaps of 43 and 44 pixels can really mean a 43.5-pixel step. Fitting the spacing across all detected centers avoided the drift caused by rounding each gap.

During a game, the initial calibration stays fixed. Later detections check that the grid still lines up, using unchanged complete tiles as evidence rather than trusting small shifts in the contour estimate.

## Getting the game loop right

The first live loop read the board after each move. It worked, but spent too much time taking screenshots, waiting for animations and running OCR.

I changed it to execute all known moves in a batch before reading the new board. Openings still need a quick visual check before each click: opening a zero can reveal another planned destination, so that click should be skipped.

The bot also needs to know when the game has ended. Sunglasses on the face provide a quick victory signal; result dialogs confirm wins and losses. Achievement notices can cover or shade part of the board, so the reader waits for them to disappear.

These checks became part of the loop rather than exceptions handled after a bad reading.

## Making recognition faster

Number templates removed much of the repeated OCR work. The next improvement was caching cell readings: if a cell's image and grid coordinates are unchanged, its previous reading can be reused.

The cache only reuses automatic readings with matching pixels and geometry. It does not blindly assume that a revealed cell looks the same forever, because overlays and animations can change its appearance.

Timing measurements helped separate the costs of capture, waiting, grid detection, recognition, deduction and clicks. This made it possible to improve the expensive parts without guessing where the time was going.

A zero click delay looked attractive, but the game missed some clicks. I settled on 0.1 seconds for the daily controller and kept the delay configurable.

## Reasoning beyond local rules

Some positions need more than subset subtraction. I added a binary constraint solver through SciPy/HiGHS: each unknown cell is either a mine or safe, and each clue becomes an equation. To prove a cell's value, the solver tries the opposite assumption and checks whether any compatible arrangement exists.

When a guess is needed, the probability code counts compatible arrangements conditioned on the total number of mines. It splits independent components, groups cells that affect the same clues and caches repeated states. The groups need combinatorial weights: choosing two mines among four equivalent cells represents six arrangements, not one.

The original limit of 100 cells per component became unnecessary after grouping. Removing it let a previously blocked component of 159 cells be counted exactly in about 0.20 seconds on the saved test board. That is a measurement of one calculation, not a whole game.

Exact counting still has time and state budgets. If those are exhausted, the bot can estimate a guess from feasible arrangements found using random optimization objectives. Those samples are not uniform, so their frequencies are only a heuristic. They never produce confirmed flags or safe moves.

## Giving each challenge its own rules

The five modes share recognition and deduction, but their actions differ:

- **Classic:** open safe cells, flag mines and optionally guess.
- **Flags:** place only confirmed flags, up to the target. Safe deductions stay in memory.
- **Taps:** open only safe cells, without flags. Cascades and clicks on mines do not count as successful openings.
- **Treasure Hunt:** look for the chest surrounded by mines. Mine rings influence guesses only when there are no safe openings, with a more conservative choice on the last life.
- **Detonation:** click confirmed mines in batches, then use the highest mine probability when a guess is needed. Track mines and available moves separately.

Keeping these restrictions in the plan builder prevents the shared solver from sending a valid Minesweeper move that is forbidden by the current challenge.

## Checking that clicks happened

Sending a click does not prove that the game registered it. The bot reads the result and checks each planned action.

Missing flags and confirmed openings can be retried once after a fresh visual check. Confirmed detonations also need their move budget reconciled with the on-screen counter. The retry must not count a successful action twice.

Guesses are handled differently: the bot waits and recaptures if the destination still looks covered, but does not click it again. Each recovery has a limit, and unresolved verification failures stop the run.

## Moving between challenges

The daily controller recognizes the five colored cards and the blue completion medals. It opens unfinished challenges from left to right, waits for video ads, presses the verified close button, handles the instructions and starts the player with fresh memory.

After a confirmed win it presses Continue and checks that the card received its medal. After a confirmed defeat it follows the retry flow. Solver problems stop the controller instead of being treated as defeats.

Once all five cards are complete, it advances with the right arrow. The stopping rule is the one I chose for this project: stop if the first card of the next day is already completed. A separate day limit can shorten a run.

Transitions need patience too. The old screen can remain visible after a click, and the board can briefly appear before the instruction panel. The controller waits for the expected screen rather than starting the solver on the first visible frame.

## Testing without moving the mouse

The game loop and daily controller accept capture, click and window-check adapters. Tests can therefore simulate delayed screens, missed clicks, cascades, wins and losses without controlling the computer.

Saved board fixtures cover difficult constraint and probability cases. Small boards are also compared against exhaustive enumeration to check that the exact probabilities have the right weights.

The gameplay GIFs in the README show the real application. The tests cover the reasoning and interaction logic; they do not replace testing recognition against actual screenshots.
