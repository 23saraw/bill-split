"""calculate: exact arithmetic. Each value's approximation must be its exact value rounded to 6 places."""

import math
import re
from fractions import Fraction

from .checks import MAX_EXPRESSION, MAX_VALUES, result

EXACT = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?|-?[1-9][0-9]*/[1-9][0-9]*")
APPROX = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]{0,5}[1-9])?")


def read(text):
    """An exact value as calculate writes it, or None: a decimal when it ends, else a reduced 'p/q'."""
    if not EXACT.fullmatch(text) or text in ("-0",):
        return None
    if "/" not in text:
        return Fraction(text)
    value = Fraction(text)
    rest = value.denominator
    for prime in (2, 5):
        while rest % prime == 0:
            rest //= prime
    if f"{value.numerator}/{value.denominator}" != text or rest == 1:
        return None  # not reduced, or a decimal written as a fraction
    return value


def six_places(value):
    millionths = math.floor(abs(value) * 10**6 + Fraction(1, 2))
    return -millionths if value < 0 else millionths


def verify_input(value):
    if not 1 <= len(value.expressions) <= MAX_VALUES:
        return result(False, f"give 1 to {MAX_VALUES} expressions, not {len(value.expressions)}")
    for expression in value.expressions:
        if not expression.strip() or len(expression) > MAX_EXPRESSION:
            return result(False, f"an expression must be 1 to {MAX_EXPRESSION} characters, not {len(expression)}")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if len(output_value.values) != len(input_value.expressions):
        return result(False, "calculate gives one value per expression, and this is not that")
    for value in output_value.values:
        number = read(value.exact)
        if number is None:
            return result(False, f"{value.exact!r} is not an exact value as calculate writes it")
        if not APPROX.fullmatch(value.approx) or value.approx == "-0":
            return result(False, f"{value.approx!r} is not a canonical decimal with at most 6 places")
        if six_places(number) != six_places(Fraction(value.approx)):
            return result(False, f"{value.approx!r} is not {value.exact} rounded to 6 places")
    return result(True, "the expressions are worked out", values=len(output_value.values))
