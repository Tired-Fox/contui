""" CSS Parser
https://www.w3.org/TR/css-syntax-3/#parsing
"""

from __future__ import annotations
from typing import Any, Generic, Literal, Optional, TypeVar
from contui.css.lexer import Lexer, ParseError

from contui.css.tokens import *

class Preserved:
    token: Token
    def __init__(self, token: Token) -> None:
        # NOTE: Not function, {}, (), [], bad-string, or bad-url tokens
        self.token = token

class FunctionBlock:
    name: str
    value: list[Component]
    def __init__(self, name: str, value: list | None = None) -> None:
        self.name = name
        self.value = value or []

class Block:
    token: LCurlyBracket | LSquareBracket | LParantheses
    value: list[Component]
    def __init__(self, token: LCurlyBracket | LSquareBracket | LParantheses) -> None:
        self.token =  token
        self.value = []

class Decleration:
    important: bool
    name: str
    value: list[Component]
    def __init__(self, name: str, value: list | None = None):
        self.name = name
        self.value = value or []
        self.important = False

    def __repr__(self) -> str:
        return f"Decl({'!, ' if self.important else ''}{self.name!r}, {self.value})"

Component = Preserved | FunctionBlock | Decleration | Block

class PropertyDecl(Decleration): pass
class DescriptorDecl(Decleration): pass

class QualifiedRule:
    prelude: list[Component]
    block: Block | None
    def __init__(self, prelude: list[Component] | None = None, block: Block | None = None) -> None:
        self.prelude = prelude or []
        self.block = block

    def __repr__(self) -> str:
        return f"QualifiedRule(prelude={self.prelude}, block={{...}})"

class AtRule:
    name: str
    prelude: list[Component]
    block: Optional[Block]
    def __init__(self, name: str, prelude: list | None = None, block: Block | None = None) -> None:
        self.name = name
        self.prelude = prelude or []
        self.block = block

    def __repr__(self) -> str:
        block = "None"
        if block is not None:
            block = "{...}"
        return f"AtRule({self.name!r}, prelude={self.prelude}, block={block})"

    
T = TypeVar("T")
class CSSStylesheet(Generic[T]):
    # constructorDocument: None
    # media: list[str]

    def __init__(
        self,
        base: str | None = None,
        location: str | None = None,
        title: str = "",
        parent: CSSStylesheet | None = None,
        ownerNode: T | None = None,
        ownerRule: None = None,
        disabled: bool = False,
        *,
        disallow_modification: bool = False
    ) -> None:
        self._base_ = base
        self._location_ = location
        self.parentStyleSheet = parent
        self.ownerNode = ownerNode 
        self._owner_css_rule_ = ownerRule
        self.title = title if title != "" else None
        self.alternate = False
        self.disabled = disabled
        self.origin_clean = True 
        self.disallow_modification = disallow_modification
        self.constructed = True
        
        self._css_rules_ = []

    @property
    def owner_rule(self) -> Any | None:
        return self._owner_css_rule_

    @property
    def css_rules(self) -> list[Any]:
        return self._css_rules_

    def insertRule(self, rule, index: int = -1) -> int:
        if not self.origin_clean:
            raise SecurityError
        if self.disallow_modification:
            raise NotAllowedError 

        parsed_rule = Parse.parse_rule(rule)

        rule = Parse.parse_rule(rule)
        if parsed_rule == "@import" and self.constructed:
            raise SyntaxError
        if isinstance(rule, AtRule) and rule.name == "namespace" and not all(isinstance(v, AtRule) and v.name in ["namespace", "import"] for v in self.css_rules):
            raise InvalidStateError

        self._css_rules_.insert(index, rule)
        return index

    def deleteRule(self, index: int):
        if not self.origin_clean:
            raise SecurityError
        if self.disallow_modification:
            raise NotAllowedError

        oldRule = self._css_rules_[index]
        if isinstance(oldRule, AtRule) and oldRule.name == "namespace" and not all(isinstance(v, AtRule) and v.name in ["namespace", "import"] for v in self.css_rules):
            raise InvalidStateError
        self._css_rules_.pop(index)

    @property
    def type(self) -> Literal['text/css']:
        return 'text/css'

    @property
    def href(self) -> str | None:
        return self._location_

    def replace(self, text: str) -> CSSStylesheet:
        if not self.constructed or self.disallow_modification:
            raise NotAllowedError

        rules = Parse.parse_rule_list(text)
        rules = list(filter(lambda r: isinstance(r, AtRule) and r.name == "import", rules))
        self._css_rules_ = rules

        return self

    def __repr__(self) -> str:
        sep = "\n  "
        return f"""Stylesheet(
  {sep.join(repr(rule) for rule in self.css_rules)}
)"""

class SecurityError(Exception):pass
class NotAllowedError(Exception):pass
class InvalidStateError(Exception):pass

Tokens = list[Token] | str | list[Component] 

