""" CSS LEXING
https://www.w3.org/TR/css-syntax-3/#tokenizing-and-parsing

References:
    - [basics](https://developer.mozilla.org/en-US/docs/Learn/CSS/First_steps/How_CSS_is_structured)
    - [nesting](https://developer.chrome.com/articles/css-nesting/)
    - [custom properites](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
    - [pseudo classes+functions](https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes)
    - [@media](https://developer.mozilla.org/en-US/docs/Web/CSS/@media)
    - [@import](https://developer.mozilla.org/en-US/docs/Web/CSS/@import)

<comment></comment>
<at-rule/>
<ruleset>
    <selector/> <block>
        <property/>: <value/>;
        <variable/>: <anything/>;
    </block>
</ruleset>

property => List of valid properties,
value => int, float, function, shorthand, hex, named constants, etc...,
block => `{}`,
selector => element, class, id, pseudo, children, sibling, etc...,
at-rules => @import, @media, etc...,
"""

from __future__ import annotations
import re
from typing import Literal
from contui.css.tokens import *
REPLACEMENT_CHAR = '\uFFFD'

class Check:
    @staticmethod
    def letter(current: str | None) -> bool:
        return current is not None and current.isalpha()

    @staticmethod
    def non_ascii(current: str | None) -> bool:
        return current is not None and ord(current) >= ord('\u0080')

    @staticmethod
    def ident_start(current: str | None) -> bool:
        return current is not None and (Check.letter(current) or Check.non_ascii(current) or current == "_")

    @staticmethod
    def digit(current: str | None) -> bool:
        return current is not None and current.isdigit()

    @staticmethod
    def whitespace(current: str | None) -> bool:
        return current is not None and current in '\t\n '

    @staticmethod
    def hex(current: str | None) -> bool:
        return current is not None and (current.isdigit() or current in 'abcdefABCDEF')

    @staticmethod
    def ident(current: str | None) -> bool:
        return current is not None and (Check.letter(current) or Check.digit(current) or current == "-")

    @staticmethod
    def escape(current: str | None, next: str | None) -> bool:
        return current == "\\" and next != "\n"

    @staticmethod
    def non_printable(current: str | None) -> bool:
        o = ord(current or '')
        return (
            current is not None
            and (
                o in range(ord('\u0000'), ord('\u0008'))
                or current == "\t"
                or o in range(ord('\u000E'), ord('\u001F'))
                or o == ord('\u007F')
            )
        )

    @staticmethod
    def starts_with_ident(first: str | None, second: str | None, third: str | None) -> bool:
        if second is None or third is None:
            return False

        if Check.ident_start(first):
            return True
        elif (
            first == "-"
            and (Check.ident_start(second) or second == "-")
            or Check.escape(second, third)
        ):
            return True
        elif first == "\\" and Check.escape(first, second):
            return True
        return False

    @staticmethod
    def starts_with_number(first: str, second: str | None, third: str | None) -> bool:
        if first in "+-":
            if Check.digit(second):
                return True
            elif second == "." and Check.digit(third):
                return True
            return False
        elif first == ".":
            return Check.digit(second)
        elif Check.digit(first):
            return True
        return False




