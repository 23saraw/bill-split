"""The splitting rules, written again apart from src/plugin/rules.py and sharing no code with it.

The plugin charges line by line; this works person by person, keeping each person's food and alcohol apart, and
reads numbers through Decimal. A wrong rule would have to be written the same wrong way twice for the answer key
to pass."""

import math
import re
from decimal import Decimal
from fractions import Fraction

from contract import CouponKind, Kind

DECIMAL = re.compile(r"(0|[1-9][0-9]*)(\.[0-9]*[1-9])?")
MONEY = re.compile(r"(0|[1-9][0-9]*)\.[0-9]{2}")
WHOLE = re.compile(r"0|[1-9][0-9]*")


def exact(text):
    """A canonical decimal or money string as an exact fraction."""
    return Fraction(Decimal(text))


def cents(text):
    """A money string as whole cents: '23.41' -> 2341."""
    dollars, part = text.split(".")
    return int(dollars) * 100 + int(part)


def money(count):
    return f"{count // 100}.{count % 100:02d}"


def judge(key):
    """{'exact': the exact total, 'total': it in cents rounded half up, 'left': the leftover cents, 'people':
    {person: {'exact', 'floor', 'extra', 'cents', 'treated'}}}, every amount in cents but 'exact' in dollars."""
    rate = {Kind.FOOD: exact(key.food_tax) / 100, Kind.ALCOHOL: exact(key.alcohol_tax) / 100}
    named, coupon = set(), None
    for coupon in key.coupons:
        named = set(coupon.items)
    before = {person: {Kind.FOOD: Fraction(0), Kind.ALCOHOL: Fraction(0)} for person in key.people}
    eligible = {person: {Kind.FOOD: Fraction(0), Kind.ALCOHOL: Fraction(0)} for person in key.people}
    for line in key.lines:
        portion = exact(line.price) * int(line.qty) / len(line.shared_by)
        for person in line.shared_by:
            before[person][line.kind] += portion
            if line.item in named:
                eligible[person][line.kind] += portion
    named_total = sum(sum(kinds.values()) for kinds in eligible.values())
    owed = {}
    for person in key.people:
        due = Fraction(0)
        for kind in (Kind.FOOD, Kind.ALCOHOL):
            if coupon is None:
                off = Fraction(0)
            elif coupon.kind is CouponKind.PERCENT:
                off = eligible[person][kind] * exact(coupon.value) / 100
            else:
                off = min(exact(coupon.value), named_total) * eligible[person][kind] / named_total
            due += (before[person][kind] - off) * (1 + rate[kind])
        owed[person] = due + sum(before[person].values()) * exact(key.tip) / 100
    treated = set(key.treat)
    for person in treated:
        others = [other for other in key.people if other != person]
        for other in others:
            owed[other] += owed[person] / len(others)
        owed[person] = Fraction(0)
    whole = sum(owed.values())
    total = math.floor(whole * 100 + Fraction(1, 2))
    people = {}
    for person in key.people:
        floor = math.floor(owed[person] * 100)
        people[person] = {"exact": owed[person], "floor": floor, "extra": False, "treated": person in treated}
    left = total - sum(entry["floor"] for entry in people.values())
    ranked = sorted(people, key=lambda person: (people[person]["floor"] - owed[person] * 100, person))
    for person in ranked[:left]:
        people[person]["extra"] = True
    for entry in people.values():
        entry["cents"] = entry["floor"] + entry["extra"]
    return {"exact": whole, "total": total, "left": left, "people": people}


def shown(value):
    """A non-negative fraction as a decimal: exact when it ends, else '≈' and 6 places."""
    rest, twos, fives = value.denominator, 0, 0
    while rest % 2 == 0:
        rest, twos = rest // 2, twos + 1
    while rest % 5 == 0:
        rest, fives = rest // 5, fives + 1
    places = max(twos, fives) if rest == 1 else 6
    digits = math.floor(value * 10**places + Fraction(1, 2))
    whole, part = divmod(digits, 10**places)
    text = str(whole) if places == 0 else f"{whole}.{part:0{places}d}".rstrip("0").rstrip(".")
    return text if rest == 1 else f"≈{text}"
