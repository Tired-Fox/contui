from __future__ import annotations

from copy import deepcopy
from sys import stdout
from os import get_terminal_size
from typing import Generator, overload

from contui.style import Style

__all__ = ["Buffer"]

def _write(content: str):
    stdout.write(content)
    stdout.flush()

class Pixel:
    """A unicode symbol and it's ansi sequence styling."""

    __slots__ = ("symbol", "style")

    def __init__(self, symbol: str, style: Style):
        self.symbol = symbol
        self.style = deepcopy(style)

    def set(self, symbol: str, style: Style | None = None):
        self.symbol = symbol
        if style is not None:
            self.style = style

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, Pixel):
            return self.symbol == __value.symbol and self.style == __value.style
        return False

    def __repr__(self) -> str:
        return repr(f"{self.style}{self.symbol}\x1b[0m")

    def __str__(self) -> str:
        return f"{self.style}{self.symbol}\x1b[0m"


class Buffer:
    """A terminal buffer that overwrites to a rect of the terminal.

    Args
        width (int | None): The width of the buffer. Defaults to terminal width.
        height (int | None): The height of the buffer. Defaults to terminal height.
        default (str): The char to use for each pixel by default. Defaults to `''` (empty str)
    """

    __slots__ = ("__BUFFER__", "__CACHE__", "_width_", "_height_", "_default_")

    def __init__(
        self, width: int | None = None, height: int | None = None, default: str = " "
    ) -> None:
        (cols, lines) = get_terminal_size()

        self._width_ = width or cols
        self._height_ = height or lines
        self._default_ = default

        self.__BUFFER__: list[list[Pixel]] = [
            [Pixel(default, Style()) for _ in range(self._width_)]
            for _ in range(self._height_)
        ]
        self.__CACHE__ = []

    @property
    def width(self) -> int:
        """Current width of the buffer."""
        return self._width_

    @property
    def height(self) -> int:
        """Current height of the buffer."""
        return self._height_

    def resize(self, width: int | None = None, height: int | None = None):
        """Resize the buffer to the specified size. Can omit width or height to not change that dimension.

        Args
            width (int | None): The width to update the buffer too. Defaults to the current buffer width.
            height (int | None): The height to update the buffer too. Defaults to the current buffer height.
        """
        # PERF: Ensure that write or a render is called after resize. This will clear the screen
        self.clear()
        width = width or self._width_
        height = height or self._height_

        if height > self._height_:
            self.__BUFFER__.extend(
                [
                    [Pixel(self._default_, Style()) for _ in range(self._width_)]
                    for _ in range(height - self._height_)
                ]
            )
        elif height < self._height_:
            self.__BUFFER__ = self.__BUFFER__[:height]

        if width > self._width_:
            for row in range(len(self.__BUFFER__)):
                self.__BUFFER__[row].extend(
                    [Pixel(self._default_, Style()) for _ in range(self._width_)]
                )
        elif width < self._width_:
            for row in range(len(self.__BUFFER__)):
                self.__BUFFER__[row] = self.__BUFFER__[row][:width]

        self._width_ = width
        self._height_ = height

    def clear(self):
        """Clears the screen, cache, and buffer."""
        self.__CACHE__.clear()
        self.__reset__()
        _write("\x1b[2J")

    def cache(self):
        """Cache the current buffer state."""
        self.__CACHE__ = deepcopy(self.__BUFFER__)

    def render(self) -> str:
        """Calculate what pixels should be drawn. Only the changed pixels are rendered.

        Returns
            The ansi sequences and characters in a single string to render the entire buffer.
        """

        # List of formatted pixels to render
        result = ""

        if len(self.__CACHE__) != len(self.__BUFFER__):
            for i, row in enumerate(self.__BUFFER__):
                for j, col in enumerate(row):
                    result += f"\x1b[{i+1};{j+1}H{col}"

        for i, (br, sr) in enumerate(zip(self.__BUFFER__, self.__CACHE__)):
            if len(br) != len(sr):
                result += "".join(f"\x1b[{i+1};{j+1}H{p}" for j, p in enumerate(br))
            else:
                for j, (bp, sp) in enumerate(zip(br, sr)):
                    if bp != sp:
                        result += f"\x1b[{i+1};{j+1}H{bp}"

        return result

    def write(self, cursor: tuple[int, int] | None = None):
        """Render the buffer and write it to stdout. When finished the current buffer state is cached."""
        bsize = len(self.__BUFFER__)
        final = (
            f"\x1b[{bsize};{len(self.__BUFFER__[0]) if bsize > 0 else 0}H"
            if cursor is None
            else f"\x1b[{cursor[0]};{cursor[1]}H"
        )
        _write(f"{self.render()}{final}\x1b[0m")
        self.cache()

    def sub(self, x: int, y: int, w: int, h: int) -> Buffer:
        x = max(0, min(x, self.width))
        y = max(0, min(y, self.height))
        w = max(0, min(w, self.width - x))
        h = max(0, min(h, self.height - y))

        buffer = Buffer()
        buffer._default_ = self._default_
        buffer.__BUFFER__ = [
            [self.__BUFFER__[r][p] for p in range(x, x+w)]
            for r in range(y, y+h)
        ]
        buffer._width_ = w
        buffer._height_ = h
        return buffer

    @overload
    def __getitem__(self, key: int) -> list[Pixel]:
        ...

    @overload
    def __getitem__(self, key: slice) -> list[list[Pixel]]:
        ...

    def __getitem__(self, key: int | slice) -> list[Pixel] | list[list[Pixel]]:
        return self.__BUFFER__[key]

    def __iter__(self) -> Generator[list[Pixel], None, None]:
        yield from self.__BUFFER__

    def __len__(self) -> int:
        return len(self.__BUFFER__)

    def __repr__(self) -> str:
        return repr(self.__BUFFER__)

    def __str__(self) -> str:
        if len(self.__BUFFER__) > 0:
            result = "".join(str(p) for p in self.__BUFFER__[0])
            for row in self.__BUFFER__[1:]:
                result += f"\n{''.join(p.symbol for p in row)}"
            return result
        return ""

    def __reset__(self):
        """Reset all pixels in the buffer to the default symbol and styling."""
        for row in range(len(self.__BUFFER__)):
            for col in range(len(self.__BUFFER__[row])):
                self.__BUFFER__[row][col].set(self._default_, Style())

