"""round_each: a distractor; it rounds each amount on its own, so the shares need not add up to the total."""

import math
from fractions import Fraction

from .calculate import read
from .checks import MAX_VALUES, is_money, result
from .rules import cents


def verify_input(value):
    if not 1 <= len(value.amounts) <= MAX_VALUES:
        return result(False, f"give 1 to {MAX_VALUES} amounts, not {len(value.amounts)}")
    for text in value.amounts:
        number = read(text)
        if number is None or number < 0:
            return result(False, f"{text!r} is not a non-negative amount as calculate writes it ('4.335' or '13/3')")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if len(output_value.rounded) != len(input_value.amounts):
        return result(False, "round_each gives one amount per amount, and this is not that")
    for text, rounded in zip(input_value.amounts, output_value.rounded):
        number = read(text)
        if number is None or not is_money(rounded) or cents(rounded) != math.floor(number * 100 + Fraction(1, 2)):
            return result(False, f"{rounded!r} is not {text} rounded half up to the cent")
    return result(True, "the amounts are rounded", amounts=len(output_value.rounded))