RETURNS = re.compile("\r\n|\f|\r")
class Lexer:
    def __init__(self, source: str) -> None:
        self.source: list[str] = list(RETURNS.sub("\n", source).replace('\u0000', REPLACEMENT_CHAR))
        self.index = 0
        self.pos = [1, 1]
        self.errors = []

    @staticmethod
    def from_path(path: str) -> Lexer:
        return Lexer(Lexer.get_css(path))

    @staticmethod
    def get_css(path: str) -> str:
        """Automatically attempt to figure out the encoding and return the bytes of the source.

        Returns:
            tuple[str, bytes]: The charset and the sources bytes.
        """
        with open(path, "rb") as f:
            if (chrst := f.read(8)) == b'@charset':
                chrst = b''
                while (byte := f.read(1)) != b";":
                    chrst += byte
                chrst = chrst.decode().strip().replace('"', "").lower()
                # PERF: Optimize and read per char
                return (
                    f.read()
                    .decode(chrst)
                    .strip()
                )
            return (
                (chrst + f.read())
                .decode()
                .strip()
            )

    def __iter__(self):
        return self

    def __next__(self):
        next = self.consume()
        if isinstance(next, EOF):
            raise StopIteration
        return next

    def process(self) -> list[Token]:
        """Parses the entire source at once."""
        return [token for token in self]

    def peek(self, amount: int = 1) -> str | None:
        """The next code point."""
        if len(self.source) >= amount:
            return self.source[amount-1]
        return None

    def next(self) -> str:
        if len(self.source) >= 1:
            return self.source.pop(0)
        return "_error_"

    def error(self, error: Exception):
        self.errors.append(error)

    def _consume_comment_(self, current: str) -> Comment:
        comment = Comment(current + self.next())
        next = self.next()
        while self.peek() != "/" or next != "*":
            if next is None or self.peek() is None:
                raise ParseError("Comment not closed")
            comment.raw += next
            next = self.next()
        comment.raw += "*/"
        self.next()
        return comment

    def _consume_whitespace_(self, current: str) -> Whitespace:
        whitespace = Whitespace(current)
        while (peek := self.peek()) is not None and peek in "\n\t ":
            whitespace.raw += self.next()
        return whitespace

    def _consume_string_(self, current: str, ending: str|None = None) -> String | BadString:
        # print(current, ending)
        # input()
        ending = ending or current
        if self.peek() is None:
            return BadString()

        string = String()
        escaped = False
        while True:
            if self.peek() is None:
                self.error(ParseError("String was not closed"))
                return string
            if (next := self.next()) == "\\":
                escaped = True
            elif next == "\n" and escaped:
                continue
            elif next == "\n":
                self.error(SyntaxError("String literal not closed"))
                return BadString(string.raw)
            elif not escaped and next == ending:
                return string
            else:
                string.raw += next
                escaped = False

    def _consume_escape_(self, current: str) -> str:
        if self.peek() is None:
            return REPLACEMENT_CHAR

        next = self.next()
        if Check.hex(next):
            output = next
            while Check.hex(self.peek()) and len(output) < 7:
                output += self.next()
            if Check.digit(output) and int(output) == 0 or int(output, 16) > int("10FFFF", 16):
                return REPLACEMENT_CHAR
            return current + output
        else:
            return next

    def _consume_ident_(self) -> str:
        result = ''

        while self.peek() is not None:
            next = self.next()
            if Check.ident(next):
                result += next
            elif Check.escape(next, self.peek()):
                result += self._consume_escape_(next)
            else:
                self.source.insert(0, next)
                return result
        return result

    def _consume_hash_(self, current: str) -> Hash | Delim:
        if len(self.source) >= 1:
            if Check.ident(self.peek()) or Check.escape(self.peek(), self.peek(2)):
                hasht = Hash('#')
                first = self.peek()
                second = self.peek(2)
                third = self.peek(3)
                if Check.starts_with_ident(first, second, third):
                    hasht.type = "id"
                hasht.raw = self._consume_ident_()
                return hasht
        return Delim(current)

    def _consume_number_(self) -> tuple[int, Literal['integer', 'number'], str]:
        """Consume a number from the code points. Returning a numeric value and a type
        of either integer or number.
        """
        _type = 'integer'
        raw = ''
        if (peek := self.peek()) is not None and peek in "-+":
            raw += self.next()

        while Check.digit(self.peek()):
            raw += self.next()

        if self.peek() == "." and Check.digit(self.peek(2)):
            raw += self.next() + self.next()
            _type = "number"
            while Check.digit(self.peek()):
                raw += self.next()
            return int(raw), _type, raw
        elif (peek := self.peek()) is not None and peek in "Ee":
            science = ''
            _type = "number"
            _t = self.next() # Consume the E
            if (peek := self.peek(2)) is not None and peek in "-+" and Check.digit(self.peek(3)):
                science = self.next() + self.next()
            elif Check.digit(self.peek(2)):
                science = self.next()
            while Check.digit(self.peek()):
                science += self.next()
            return int(raw) * (10 ** int(science)), _type, raw + _t + science
        return int(raw), _type, raw

    def _consume_numeric_(self) -> Number | Percentage | Dimension:
        """Consume code points a produce a Number, Percentage, or Dimension token."""
        number = self._consume_number_()
        if Check.starts_with_ident(self.peek(), self.peek(2), self.peek(3)):
            dim = Dimension(number[0], number[1], '', number[2])
            dim.unit = self._consume_ident_()
            dim.raw += dim.unit
            return dim
        elif self.peek() == "%":
            self.next()
            return Percentage(*number)
        return Number(*number)

    def _consume_remnant_bad_url_(self):
        next = self.next()
        while True:
            if next in ["_error_", ")"]:
                return
            elif Check.escape(next, self.peek()):
                self._consume_escape_(next)
            next = self.next()

    def _consume_url_(self) -> Url | BadUrl:
        url = Url()
        while Check.whitespace(self.peek()):
            self.next()

        if self.peek() is None:
            self.error(ParseError("Url not closed"))

        next = self.next()
        while True:
            if next == ")":
               return url 
            elif Check.whitespace(next):
                while Check.whitespace(self.peek()):
                    self.next()
                if (peek := self.peek()) is None or peek == ")":
                    self.next()
                    self.error(ParseError("Url not closed"))
                    return url
                else:
                    self._consume_remnant_bad_url_()
                    return BadUrl()
            elif next in '\'"(' or Check.non_printable(next):
                self._consume_remnant_bad_url_()
                return BadUrl()
            elif next == "\\":
                if Check.escape(next, self.peek()):
                    url.raw += self._consume_escape_(next)
                else:
                    self.error(ParseError("Invalid backslash in url"))
                    self._consume_remnant_bad_url_()
                    return BadUrl()
            else:
                url.raw += next

            if self.peek() is None:
                self.error(ParseError("Url not closed"))
                return url

            next = self.next()

    def _consume_ident_like_(self) -> Ident | Function | Url | BadUrl:
        ident = self._consume_ident_()
        if ident == "url" and self.peek() == "(":
            self.next()
            while Check.whitespace(self.peek()) and Check.whitespace(self.peek(2)):
                self.next()
            two = (self.peek() or '') + (self.peek(2) or '')
            one = (self.peek() or '')
            if (len(two) == 2 and two[0] == " " and two[1] in '\'"') or (len(one) == 1 and one in '\'"'):
                return Function(ident)
            else:
                return self._consume_url_()
        elif self.peek() == "(":
            self.next()
            return Function(ident)
        if ident == "":
            input(ident)
        return Ident(ident)

    def consume(self) -> Token:
        """Consume code points and return the next token."""
        next = self.next()
        if next == "_error_":
            return EOF()
        elif next == "/" and self.peek() == "*":
            return self._consume_comment_(next)
        elif next in '"\'':
            return self._consume_string_(next)
        elif next == '#':
            return self._consume_hash_(next)
        elif next == "+":
            if Check.starts_with_number(next, self.peek(), self.peek(2)):
                self.source.insert(0, next)
                return self._consume_numeric_()
            return Delim(next)
        elif next == "-":
            if Check.starts_with_number(next, self.peek(), self.peek(2)):
                self.source.insert(0, next)
                return self._consume_numeric_()
            elif self.peek(2) == "-" and self.peek(3) == ">":
                self.next()
                self.next()
                return CDC('-->')
            elif Check.starts_with_ident(next, self.peek(2), self.peek(3)):
                self.source.insert(0, next)
                return self._consume_ident_like_()
            return Delim(next)
        elif next == ".":
            if Check.starts_with_number(next, self.peek(2), self.peek(3)):
                self.source.insert(0, next)
                return self._consume_numeric_()
            return Delim(next)
        elif next == "<":
            if (self.peek(1)or'') + (self.peek(2) or '') + (self.peek(3) or '') == "!--":
                self.next()
                self.next()
                self.next()
                return CDO('<!--')
            return Delim("<")
        elif next == "@":
            if Check.starts_with_ident(self.peek(), self.peek(2), self.peek(3)):
                return AtKeyword(self._consume_ident_())
            return Delim(next)
        elif next == "\\":
            if Check.escape(next, self.peek()):
                self.source.insert(0, next)
                return self._consume_ident_like_()
            self.error(ParseError("Invalid backslash"))
            return Delim(next)
        elif Check.digit(next):
            self.source.insert(0, next)
            return self._consume_numeric_()
        elif Check.ident_start(next):
            self.source.insert(0, next)
            return self._consume_ident_like_()
        elif next in "\n\t ":
            return self._consume_whitespace_(next)
        elif next == "(":
            return LParantheses(next)
        elif next == ")":
            return RParantheses(next)
        elif next == "[":
            return LSquareBracket(next)
        elif next == "]":
            return RSquareBracket(next)
        elif next == "{":
            return LCurlyBracket(next)
        elif next == "}":
            return RCurlyBracket(next)
        elif next == ",":
            return Comma(next)
        elif next == ":":
            return Colon(next)
        elif next == ";":
            return Semicolon(next)
        else:
            return Delim(next)

class ParseError(Exception): pass

if __name__ == "__main__":
    """
    @        | at-rule
    :        | pseudo-class
    ::       | pseudo-element
    .        | class
    #        | id
    *        | any
    keyword  | element tag
    function | function name and params
    """
    
    # Unicode in -> tokenization -> AST -> CSSStylesheet Object

    # First bytes == @charset ""
    source = Lexer.get_css("css/at_rule.css")
    parser = Lexer(source)

    compressed = ""
    previous = ""
    for token in parser:
        if not isinstance(token, Whitespace):
            print(repr(token))
            if isinstance(token, Comment):
                continue
            if isinstance(previous, AtKeyword):
                compressed += " "
            elif isinstance(token, (Ident, Function, Number, Percentage, Dimension)) and isinstance(previous, (Ident, Number)):
                compressed += " "
            compressed += str(token)
            previous = token

    print(parser.errors)
    with open("css/out_lexer.txt", "+w", encoding="utf-8") as file:
        file.write(compressed)
        file.flush()
