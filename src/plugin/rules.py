"""The splitting rules, as the README pins them. load_receipt's answer key is computed here, in exact fractions."""

from __future__ import annotations

import re
from collections import defaultdict
from fractions import Fraction

from contract import CouponKind, Kind, ReceiptOutput

DECIMAL = re.compile(r"(0|[1-9][0-9]*)(\.[0-9]*[1-9])?")  # canonical: no sign, exponent or needless zero
MONEY = re.compile(r"(0|[1-9][0-9]*)\.[0-9]{2}")
WHOLE = re.compile(r"0|[1-9][0-9]*")


def cents_text(cents: int) -> str:
    """Whole cents as dollars with two decimals: 2341 -> '23.41'."""
    return f"{cents // 100}.{cents % 100:02d}"


def exact_shares(receipt: ReceiptOutput) -> dict[str, Fraction]:
    """{person: exact amount owed}, line by line: each line's cost split equally among who shares it; the coupon
    off the named lines; each kind's tax on what is left; the tip on the cost before the coupon; then the treated
    person's amount split equally among everyone else."""
    rates = {Kind.FOOD: Fraction(receipt.food_tax) / 100, Kind.ALCOHOL: Fraction(receipt.alcohol_tax) / 100}
    tip = Fraction(receipt.tip) / 100
    cost = {line.item: Fraction(line.price) * int(line.qty) for line in receipt.lines}
    off: dict[str, Fraction] = defaultdict(Fraction)
    for coupon in receipt.coupons:
        named = sum(cost[item] for item in coupon.items)
        for item in coupon.items:
            if coupon.kind is CouponKind.PERCENT:
                off[item] = cost[item] * Fraction(coupon.value) / 100
            else:
                off[item] = min(Fraction(coupon.value), named) * cost[item] / named
    owed: dict[str, Fraction] = {person: Fraction(0) for person in receipt.people}
    for line in receipt.lines:
        each = len(line.shared_by)
        charged = (cost[line.item] - off[line.item]) * (1 + rates[line.kind]) + cost[line.item] * tip
        for person in line.shared_by:
            owed[person] += charged / each
    for treated in receipt.treat:
        others = [person for person in receipt.people if person != treated]
        given, owed[treated] = owed[treated], Fraction(0)
        for person in others:
            owed[person] += given / len(others)
    return owed


def split(receipt: ReceiptOutput) -> tuple[int, dict[str, int]]:
    """(total, {person: owed}) in whole cents. The total is the exact sum rounded half up; each share is cut down
    to the cent, and the cents still missing go one each to the largest cut-off remainders, ties by name."""
    owed = exact_shares(receipt)
    in_cents = {person: value * 100 for person, value in owed.items()}
    total = int(sum(in_cents.values()) + Fraction(1, 2))
    cents = {person: value.numerator // value.denominator for person, value in in_cents.items()}
    order = sorted(receipt.people, key=lambda person: (-(in_cents[person] - cents[person]), person))
    for person in order[: total - sum(cents.values())]:
        cents[person] += 1
    return total, cents
