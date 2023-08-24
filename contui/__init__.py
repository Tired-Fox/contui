from __future__ import annotations
from abc import abstractmethod
from collections.abc import Callable
from typing import Literal, TypedDict
from contui.buffer import Buffer
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
Size = int | float | Callable[[int], int] | Literal['fit-content']

class Properties(TypedDict, total=False):
    width: Size
    height: Size

DEFAULTS = {
    'width': 1.0,
    'height': 1.0
}

def default_properties(origin: Properties | dict) -> Properties:
    for key, value in DEFAULTS.items():
        origin[key] = origin.get(key, value)
    return origin

class Node:
    style: Properties

    def __init__(self, *, style: Properties | None = None):
        self.buffer = buffer
        self.style = default_properties(style or {})

    @abstractmethod
    def render(self):
        return NotImplementedError

class Rect:
    __slots__ = ("left", "top", "right", "bottom")
    def __init__(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    @staticmethod
    def from_buff(buffer: Buffer) -> Rect:
        return Rect(0, 0, buffer.width, buffer.height)

    @property
    def points(self) -> tuple[int, int, int, int]:
        """Left, Top, Right, and Bottom respectively."""
        return (self.left, self.top, self.right, self.bottom)

    @property
    def width(self) -> int:
        """Width of the struct, exclusvie to the `Right` point."""
        return self.right - self.left

    @property
    def height(self) -> int:
        """Height of the struct, exclusvie to the `Bottom` point."""
        return self.right - self.left

class Text(Node):
    def __init__(self, *, style: Properties | None = None):
        super().__init__(style=style)
        self.text = "" 

    def write(self, *text: str, sep: str = ' '):
        if self.text != "":
            self.text += sep
        self.text += sep.join(text)

    def render(self, rect: Rect, buffer: Buffer):
        """Calculate and render the pixels that are to be drawn into the buffer.

        # Args
            rect (Rect): The writable area in the buffer this node can use.
        """
        if self.buffer is None:
            return

        pixels: list[str] = [line for line in Markup.strip(self.text).split("\n")]

        for row, line in zip(buffer[rect.top: rect.bottom], pixels):
            for pixel, char in zip(row[rect.left: rect.right], line):
                pixel.set(char, Style()) 

if __name__ == "__main__":
    buffer = Buffer()

    text = Text()
    text.write('Hello World')
    text.render(Rect(buffer.width//4, buffer.height//4, int(buffer.width*.75), int(buffer.height*.75)), buffer)

    buffer.write()
