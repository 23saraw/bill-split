"""The tools. Every one reads only the bundled receipts in data/ and writes nothing."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path

from contract import (
    CalculateInput,
    CalculateOutput,
    Coupon,
    CouponKind,
    EvenSplitOutput,
    KeyOutput,
    Kind,
    Line,
    ReceiptInput,
    ReceiptOutput,
    RoundInput,
    RoundOutput,
    Share,
    Value,
)
from plugin.rules import DECIMAL, MONEY, WHOLE, cents_text, exact_shares, split

DATA = Path(__file__).parent / "data"
RECEIPT_NAME = re.compile(r"[a-z0-9-]+\.json")
TOKEN = re.compile(r"\s*(?:([0-9]+(?:\.[0-9]+)?)|(.))")
FRACTION = re.compile(r"-?[1-9][0-9]*/[1-9][0-9]*")
MAX_EXPRESSION = 400


def money(text: object, what: str, *, zero: bool = False) -> str:
    if not (isinstance(text, str) and MONEY.fullmatch(text) and (zero or Fraction(text) > 0)):
        raise ValueError(f"{what} must be dollars with two decimals{'' if zero else ', above 0'}, not {text!r}")
    return text


def rate(text: object, what: str, *, zero: bool = True) -> str:
    if not (isinstance(text, str) and DECIMAL.fullmatch(text) and (zero or Fraction(text) > 0) and Fraction(text) <= 100):
        raise ValueError(f"{what} must be a canonical decimal percent from {0 if zero else 'above 0'} to 100, not {text!r}")
    return text


def names(values: object, what: str, allowed: list[str] | None = None) -> list[str]:
    if not (isinstance(values, list) and values and all(isinstance(v, str) and v and v == v.strip() for v in values)):
        raise ValueError(f"{what} must be a non-empty list of trimmed, non-empty names")
    if len(set(values)) != len(values):
        raise ValueError(f"{what} names someone or something twice")
    unknown = [value for value in values if allowed is not None and value not in allowed]
    if unknown:
        raise ValueError(f"{what} names {unknown[0]!r}, which is not on the receipt")
    return values


def load(receipt: str) -> ReceiptOutput:
    """The receipt file ``receipt``, checked."""
    if not RECEIPT_NAME.fullmatch(receipt):
        raise ValueError(f"{receipt!r} is not a receipt file name (lowercase letters, digits and '-', then .json)")
    path = DATA / "receipts" / receipt
    if not path.is_file():
        receipts = sorted(file.name for file in (DATA / "receipts").glob("*.json"))
        raise FileNotFoundError(f"no receipt {receipt!r}: the receipts are {', '.join(receipts)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    people = names(data["people"], f"{receipt}'s people")
    if len(people) < 2:
        raise ValueError(f"{receipt} must have at least 2 people")
    lines = []
    for line in data["lines"]:
        if not (WHOLE.fullmatch(line["qty"]) and int(line["qty"]) >= 1):
            raise ValueError(f"{line['item']} has the qty {line['qty']!r}: a whole number of at least 1 is needed")
        lines.append(
            Line(
                item=line["item"],
                price=money(line["price"], f"{line['item']}'s price"),
                qty=line["qty"],
                kind=Kind(line["kind"]),
                shared_by=names(line["shared_by"], f"{line['item']}'s shared_by", people),
            )
        )
    items = names([line.item for line in lines], f"{receipt}'s items")
    coupons = []
    for coupon in data["coupons"]:
        kind = CouponKind(coupon["kind"])
        value = rate(coupon["value"], "a percent coupon", zero=False) if kind is CouponKind.PERCENT else money(
            coupon["value"], "an amount coupon"
        )
        coupons.append(Coupon(kind=kind, value=value, items=names(coupon["items"], "the coupon's items", items)))
    if len(coupons) > 1:
        raise ValueError(f"{receipt} has {len(coupons)} coupons: at most 1")
    treat = data["treat"]
    if treat:
        names(treat, f"{receipt}'s treat", people)
    if len(treat) > 1:
        raise ValueError(f"{receipt} treats {len(treat)} people: at most 1")
    return ReceiptOutput(
        receipt=receipt,
        people=people,
        lines=lines,
        food_tax=rate(data["food_tax"], "the food tax"),
        alcohol_tax=rate(data["alcohol_tax"], "the alcohol tax"),
        tip=rate(data["tip"], "the tip"),
        coupons=coupons,
        treat=list(treat),
    )


def load_receipt(given: ReceiptInput) -> KeyOutput:
    receipt = load(given.receipt)
    total, cents = split(receipt)
    return KeyOutput(
        **{field: getattr(receipt, field) for field in ReceiptOutput.__dataclass_fields__},
        total=cents_text(total),
        shares=[Share(person=person, owes=cents_text(cents[person])) for person in receipt.people],
    )


def read_receipt(given: ReceiptInput) -> ReceiptOutput:
    return load(given.receipt)


def evaluate(expression: str) -> Fraction:
    """``expression`` worked out exactly: decimal numbers, + - * /, unary minus and parentheses."""
    if not expression.strip() or len(expression) > MAX_EXPRESSION:
        raise ValueError(f"an expression must be 1 to {MAX_EXPRESSION} characters, not {len(expression)}")
    tokens = []
    for number, symbol in TOKEN.findall(expression):
        if symbol and symbol not in "+-*/()":
            if symbol.isspace():
                continue
            raise ValueError(f"{expression!r} has {symbol!r}: only numbers, + - * / and parentheses")
        tokens.append(Fraction(number) if number else symbol)
    tokens.append(None)
    position = 0

    def peek():
        return tokens[position]

    def take():
        nonlocal position
        position += 1
        return tokens[position - 1]

    def atom() -> Fraction:
        token = take()
        if token == "-":
            return -atom()
        if token == "(":
            value = sum_()
            if take() != ")":
                raise ValueError(f"{expression!r} has an unclosed parenthesis")
            return value
        if isinstance(token, Fraction):
            return token
        raise ValueError(f"{expression!r} is not arithmetic: a number or '(' is missing")

    def product() -> Fraction:
        value = atom()
        while peek() in ("*", "/"):
            if take() == "*":
                value *= atom()
            else:
                divisor = atom()
                if divisor == 0:
                    raise ValueError(f"{expression!r} divides by zero")
                value /= divisor
        return value

    def sum_() -> Fraction:
        value = product()
        while peek() in ("+", "-"):
            value = value + product() if take() == "+" else value - product()
        return value

    value = sum_()
    if peek() is not None:
        raise ValueError(f"{expression!r} has {peek()!r} where it should end")
    return value


def exact_text(value: Fraction) -> str:
    """A decimal when ``value`` ends, else 'p/q'."""
    rest = value.denominator
    for prime in (2, 5):
        while rest % prime == 0:
            rest //= prime
    if rest != 1:
        return f"{value.numerator}/{value.denominator}"
    places = 0
    while (value * 10**places).denominator != 1:
        places += 1
    digits = abs(value.numerator * 10**places // value.denominator)
    whole, part = divmod(digits, 10**places)
    text = str(whole) if places == 0 else f"{whole}.{part:0{places}d}"
    return f"-{text}" if value < 0 else text


def approx_text(value: Fraction) -> str:
    """``value`` rounded half away from zero to 6 decimals, in integers."""
    millionths = (abs(value) * 10**6 * 2 + 1) // 2
    whole, part = divmod(millionths, 10**6)
    text = f"{whole}.{part:06d}".rstrip("0").rstrip(".")
    return f"-{text}" if value < 0 and millionths else text


def calculate(given: CalculateInput) -> CalculateOutput:
    values = [evaluate(expression) for expression in given.expressions]
    return CalculateOutput(values=[Value(exact=exact_text(v), approx=approx_text(v)) for v in values])


def half_up_cents(value: Fraction) -> int:
    return int(value * 100 + Fraction(1, 2))


def even_split(given: ReceiptInput) -> EvenSplitOutput:
    receipt = load(given.receipt)
    total = half_up_cents(sum(exact_shares(receipt).values()))
    return EvenSplitOutput(
        receipt=receipt.receipt,
        people=receipt.people,
        total=cents_text(total),
        each=cents_text(half_up_cents(Fraction(total, 100) / len(receipt.people))),
    )


def amount(text: str) -> Fraction:
    """A non-negative amount as calculate writes it exactly: a canonical decimal or 'p/q'."""
    if DECIMAL.fullmatch(text) or (FRACTION.fullmatch(text) and not text.startswith("-")):
        value = Fraction(text)
        if exact_text(value) == text:
            return value
    raise ValueError(f"{text!r} is not a non-negative amount as calculate writes it ('4.335' or '13/3')")


def round_each(given: RoundInput) -> RoundOutput:
    return RoundOutput(rounded=[cents_text(half_up_cents(amount(text))) for text in given.amounts])