class Parse:
    @staticmethod
    def normalize(_input_: Tokens) -> list[Token] | list[Component]:
        if isinstance(_input_, list):
            return _input_
        elif isinstance(_input_, str):
            lexer = Lexer(_input_)
            return lexer.process()
        raise TypeError(
            "Unexpected input to parse. Expected string, list of tokens, or list of component values."
        )

    @staticmethod
    def parse_component_value(source: Tokens) -> Component:
        parser = Parser(source)
        while isinstance(parser.peek(), Whitespace):
            parser.next()
        if isinstance(parser.peek(), EOF):
            raise SyntaxError("Expected component value")
        cv = parser.consume_component_value()
        while isinstance(parser.peek(), Whitespace):
            parser.next()
        if isinstance(parser.peek(), EOF):
            return cv
        raise SyntaxError("Expected only a component value but recieve more tokens")

    @staticmethod
    def parse_component_values(_input_: Tokens) -> list[Component]:
        parser = Parser(_input_)
        result = []
        while not isinstance(val := parser.consume_component_value(), EOF):
            result.append(val)
        return result

    @staticmethod
    def parse_comma_seperated(_input_: Tokens) -> list:
        parser = Parser(_input_)
        if all(isinstance(v, Whitespace) for v in parser.tokens):
            return []

        result = []
        current = []
        while True:
            next = parser.consume_component_value()
            if isinstance(next, EOF):
                if len(current) > 0:
                    result.append(current)
                break
            elif isinstance(next, Delim) and next.raw == ',':
                if len(current) > 0:
                    result.append(current)
                    current = []
            else:
                current.append(next)
        return result

    @staticmethod
    def parse_rule_list(_input_: Tokens):
        parser = Parser(_input_)
        return parser.consume_rule_list()

    @staticmethod
    def parse_rule(_input_: Tokens):
        parser = Parser(_input_)

        while isinstance(parser.peek(), Whitespace):
            parser.next()

        rule = None
        if isinstance(parser.peek(), EOF):
            raise SyntaxError
        elif isinstance(parser.peek(), AtKeyword):
            rule = parser.consume_at_rule()
        else:
            rule = parser.consume_qualified_rule()
            if rule is None:
                raise SyntaxError("Invalid rule")

        while isinstance(parser.peek(), Whitespace):
            parser.next()

        if isinstance(parser.peek(), EOF):
            return rule
        raise SyntaxError("Invalid rule, more tokens then expected")

    @staticmethod
    def parse_decleration(source: Tokens) -> Decleration:
        parser = Parser(source)
        while isinstance(parser.peek(), Whitespace):
            parser.next()

        if not isinstance(parser.peek(), Ident):
            raise SyntaxError("Missing ident for decleration")
        decl = parser.consume_decleration()
        if (decl) is not None:
            return decl
        raise SyntaxError("Invalid decleration")

    @staticmethod
    def parse_stylesheet(source: Tokens, url: str | None = None) -> CSSStylesheet:
        stylesheet = CSSStylesheet(location=url)
        parser = Parser(source)
        stylesheet._css_rules_ = parser.consume_rule_list(True)
        return stylesheet

    @staticmethod
    def parse_style_block(source: Tokens) -> list[Decleration | AtRule | QualifiedRule]:
        parser = Parser(source)
        return parser.consume_style_block()

    @staticmethod
    def parse_decl_list(source: Tokens) -> list[Decleration]:
        parser = Parser(source)
        return parser.consume_decl_list()


