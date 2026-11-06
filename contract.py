"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output

RECEIPT = "A bundled receipt file's name, such as 'dinner-1.json'"
MONEY = "Dollars with exactly two decimals: digits, a point and two digits, such as '23.41' or '0.00'"
RATE = "A percent as a canonical decimal string, such as '8.25' or '0'"
PERSON = "A person's name, exactly as the receipt writes it"


class Tool(Enum):
    LOAD_RECEIPT = "load_receipt"
    READ_RECEIPT = "read_receipt"
    CALCULATE = "calculate"
    EVEN_SPLIT = "even_split"
    ROUND_EACH = "round_each"


class Task(Enum):
    SPLIT_BILL = "split-bill"


class Kind(Enum):
    FOOD = "food"
    ALCOHOL = "alcohol"


class CouponKind(Enum):
    PERCENT = "percent"
    AMOUNT = "amount"


@dataclass
class ReceiptInput(Output):
    receipt: Annotated[str, RECEIPT]


@dataclass
class Line(Output):
    item: Annotated[str, "The item's name on the receipt"]
    price: Annotated[str, "The price of one, in dollars with two decimals, such as '23.41'"]
    qty: Annotated[str, "How many were ordered: a whole number, at least 1"]
    kind: Annotated[Kind, "Food or alcohol; each is taxed at its own rate"]
    shared_by: Annotated[list[str], "Who shares the item, equally; the line's cost is price times qty"]


@dataclass
class Coupon(Output):
    kind: Annotated[CouponKind, "percent: value percent off each named item; amount: value dollars off the named items"]
    value: Annotated[str, "A percent coupon's percent, such as '25'; an amount coupon's dollars, such as '5.00'"]
    items: Annotated[list[str], "The items the coupon applies to"]


@dataclass
class ReceiptOutput(Output):
    receipt: Annotated[str, RECEIPT]
    people: Annotated[list[str], "Everyone at the table, including anyone who ate nothing"]
    lines: Annotated[list[Line], "The receipt's lines, as written"]
    food_tax: Annotated[str, "The tax rate on food: a canonical decimal percent, such as '8.25'"]
    alcohol_tax: Annotated[str, "The tax rate on alcohol: a canonical decimal percent, such as '8.25'"]
    tip: Annotated[str, "The tip: a canonical decimal percent, such as '18' or '0'"]
    coupons: Annotated[list[Coupon], "The coupon, or [] when there is none"]
    treat: Annotated[list[str], "The person the group treats, or [] when nobody is treated"]


@dataclass
class Share(Output):
    person: Annotated[str, PERSON]
    owes: Annotated[str, MONEY]


@dataclass
class SplitOutput(Output):
    receipt: Annotated[str, RECEIPT]
    total: Annotated[str, "The bill's total, in dollars with two decimals, such as '23.41'"]
    shares: Annotated[list[Share], "What each person owes, one entry per person at the table"]


@dataclass
class KeyOutput(Output):
    receipt: Annotated[str, RECEIPT]
    people: Annotated[list[str], "Everyone at the table"]
    lines: Annotated[list[Line], "The receipt's lines"]
    food_tax: Annotated[str, RATE]
    alcohol_tax: Annotated[str, RATE]
    tip: Annotated[str, RATE]
    coupons: Annotated[list[Coupon], "The coupon, or []"]
    treat: Annotated[list[str], "The treated person, or []"]
    total: Annotated[str, "The expected total, in dollars with two decimals, such as '23.41'"]
    shares: Annotated[list[Share], "The expected shares, one per person, in the receipt's order"]


@dataclass
class CalculateInput(Output):
    expressions: Annotated[
        list[str], "Arithmetic to work out exactly: decimal numbers, + - * /, and parentheses, such as '(13 / 3) * 0.75'"
    ]


@dataclass
class Value(Output):
    exact: Annotated[str, "The exact result: a decimal when it ends, such as '-2.5', else a fraction, such as '13/3'"]
    approx: Annotated[str, "The result rounded half away from zero to 6 decimals, such as '4.333333'"]


@dataclass
class CalculateOutput(Output):
    values: Annotated[list[Value], "One value per expression, in order"]


@dataclass
class EvenSplitOutput(Output):
    receipt: Annotated[str, RECEIPT]
    people: Annotated[list[str], "Everyone at the table"]
    total: Annotated[str, "The bill's total, in dollars with two decimals, such as '23.41'"]
    each: Annotated[str, "The rounded total divided by the number of people, rounded half up to the cent"]


@dataclass
class RoundInput(Output):
    amounts: Annotated[list[str], "Non-negative amounts, as calculate writes them exactly: '4.335' or '13/3'"]


@dataclass
class RoundOutput(Output):
    rounded: Annotated[list[str], "Each amount on its own, rounded half up to the cent"]


TOOLS = {
    Tool.LOAD_RECEIPT: (ReceiptInput, KeyOutput),
    Tool.READ_RECEIPT: (ReceiptInput, ReceiptOutput),
    Tool.CALCULATE: (CalculateInput, CalculateOutput),
    Tool.EVEN_SPLIT: (ReceiptInput, EvenSplitOutput),
    Tool.ROUND_EACH: (RoundInput, RoundOutput),
}
TASKS = {Task.SPLIT_BILL: (ReceiptInput, SplitOutput)}
