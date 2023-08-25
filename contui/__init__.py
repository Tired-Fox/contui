from __future__ import annotations
from abc import abstractmethod
from collections.abc import Callable
import re
from typing import Literal, TypedDict
from contui.buffer import Buffer, Pixel
from conterm.pretty import Markup

from contui.style import Style

__version__ = "0.1.0"

""" # Ideas

+ Update Loop:
    - Read for input
    - Call user updates
    - Render

+ Nodes:
    - Component:
        - RichText
        - Text
        - Input
        - Select
    - Parent:
        - Window
        - Container 

+ CSS Like styling
+ Hooks
+ Mouse support
+ Hover support (Default off)
"""

""" # Areas to Study

+ CSS Parser
+ Config Parser (TCFG? but upgraded)
+ HTML Parser?? Late game
+ Context managers (builders)
+ Apply css styles to nodes in terms of terminal
+ All nodes are scrolling nodes
"""
Top = Bottom = Left = Right = Inline = Block = int
Percent = float

Size = int | Percent | Callable[[int], int] | Literal['fit-content']
Align = Literal['start', 'center', 'end']
Position = int | tuple[Block, Inline] | tuple[Top, Right, Bottom, Left]

class Properties(TypedDict):
    width: Size
    height: Size
    text_align: Align
    align_items: Align
    padding: Position 
    margin: Position 

class OptionalProperties(TypedDict, total=False):
    width: Size
    height: Size
    text_align: Align
    align_items: Align
    padding: Position 
    margin: Position 

DEFAULTS: OptionalProperties = {
    'width': 1.0,
    'height': 1.0,
    'text_align': "start",
    "align_items": "start",
    "padding": 0,
    "margin": 0
}

def default_properties(origin: OptionalProperties | dict) -> Properties:
    for key, value in DEFAULTS.items():
        origin[key] = origin.get(key, value)
    return origin

class Node:
    style: Properties

    def __init__(self, *, style: OptionalProperties | None = None):
        self.buffer = buffer
        self.style = default_properties(style or {})

    @abstractmethod
    def render(self):
        return NotImplementedError

class Rect:
    __slots__ = ("left", "top", "right", "bottom")
    def __init__(self, left: int = 0, top: int = 0, width: int = 0, height: int = 0):
        self.left = left
        self.top = top
        self.right = self.left + width 
        self.bottom = self.top + height 

    @staticmethod
    def from_buff(buffer: Buffer) -> Rect:
        return Rect(0, 0, buffer.width, buffer.height)

    @property
    def points(self) -> tuple[int, int, int, int]:
        """Top, Right, Bottom, and Left respectively."""
        return (self.top, self.right, self.bottom, self.left)

    @property
    def width(self) -> int:
        """Width of the struct, exclusvie to the `Right` point."""
        return self.right - self.left

    @property
    def height(self) -> int:
        """Height of the struct, exclusvie to the `Bottom` point."""
        return self.bottom - self.top

    def padded(self, padding: Position) -> Rect:
        """Applies padding to the rect.

        Returns
            A copy of the current rect with the padding applied.
        """
        padding = normalize_position(padding)

        rect = Rect(self.left, self.top, self.width, self.height)
        rect.left += calc(padding[3], self.width)
        rect.right -= calc(padding[1], self.width)
        rect.top += calc(padding[0], self.height)
        rect.bottom -= calc(padding[2], self.height)
        return rect

ANSI = re.compile(r"\x1b\[[\d;]+m")

class RichText(Node):
    def __init__(self, text: str="", *, style: OptionalProperties | None = None):
        super().__init__(style=style)
        self.text = Markup.parse(text, mar=False)

    def write(self, *text: str, sep: str = ' '):
        self.text += Markup.parse(*text, sep=sep, mar=False)

    def render(self, rect: Rect, buffer: Buffer):
        """Calculate and render the pixels that are to be drawn into the buffer.

        # Args
            rect (Rect): The writable area in the buffer this node can use.
        """
        if self.buffer is None:
            return

        rect = rect.padded(self.style['padding'])

        _style = Style()
        pixels = []
        previous = 0
        for ansi in ANSI.finditer(self.text):
            if ansi.start() > previous:
                # add all chars with previous style
                pixels.extend(
                    Pixel(c, _style) for c in self.text[previous : ansi.start()]
                )
            _style = Style.from_ansi(ansi.group(0))
            previous = ansi.start() + len(ansi.group(0))
        if previous < len(self.text):
            pixels.extend(Pixel(c, _style) for c in self.text[previous:])

        lines: list[list[Pixel]] = []
        previous = 0
        for i in range(len(pixels)):
            if pixels[i].symbol == "\n":
                lines.append(pixels[previous:i])
                previous = i + 1
        if previous < len(pixels):
            lines.append(pixels[previous:])

        for row, line in zip(
            buffer[rect.top + align(lines, self.style['align_items'], rect.height): rect.bottom],
            lines
        ):
            for pixel, char in zip(
                row[rect.left + align(line, self.style['text_align'], rect.width): rect.right],
                line
            ):
                pixel.set(char.symbol, char.style) 

class Text(Node):
    def __init__(self, text: str="", *, style: OptionalProperties | None = None):
        super().__init__(style=style)
        self.text = text

    def write(self, *text: str, sep: str = ' '):
        self.text += sep.join(text)

    def render(self, rect: Rect, buffer: Buffer):
        """Calculate and render the pixels that are to be drawn into the buffer.

        # Args
            rect (Rect): The writable area in the buffer this node can use.
        """
        if self.buffer is None:
            return

        rect = rect.padded(self.style['padding'])
        pixels: list[list[str]] = [[char for char in line] for line in self.text.strip().split("\n")]

        for row, line in zip(
            buffer[rect.top + align(pixels, self.style['align_items'], rect.height): rect.bottom],
            pixels
        ):
            for pixel, char in zip(
                row[rect.left + align(line, self.style['text_align'], rect.width): rect.right],
                line
            ):
                pixel.set(char, Style()) 

def align(origin: list, alignment: Align, total: int) -> int:
    if alignment == "center":
        remainder = (total - len(origin))
        return  remainder // 2 if remainder > 0 else 0
    elif alignment == "end":
        return total - len(origin)
    return 0

def normalize_position(val: Position) -> tuple[Top, Right, Bottom, Left]:
    """Normalize a positioning style to be a tuple of 4 values."""
    if isinstance(val, tuple):
        if len(val) == 2:
            return (val[0], val[1], val[0], val[1])
        return val
    return tuple(val for _ in range(4))

def calc(val: int | float | Callable[[int], int], total: int) -> int:
    """Calculate the final value based on max size. If the value is an int then it is unchanges.
    If the value is a Percent (float) then the max width is multiplied by the value. Finally, if the
    value is a callable then the max value is passed in and the resulting int is returned.
    """
    if callable(val):
        return val(total)
    elif isinstance(val, float):
        return round(total * val)
    return val

if __name__ == "__main__":
    buffer = Buffer()
    buffer.write()

    rich = RichText('[@243 blue]Hello World!', style={'align_items': 'center', 'text_align': 'center'})
    text = RichText(style={'padding': (1, 2)})
    for _ in range(buffer.height):
        text.write("[243]" + "█"*(buffer.width) + "\n")

    text.render(Rect(0, 0, buffer.width, buffer.height), buffer)
    rich.render(
        Rect(0, 0, buffer.width, buffer.height),
        buffer
    )

    buffer.write()
