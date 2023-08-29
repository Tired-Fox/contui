from typing import Literal

__all__ = [
    "Token",
    "Ident",
    "Function",
    "AtKeyword",
    "Hash",
    "String",
    "BadString",
    "Url",
    "BadUrl",

    "Delim",
    "Colon",
    "Semicolon",
    "Comma",

    "LCurlyBracket",
    "LSquareBracket",
    "LParantheses",
    "RCurlyBracket",
    "RSquareBracket",
    "RParantheses",

    "Number",
    "Percentage",
    "Dimension",

    "Comment",
    "Whitespace",
    "CDC",
    "CDO",
    "EOF"
]

class Token:
    raw: str 
    def __init__(self, raw: str = ''):
        self.raw = raw

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.raw!r})'

    def __str__(self) -> str:
        return self.raw

class Ident(Token): pass
class Function(Token):
    def __str__(self) -> str:
        return f"{self.raw}("
class AtKeyword(Token):
    def __str__(self) -> str:
        return f"@{self.raw}"
class Hash(Token):
    def __init__(self, raw: str = '', *, type: Literal['id', 'unrestricted'] = 'unrestricted'):
        self.type = type
        super().__init__(raw)
    def __repr__(self) -> str:
        return f'Hash({"id, " if self.type == "id" else ""}{self.raw!r})'
    def __str__(self) -> str:
        return f"#{self.raw}"

class String(Token):
    def __str__(self) -> str:
        return repr(self.raw)
class BadString(Token): pass
class Url(Token):
    def __str__(self) -> str:
        return f"url({self.raw})"
class BadUrl(Token): pass

class Delim(Token):
    def __init__(self, raw: str):
        if len(raw) > 1:
            raise ValueError("Delimiters may only be one codepoint long")
        super().__init__(raw)
    def __repr__(self) -> str:
        return f'Delim({self.raw!r})'

class Colon(Delim): pass
class Semicolon(Delim): pass
class Comma(Delim): pass

class LCurlyBracket(Token):
    @property
    def alt(self) -> type:
        return RCurlyBracket
    @staticmethod
    def value() -> Literal['{']:
        return '{'
class RCurlyBracket(Token):
    @property
    def alt(self) -> type:
        return LCurlyBracket
    @staticmethod
    def value() -> Literal['}']:
        return '}'
class LSquareBracket(Token):
    @property
    def alt(self) -> type:
        return RSquareBracket
    @staticmethod
    def value() -> Literal['[']:
        return '['
class RSquareBracket(Token):
    @property
    def alt(self) -> type:
        return LSquareBracket 
    @staticmethod
    def value() -> Literal[']']:
        return ']'
class LParantheses(Token):
    @property
    def alt(self) -> type:
        return RParantheses
    @staticmethod
    def value() -> Literal['(']:
        return '('
class RParantheses(Token):
    @property
    def alt(self) -> type:
        return LParantheses
    @staticmethod
    def value() -> Literal[')']:
        return ')'

class Number(Token):
    value: int
    type: Literal['integer', 'number']
    def __init__(self, value: int, type: Literal['integer', 'number'], raw: str):
        self.value = value 
        self.type = type
        super().__init__(raw)

    def __repr__(self) -> str:
        return f"Number({self.raw!r})"

class Percentage(Number):
    def __repr__(self) -> str:
        return f"Percentage({self.value!r}%)"

    def __str__(self) -> str:
        return f"{self.raw}%"
class Dimension(Token):
    value: int
    type: Literal['integer', 'number']
    def __init__(self, value: int, type: Literal['integer', 'number'], unit: str, raw: str):
        self.value = value 
        self.unit = unit
        self.type = type
        super().__init__(raw)

    def __repr__(self) -> str:
        return f"Dimension({self.raw!r})"

    def __str__(self) -> str:
        return f"{self.raw}"

class Comment(Token):
    def __init__(self, raw: str):
        super().__init__(raw)

    @property
    def text(self) -> str:
        return self.raw.lstrip("/*").rstrip("*/")

class Whitespace(Token): pass
class CDO(Token): pass
class CDC(Token): pass
class EOF(Token): pass