class Parser:
    # List of css tokens, return input
    # List of css component values, return input
    # string, filter code points, tokenize result, and return final
    def __init__(self, tokens: Tokens) -> None:
        self.tokens: list[Token] | list[Component] = Parse.normalize(tokens)
        self.errors: list[Exception] = []

    def peek(self, amount: int = 1) -> Token | Component:
        if len(self.tokens) >= amount:
            return self.tokens[amount - 1]
        return EOF()

    def reconsume(self, value):
        self.tokens.insert(0, value)

    def next(self) -> Token | Component:
        if len(self.tokens) >= 1:
            return self.tokens.pop(0)
        return EOF()

    def error(self, error: Exception):
        self.errors.append(error)

    def consume_block(self, opening: LCurlyBracket | LSquareBracket | LParantheses) -> Block:
        block = Block(opening)
        while True:
            next = self.next()
            if isinstance(next, opening.alt):
                return block
            elif isinstance(next, EOF):
                self.error(ParseError("Block was not closed"))
                return block
            else:
                self.reconsume(next)
                block.value.append(self.consume_component_value())

    def consume_function(self, function: Function) -> FunctionBlock:
        fblock = FunctionBlock(function.raw)
        while True:
            next = self.next()
            if isinstance(next, RParantheses):
                return fblock
            elif isinstance(next, EOF):
                self.error(ParseError("Function was not closed"))
                return fblock
            else:
                self.reconsume(next)
                fblock.value.append(self.consume_component_value())

    def consume_component_value(self) -> Component:
        next = self.next()
        if isinstance(next, (LCurlyBracket, LSquareBracket, LParantheses)):
            return self.consume_block(next)
        elif isinstance(next, Function):
            return self.consume_function(next)
        return next

    def consume_at_rule(self) -> AtRule:
        next = self.next()
        at_rule = AtRule(next.raw)

        while True:
            next = self.next()
            if isinstance(next, Semicolon):
                return at_rule
            elif isinstance(next, EOF):
                self.error(ParseError("At Rule missing semi-colon"))
                return at_rule
            elif isinstance(next, LCurlyBracket):
                at_rule.block = self.consume_block(next)
                return at_rule
            elif isinstance(next, Block) and isinstance(next.token, LCurlyBracket):
                at_rule.block = next
                return at_rule
            else:
                self.reconsume(next)
                at_rule.prelude.append(self.consume_component_value())

    def consume_qualified_rule(self) -> QualifiedRule | None:
        qrule = QualifiedRule()
        while True:
            next = self.next()
            if isinstance(next, EOF):
                self.error(ParseError("Qualified rule is not closed"))
                return None
            elif isinstance(next, LCurlyBracket):
                qrule.block = self.consume_block(next)
                return qrule
            elif isinstance(next, Block) and isinstance(next.token, LCurlyBracket):
                qrule.block = next
                return qrule
            else:
                self.reconsume(next)
                qrule.prelude.append(self.consume_component_value())

    def consume_rule_list(self, top_level: bool = False) -> list[QualifiedRule | AtRule]:
        rules = []
        while True:
            next = self.next()
            if isinstance(next, Whitespace):
                continue
            elif isinstance(next, EOF):
                return rules
            elif isinstance(next, (CDO, CDC)):
                if top_level: continue
                self.reconsume(next)
                if (rule := self.consume_qualified_rule()) is not None:
                    rules.append(rule)
            elif isinstance(next, AtKeyword):
                self.reconsume(next)
                rules.append(self.consume_at_rule())
            else:
                self.reconsume(next)
                if (rule := self.consume_qualified_rule()) is not None:
                    rules.append(rule)

    def consume_decleration(self) -> Decleration | None:
        next = self.next()
        decl = Decleration(next.raw)
        while isinstance(self.peek(), Whitespace):
            self.next()

        if not isinstance(self.peek(), Colon):
            self.error(ParseError("Expected a colon"))
            return None

        next = self.next() 
        while isinstance(self.peek(), Whitespace):
            self.next()

        while not isinstance(self.peek(), EOF):
            decl.value.append(self.consume_component_value())
        while isinstance(decl.value[-1], Whitespace):
            decl.value.pop()
        
        if len(decl.value) >= 2 and isinstance(decl.value[-2], Delim) and decl.value[-2].raw == "!" and isinstance(decl.value[-1], Ident) and decl.value[-1].raw == "important":
            decl.value.pop()
            decl.value.pop()
            decl.important = True

        while isinstance(decl.value[-1], Whitespace):
            decl.value.pop()

        return decl

    def consume_style_block(self) -> list[Decleration | AtRule | QualifiedRule]:
        decls = []
        rules = []
        while True:
            next = self.next()
            if isinstance(next, (Whitespace, Semicolon)):
                continue
            elif isinstance(next, EOF):
                return decls + rules
            elif isinstance(next, AtKeyword):
                self.reconsume(next)
                rules.append(self.consume_at_rule())
            elif isinstance(next, Ident):
                temp: list = [next]
                while not isinstance(self.peek(), (EOF, Semicolon)):
                    temp.append(self.consume_component_value())
                if (decl := Parse.parse_decleration(temp)) is not None:
                    decls.append(decl)
            elif isinstance(next, Delim) and next.raw == "&":
                self.reconsume(next)
                if (qrule := self.consume_qualified_rule()) is not None:
                    rules.append(qrule)
            else:
                self.error(ParseError("Invalid style block syntax"))
                self.reconsume(next)
                while not isinstance(self.peek(), (EOF, Semicolon)):
                    self.consume_component_value()

    def consume_decl_list(self) -> list[Decleration]:
        decls = []
        while True:
            next = self.next()
            if isinstance(next, (Whitespace, Semicolon)):
                continue
            elif isinstance(next, EOF):
                return decls
            elif isinstance(next, AtKeyword):
                self.reconsume(next)
                decls.append(self.consume_at_rule())
            elif isinstance(next, Ident):
                temp: list = [next]
                while not isinstance(self.peek(), (Semicolon, EOF)):
                    temp.append(self.next())
                if (decl := Parse.parse_decleration(temp)) is not None:
                    decls.append(decl)
            else:
                self.error(ParseError("Invalid decleration list"))
                self.reconsume(next)
                while not isinstance(self.peek(), (Semicolon, EOF)):
                    self.consume_component_value()


if __name__ == "__main__":
    """
    <at-rule>, <ident-token>, <at-keyword-token>
    """
    # https://www.w3.org/TR/css-syntax-3/#rule-defs
    stylesheet = Parse.parse_stylesheet("""
@import "style.css";

div {
    color: blue !important;
    width: 100%;
    & a {
        text-decoration: none;
    }
}
""")

    if len(stylesheet.css_rules) > 1 and isinstance(stylesheet.css_rules[1], QualifiedRule):
        parser = Parser(stylesheet.css_rules[1].block.value)
        print(parser.tokens)
        print(parser.consume_style_block())

