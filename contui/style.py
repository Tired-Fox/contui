from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from functools import cache
from typing import Literal
from typing_extensions import TypeAliasType

__all__ = ["Color", "Style", "S", "ColorFormat"]

ColorFormat = TypeAliasType(
    "ColorFormat",
    tuple[int, int, int]
    | int
    | Literal["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    | str,
)


@dataclass
class Color:
    """Helper class to get color ansi sequences."""

    Black = "0"
    Red = "1"
    Green = "2"
    Yellow = "3"
    Blue = "4"
    Magenta = "5"
    Cyan = "6"
    White = "7"

    @staticmethod
    def new(color: ColorFormat) -> str:
        if isinstance(color, tuple) and len(color) == 3:
            return Color.rgb(*color)
        elif isinstance(color, int):
            return Color.xterm(color)
        elif isinstance(color, str) and color in [
            "black",
            "red",
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
            "white",
        ]:
            return getattr(Color, f"{color[0].upper()}{color[1:]}")
        else:
            return Color.hex(color)

    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        return f"8;2;{r};{g};{b}"

    @staticmethod
    def xterm(code: int) -> str:
        return f"8;5;{code}"

    @staticmethod
    def hex(code: str) -> str:
        code = code.lstrip("#")
        if len(code) not in [3, 6]:
            raise Exception("Hex value must be 3 or 6 digits")

        if len(code) == 3:
            code = f"{code[0]*2}{code[1]*2}{code[2]*2}"

        return f"8;2;{int(code[0:2], 16)};{int(code[2:4], 16)};{int(code[4:6], 16)}"


class Ansi(Enum):
    Bold = 1
    Dim = 2
    Italic = 3
    Underline = 4
    Blink = 6
    Reverse = 7
    Strike = 9
    U_Bold = 22
    U_Dim = 22
    U_Italic = 23
    U_Underline = 24
    U_SBlink = 25
    U_RBlink = 25
    U_Blink = 25
    U_Reverse = 27
    U_Strike = 29

    @staticmethod
    def from_int(value: int):
        if value == 1:
            return Ansi.Bold
        elif value == 2:
            return Ansi.Dim
        elif value == 3:
            return Ansi.Italic
        elif value == 4:
            return Ansi.Underline
        elif value == 6:
            return Ansi.Blink
        elif value == 7:
            return Ansi.Reverse
        elif value == 9:
            return Ansi.Strike
        return Ansi.Bold


class S(Enum):
    """Helper enum for ansi sequence styling."""

    Bold = 1 << 0
    Dim = 1 << 1
    Italic = 1 << 2
    Underline = 1 << 3
    Blink = 1 << 4
    Reverse = 1 << 5
    Strike = 1 << 6
    # U_Bold = 1 << 7
    # U_Dim = 1 << 8
    # U_Italic = 1 << 9
    # U_Underline = 1 << 10
    # U_SBlink = 1 << 11
    # U_RBlink = 1 << 12
    # U_Blink = 1 << 13
    # U_Reverse = 1 << 14
    # U_Strike = 1 << 15


class Style:
    """Helper class to compose ansi sequence styles into a single ansi sequence."""

    def __init__(
        self, *styles: S, fg: str | None = None, bg: str | None = None
    ) -> None:
        # Pack styles into single int value
        self.fg = f";3{fg}" if fg is not None else ""
        self.bg = f";4{bg}" if bg is not None else ""
        self.style = 0
        for style in styles:
            self.style |= style.value

    def __hash__(self) -> int:
        return (
            self.style + (1 if self.fg != "" else 0)
            << 16 + (1 if self.bg != "" else 0)
            << 17
        )

    @staticmethod
    def from_ansi(sequence: str) -> Style:
        style = Style()
        sequence = sequence.lstrip("\x1b[").rstrip("m")
        codes = [int(code) for code in sequence.split(";")]

        # Bold = 1
        # Dim = 2
        # Italic = 3
        # Underline = 4
        # Blink = 6
        # Reverse = 7
        # Strike = 9
        i = 0
        while i < len(codes):
            code = codes[i]
            if code < 10 and code > 0 and code != 8:
                style.style |= S[Ansi.from_int(code).name].value
            elif code > 29 and code < 38:
                style.fg = str(code)
            elif code > 39 and code < 48:
                style.bg = str(code)
            elif code in [38, 48]:
                if code < 40:
                    t = lambda val: setattr(style, "fg", f";3{val}")
                else:
                    t = lambda val: setattr(style, "bg", f";4{val}")

                if i + 1 >= len(codes):
                    raise ValueError(
                        f"Missing special ansi color sequence type <{code};\x1b[33m<2|5>\x1b[39m"
                    )
                next = codes[i + 1]
                i += 1

                if next != 5 and next != 2:
                    raise ValueError(
                        f"Invalid special ansi color sequence <{code};\x1b[31m{next}\x1b[39m>"
                    )

                if next == 2:
                    if (missing := (i + 4) - len(codes)) > 0:
                        rgb = ["r", "g", "b"]
                        hint = [str(v) for v in codes[i + 1 : i + 4 - missing]]
                        hint.extend(f"\x1b[33m{v}\x1b[39m" for v in rgb[3 - missing :])
                        hint = ";".join(hint)
                        raise ValueError(
                            f"Missing special ansi color sequence rgb values <{code};2;{hint}>"
                        )
                    rgb = codes[i + 1 : i + 4]
                    rest = f"2;{';'.join(str(v) for v in rgb)}"
                    i += 3
                else:
                    if i + 1 >= len(codes):
                        raise ValueError(
                            f"Missing special ansi color sequence xterm code <{code};5;\x1b[33m<code>\x1b[39m"
                        )
                    rest = f"5;{codes[i+1]}"
                    i += 1

                t(f"8;{rest}")
            i += 1
        return style

    @cache
    def reset(self) -> str:
        styles = [
            Ansi[f"U_{style.name}"] for style in S if self.style & style.value > 0
        ]
        fg, bg = "", ""
        if self.fg != "":
            fg += "39"
        if self.bg != "":
            bg += "49"
        return f"\x1b[{';'.join([str(style.value) for style in styles])}{fg}{bg}m"

    @cache
    def ansi(self) -> str:
        styles = [Ansi[style.name] for style in S if self.style & style.value > 0]
        if len(styles) == 0 and self.fg == "" and self.bg == "":
            return ""
        return f"\x1b[{';'.join([str(style.value) for style in styles])}{self.fg}{self.bg}m"

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, Style):
            return (
                self.style == __value.style
                and self.fg == __value.fg
                and self.bg == __value.bg
            )
        return False

    def __repr__(self) -> str:
        return self.reset()

    def __str__(self) -> str:
        return self.ansi()

