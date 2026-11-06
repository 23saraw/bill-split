"""read_receipt: the receipt as written."""

from .checks import receipt_input, receipt_problem, result

verify_input = receipt_input


def verify_output(input_value, output_value, workspace):
    if output_value.receipt != input_value.receipt:
        return result(False, f"read_receipt gave {output_value.receipt!r}, not {input_value.receipt!r}")
    problem = receipt_problem(output_value)
    if problem:
        return result(False, problem)
    return result(True, "the receipt is read", people=len(output_value.people), lines=len(output_value.lines))
