from __future__ import annotations

from typing import Callable

import numpy as np
import pygame


class SDLDisplay:
    """Preview window. Keys 1..9 call on_key(0..8). Shows full brightness on purpose."""

    def __init__(self, width: int, height: int, scale: int = 2,
                 on_key: Callable[[int], None] | None = None):
        pygame.init()
        self.size = (width * scale, height * scale)
        self.on_key = on_key
        self.window = pygame.display.set_mode(self.size)
        pygame.display.set_caption("Code is Art")
        self.brightness = 1.0

    def push(self, frame: np.ndarray) -> None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise KeyboardInterrupt
            if ev.type == pygame.KEYDOWN and self.on_key is not None and pygame.K_1 <= ev.key <= pygame.K_9:
                self.on_key(ev.key - pygame.K_1)
        surf = pygame.surfarray.make_surface(np.ascontiguousarray(frame.transpose(1, 0, 2)))
        pygame.transform.scale(surf, self.size, self.window)
        pygame.display.flip()

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        pygame.quit()
