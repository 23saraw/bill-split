"""Checks shared by the tool verifiers. Pure functions of their arguments."""

import re

from contract import CouponKind

from .rules import DECIMAL, MONEY, WHOLE, exact

RECEIPT_NAME = re.compile(r"[a-z0-9-]+\.json")
MAX_VALUES = 50  # expressions or amounts one call may give
MAX_EXPRESSION = 400
MOST = 6  # list entries a constraint's expected or actual shows


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def constraint(identifier, text, ok, expected=None, actual=None, message=""):
    """One constraint's entry, always with the same keys: ok is True (holds), False (fails) or None (not
    checked: a check it needs did not hold); message says why it fails or was not checked, "" when it holds."""

    def cut(value):
        if isinstance(value, list) and len(value) > MOST:
            return value[:MOST] + [f"... {len(value) - MOST} more"]
        return value

    return {
        "id": identifier,
        "constraint": text,
        "ok": ok,
        "expected": cut(expected),
        "actual": cut(actual),
        "message": "" if ok is True else message or text,
    }


def summary(constraints):
    """A failed verdict's message: the first failing constraint, its id and why, then how many more fail."""
    failed = [entry for entry in constraints if entry["ok"] is False]
    more = f" (+{len(failed) - 1} more)" if len(failed) > 1 else ""
    return f"{failed[0]['id']}: {failed[0]['message']}{more}"


def is_money(text, *, zero=True):
    return MONEY.fullmatch(text) is not None and (zero or exact(text) > 0)


def is_rate(text, *, zero=True):
    return DECIMAL.fullmatch(text) is not None and (zero or exact(text) > 0) and exact(text) <= 100


def receipt_input(value):
    if not RECEIPT_NAME.fullmatch(value.receipt):
        return result(False, f"{value.receipt!r} is not a receipt file name (lowercase letters, digits and '-', then .json)")
    return result(True, "input is valid")


def names_problem(names, what, allowed=None):
    if not names:
        return f"{what} is empty"
    for name in names:
        if not name or name != name.strip():
            return f"{what} has the name {name!r}: names are trimmed and not empty"
        if allowed is not None and name not in allowed:
            return f"{what} names {name!r}, who or which is not on the receipt"
    if len(set(names)) != len(names):
        return f"{what} names someone or something twice"
    return None


def receipt_problem(receipt):
    """What is wrong with a receipt's data, or None (not whether anyone's share is right)."""
    if not RECEIPT_NAME.fullmatch(receipt.receipt):
        return f"{receipt.receipt!r} is not a receipt file name"
    problem = names_problem(receipt.people, "people")
    if problem or len(receipt.people) < 2:
        return problem or "a receipt has at least 2 people"
    for line in receipt.lines:
        if not is_money(line.price, zero=False):
            return f"{line.item!r} costs {line.price!r}: dollars with two decimals, above 0"
        if not (WHOLE.fullmatch(line.qty) and int(line.qty) >= 1):
            return f"{line.item!r} has the qty {line.qty!r}: a whole number of at least 1"
        problem = names_problem(line.shared_by, f"{line.item!r}'s shared_by", receipt.people)
        if problem:
            return problem
    items = [line.item for line in receipt.lines]
    problem = names_problem(items, "the items")
    if problem:
        return problem
    for field, value in (("food_tax", receipt.food_tax), ("alcohol_tax", receipt.alcohol_tax), ("tip", receipt.tip)):
        if not is_rate(value):
            return f"{field} is {value!r}: a canonical decimal percent from 0 to 100"
    if len(receipt.coupons) > 1:
        return f"the receipt has {len(receipt.coupons)} coupons: at most 1"
    for coupon in receipt.coupons:
        if coupon.kind is CouponKind.PERCENT and not is_rate(coupon.value, zero=False):
            return f"a percent coupon of {coupon.value!r}: a canonical decimal percent above 0, at most 100"
        if coupon.kind is CouponKind.AMOUNT and not is_money(coupon.value, zero=False):
            return f"an amount coupon of {coupon.value!r}: dollars with two decimals, above 0"
        problem = names_problem(coupon.items, "the coupon's items", items)
        if problem:
            return problem
    if len(receipt.treat) > 1:
        return f"the receipt treats {len(receipt.treat)} people: at most 1"
    if receipt.treat:
        return names_problem(receipt.treat, "the treat", receipt.people)
    return None


def shares_problem(total, shares):
    """What is wrong with a total and shares as written, or None (not whether they are right)."""
    if not is_money(total):
        return f"the total is {total!r}: dollars with two decimals, such as '23.41'"
    seen = set()
    for share in shares:
        if share.person in seen:
            return f"{share.person} has more than one share: give each person once"
        seen.add(share.person)
        if not is_money(share.owes):
            return f"{share.person} owes {share.owes!r}: dollars with two decimals, such as '23.41' or '0.00'"
    return None


def key_problem(key):
    """What is wrong with the answer key's data, or None (not yet whether its shares follow the rules)."""
    problem = receipt_problem(key) or shares_problem(key.total, key.shares)
    if problem:
        return problem
    if [share.person for share in key.shares] != key.people:
        return "the answer key's shares are not one per person, in the receipt's order"
    return None
