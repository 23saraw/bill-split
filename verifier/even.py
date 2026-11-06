"""even_split: a distractor; it divides the total equally, which the rules never do."""

import math
from fractions import Fraction

from .checks import is_money, names_problem, receipt_input, result
from .rules import cents

verify_input = receipt_input


def verify_output(input_value, output_value, workspace):
    if output_value.receipt != input_value.receipt:
        return result(False, f"even_split gave {output_value.receipt!r}, not {input_value.receipt!r}")
    problem = names_problem(output_value.people, "people")
    if problem:
        return result(False, problem)
    for text in (output_value.total, output_value.each):
        if not is_money(text):
            return result(False, f"{text!r} is not dollars with two decimals")
    if cents(output_value.each) != math.floor(Fraction(cents(output_value.total), len(output_value.people)) + Fraction(1, 2)):
        return result(False, f"{output_value.each} is not {output_value.total} divided by {len(output_value.people)}")
    return result(True, "the total is divided equally", people=len(output_value.people))
