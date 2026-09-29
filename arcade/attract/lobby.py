"""The small lobby (spec 7.3 steps 1 to 4 and 7), the minimum until M8's attract director: a runner.LobbyLike.

Modes, one per tick (MODES):

- attract, nobody near: the featured game's title, centred, static and dim; nothing when none fits.
- mirror: the locked player's figure (and player 2's) in its colour, from the tick the runner locks them.
- invite, after PICTOGRAM_SECONDS near: the HAND_UP pictogram breathes beside the player's figure.
- card, for CARD_SECONDS after a session: the result, "BEST!" when the session raised tonight's best
  (SessionResult.new_best) with a score above 0, then "HAND UP = AGAIN" or "NEXT: RAISE A HAND".

On a wall at least BIG_ROWS tall the title, the card's head line and "BEST!" are drawn at BIG_SCALE where each
fits the width on one line; everything else, and everything on a shorter wall, at 1x in lines that fit.

A raised hand (the player's rising edge) in mirror or invite requests the featured game: the first MENU_ORDER
name among the lobby's games that is available, fits the layout and needs only inputs the sources give. The edge
is primed on a newly locked player and at the end of the card, so a hand already up never starts a game by
itself; it has to come down and go up again. Blobs and the body centre never start anything.

A player who drops out for up to capture_grace(cfg.camera_fps) keeps their figure and the invite, so a missed
capture never flickers the mode; a keypoint that drops out keeps its last place as long (KeypointHold, C37), so
a missed joint never blinks a limb. A figure's column (figure_rect's) keeps COLUMN_SLACK px of play, so zone_x
jitter never steps the whole figure a column and back (on the widest wall it did most captures). The lobby's own
drawing keeps the flash rule: mode changes are single steps, the pictogram breathes at 1 Hz, and nothing fills
the field.
"""
from __future__ import annotations

import math
from typing import Sequence

from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.figure import KeypointHold, draw_figure, figure_rect, to_wall
from arcade.game import INPUTS, ICON_SIZE, icon_from_rows
from arcade.games import MENU_ORDER
from arcade.input import EPSILON, Edge, Hold, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import MIN_CONF, Body, Sensed
from show.font import CELL_H

PICTOGRAM_SECONDS = 1.5      # near this long before the pictogram (spec 7.3 step 3)
BREATH_HZ = 1.0              # the pictogram's breath
BREATH_LOW = 0.4             # its light at the bottom of a breath, a share of PICTOGRAM_COLOR
CARD_SECONDS = 3.0           # the end card
TITLE_COLOR = (120, 60, 0)   # dim amber: the attract title
TEXT_COLOR = (255, 160, 0)   # the card
PICTOGRAM_COLOR = (0, 200, 0)
GAP = 2                      # px between the figure and the pictogram
COLUMN_SLACK = 1             # px a figure's column may jitter without moving it
BIG_ROWS = 48                # a wall at least this tall draws the lobby's big text at 2x
BIG_SCALE = 2
MODES = ("attract", "mirror", "invite", "card")

HAND_UP = icon_from_rows([
    "............##..",
    "......##....##..",
    ".....####...##..",
    ".....####...##..",
    "......##....##..",
    "............##..",
    "...###########..",
    "...###########..",
    "...##.##........",
    "...##.##........",
    "...##.##........",
    "......##........",
    "....##..##......",
    "....##..##......",
    "...##....##.....",
    "...##....##.....",
])


