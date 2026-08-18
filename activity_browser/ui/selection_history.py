"""Session history of (reference flow, impact category, scenario) combo indices."""

from __future__ import annotations


class IndexSelectionHistory:
    """Back/Forward stack for LCA result-tab combo selections.

    Records ``(fu_index, method_index, scenario_index)`` only. Applying Back
    or Forward must call :meth:`suppress_push` so setting combos does not
    push a duplicate.
    """

    def __init__(self) -> None:
        self._stack: list[tuple] = []
        self._index: int = -1
        self._suppress: bool = False

    def push(self, key: tuple) -> None:
        if self._suppress:
            return
        if self._index >= 0 and self._stack[self._index] == key:
            return
        self._stack = self._stack[: self._index + 1]
        self._stack.append(key)
        self._index = len(self._stack) - 1

    def can_back(self) -> bool:
        return self._index > 0

    def can_forward(self) -> bool:
        return 0 <= self._index < len(self._stack) - 1

    def back(self) -> tuple | None:
        if not self.can_back():
            return None
        self._index -= 1
        return self._stack[self._index]

    def forward(self) -> tuple | None:
        if not self.can_forward():
            return None
        self._index += 1
        return self._stack[self._index]

    def suppress_push(self) -> None:
        self._suppress = True

    def resume_push(self) -> None:
        self._suppress = False

    def seed(self, key: tuple) -> None:
        """Start history at ``key`` (call after combos are populated)."""
        if self._suppress:
            return
        self._stack = [key]
        self._index = 0
