"""load_receipt: the split-bill answer key."""

from .checks import key_problem, receipt_input, result
from .rules import judge
from .task import expected_shares, given_shares

verify_input = receipt_input


def verify_output(input_value, output_value, workspace):
    if output_value.receipt != input_value.receipt:
        return result(False, f"the answer key is for {output_value.receipt!r}, not {input_value.receipt!r}")
    problem = key_problem(output_value)
    if problem:
        return result(False, problem)
    if given_shares(output_value.total, output_value.shares) != expected_shares(judge(output_value)):
        return result(False, "the answer key's total or shares differ from the rules' recomputation")
    return result(True, "the answer key follows the rules", total=output_value.total, people=len(output_value.shares))