def _lines(text: str, width: int, canvas: Canvas, scale: int = 1) -> list[str]:
    """text in lines that fit width at scale, split between words, and inside a word too long for a line."""
    per_line = max(1, width // canvas.text_width("M", scale))
    lines: list[str] = []
    for word in text.split():
        while len(word) > per_line:
            lines.append(word[:per_line])
            word = word[per_line:]
        if lines and canvas.text_width(lines[-1] + " " + word, scale) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def _big(text: str, canvas: Canvas) -> list[tuple[str, int]]:
    """text as (line, scale): one line at BIG_SCALE on a wall at least BIG_ROWS tall where it fits the width,
    else in lines at 1x."""
    if canvas.height >= BIG_ROWS and canvas.text_width(text, BIG_SCALE) <= canvas.width:
        return [(text, BIG_SCALE)]
    return [(line, 1) for line in _lines(text, canvas.width, canvas)]


def _centred(canvas: Canvas, lines: list[tuple[str, int]], color) -> None:
    """(text, scale) per line, drawn as one block centred on the canvas."""
    y =(canvas.height - CELL_H * sum(scale for _, scale in lines)) // 2
    for text, scale in lines:
        canvas.text((canvas.width - canvas.text_width(text, scale)) // 2, y, text, color, scale)
        y += CELL_H * scale


def _score(score: float) -> str:
    return f"{score:.0f}" if float(score).is_integer() else f"{score:.1f}"


class Lobby:
    """spec 7.3's walk-up flow for the games given (classes), before M8. See the module docstring."""

    info = None

    def __init__(self, games: Sequence[type], cfg: ArcadeConfig):
        self.games = {g.info.name: g for g in games}
        self.cfg = cfg
        self.grace = capture_grace(cfg.camera_fps)
        self.request: str | None = None
        self._available: set[str] = set()
        self._inputs: set[str] = set(INPUTS)         # every input until set_status: headless runs never sense()
        self.reset(cfg.size, None)

    # ----- the runner's notices -----

    def set_available(self, names) -> None:
        self._available = set(names)

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs, calibrated: bool) -> None:
        self._inputs = set(inputs)

    def end_session(self, result) -> None:
        """Show result's card from the next update; what was seen before the session is stale."""
        self._card, self._card_start = result, None
        self._slots = [None, None]
        self._keypoints = [KeypointHold(self.grace), KeypointHold(self.grace)]
        self._hold.reset()
        self._side = None

    def featured(self) -> str | None:
        """The first MENU_ORDER name among the games that is available, lists the layout and needs only the
        inputs the sources give; None when none fits."""
        for name in MENU_ORDER:
            game = self.games.get(name)
            if (game is not None and name in self._available and self.cfg.layout in game.info.layouts
                    and game.info.needs <= self._inputs):
                return name
        return None

    # ----- the Game side -----

    def reset(self, size, rng, fx=None) -> None:
        self.size = tuple(size)
        self.t = 0.0
        self.request = None
        self._slots: list[tuple[Body, float, int] | None] = [None, None]   # (body, last seen, rect x): player, player2
        self._keypoints = [KeypointHold(self.grace), KeypointHold(self.grace)]   # C37: one per figure
        self._hold = Hold(PICTOGRAM_SECONDS, grace=self.grace)
        self._edge = Edge(self.grace)
        self._player_id: int | None = None
        self._card = None
        self._card_start: float | None = None
        self._pictogram_since: float | None = None
        self._side: int | None = None                 # the pictogram's side of the figure: -1 left, 1 right
        self._icon_at: tuple[int, int] | None = None

    def update(self, sensed: Sensed, dt: float) -> None:
        t = self.t = sensed.t
        player = sensed.player
        raised = player is not None and player.raised_wrist is not None
        card_ended = False
        if self._card is not None:
            if self._card_start is None:
                self._card_start = t
            elif t - self._card_start >= CARD_SECONDS - EPSILON:
                self._card, self._card_start, card_ended = None, None, True
        for i, body in enumerate((player, sensed.player2)):
            held = self._keypoints[i].update(body, t)
            if held is not None:
                x, slot = figure_rect(held, self.size)[0], self._slots[i]
                if slot is not None and slot[0].id == held.id:              # the same person: x with backlash
                    x = min(max(slot[2], x - COLUMN_SLACK), x + COLUMN_SLACK)
                self._slots[i] = (held, t, x)
        self._hold.update(player is not None, t)
        if player is not None and player.id != self._player_id:
            self._player_id = player.id
            fired = self._prime(raised, t)
        elif card_ended:
            fired = self._prime(raised, t)
        else:
            fired = self._edge.update(raised, t)
        if fired and self.mode in ("mirror", "invite"):
            self.request = self.featured()
        self._place_pictogram(t)

    def draw(self, canvas: Canvas) -> None:
        mode = self.mode
        if mode == "card":
            self._draw_card(canvas)
        elif mode == "attract":
            name = self.featured()
            if name is not None:
                _centred(canvas, _big(self.games[name].info.title, canvas), TITLE_COLOR)
        else:
            for body, color in zip(self._figures(), PLAYER_COLORS):     # player 2 is drawn over player 1
                if body is not None:
                    draw_figure(canvas, body, self._rect(body), color)
            if self._icon_at is not None:
                canvas.blit(HAND_UP, *self._icon_at, self._breath_color())

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        card, mode = self._card, self.mode
        shown = self._figures() if mode in ("mirror", "invite") else [None, None]
        return {"mode": mode, "near": round(self._near(), 3), "pictogram": self._icon_at is not None,
                "figures": sum(b is not None for b in shown), "featured": self.featured(),
                "card_game": None if card is None else card.game,
                "card_score": None if card is None else card.score,
                "card_reason": None if card is None else card.reason,
                "card_waiting": None if card is None else card.waiting,
                "figure_xy": None if shown[0] is None else self._head(shown[0]),
                "pictogram_xy": None if self._icon_at is None else (self._icon_at[0] + ICON_SIZE // 2,
                                                                     self._icon_at[1] + ICON_SIZE // 2)}

    # ----- inside -----

    @property
    def mode(self) -> str:
        if self._card is not None:
            return "card"
        if self._figures()[0] is None:
            return "attract"
        return "invite" if self._hold.fired else "mirror"

    def _prime(self, value: bool, t: float) -> bool:
        """A new edge that has already seen value: a hand up now fires only after it comes down and up again."""
        self._edge = Edge(self.grace)
        self._edge.update(value, t)
        return False

    def _figures(self) -> list[Body | None]:
        """The player's and player 2's bodies, each kept for up to grace after it was last seen."""
        return [None if slot is None or self.t - slot[1] > self.grace + EPSILON else slot[0]
                for slot in self._slots]

    def _rect(self, body: Body) -> tuple[int, int, int, int]:
        """figure_rect(body, size) at its slot's held x (COLUMN_SLACK): body is one _figures() gave."""
        x = next(slot[2] for slot in self._slots if slot is not None and slot[0] is body)
        _, y, w, h = figure_rect(body, self.size)
        return x, y, w, h

    def _near(self) -> float:
        start = self._hold.start
        return 0.0 if start is None else self.t - start

    def _head(self, body: Body) -> tuple[int, int]:
        f = to_wall(body, self._rect(body))
        if body.nose.conf >= MIN_CONF:
            return f(body.nose.x, body.nose.y)
        x0, y0, x1, _ = body.box
        return f((x0 + x1) / 2, y0)

    def _place_pictogram(self, t: float) -> None:
        """Where HAND_UP goes this tick: beside the player's figure, level with its shoulders, on the side with
        more room when it appears; it keeps that side until there is no room there and room on the other."""
        body = self._figures()[0]
        if self.mode != "invite" or body is None:
            self._icon_at, self._side, self._pictogram_since = None, None, None
            return
        if self._pictogram_since is None:
            self._pictogram_since = t
        w, h = self.size
        f = to_wall(body, self._rect(body))
        x0, y0, x1, y1 = body.box
        left, right = f(x0, y0)[0], f(x1, y0)[0]
        room = {-1: left - GAP, 1: w - 1 - right - GAP}
        if self._side is None:
            self._side = 1 if room[1] >= room[-1] else -1
        elif room[self._side] < ICON_SIZE <= room[-self._side]:
            self._side = -self._side
        x = right + 1 + GAP if self._side == 1 else left - GAP - ICON_SIZE
        s = body.shoulder_mid
        y = (f(s.x, s.y)[1] if s is not None else h // 2) - ICON_SIZE // 2
        self._icon_at = (max(0, min(w - ICON_SIZE, x)), max(0, min(h - ICON_SIZE, y)))

    def _breath_color(self) -> tuple[int, int, int]:
        """PICTOGRAM_COLOR at BREATH_LOW when the pictogram appears, rising to full and back once a second."""
        phase = 2 * math.pi * BREATH_HZ * (self.t - self._pictogram_since)
        light = BREATH_LOW + (1.0 - BREATH_LOW) * (0.5 - 0.5 * math.cos(phase))
        return tuple(c * light for c in PICTOGRAM_COLOR)

    def _draw_card(self, canvas: Canvas) -> None:
        r = self._card
        game = self.games.get(r.game)
        title = game.info.title if game is not None else str(r.game).upper()
        head = title if r.score is None else f"{title} {_score(r.score)}"
        lines = _big(head, canvas)
        if r.new_best and r.score is not None and r.score > 0:     # C43, Q41: tonight's best rose, above 0
            lines += _big("BEST!", canvas)
        prompt = "NEXT: RAISE A HAND" if r.waiting else "HAND UP = AGAIN"
        lines += [(line, 1) for line in _lines(prompt, canvas.width, canvas)]
        _centred(canvas, lines, TEXT_COLOR)
