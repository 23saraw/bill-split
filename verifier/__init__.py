"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import calculate, even, load, receipt, rounding, task

TOOLS = {
    Tool.LOAD_RECEIPT: load,
    Tool.READ_RECEIPT: receipt,
    Tool.CALCULATE: calculate,
    Tool.EVEN_SPLIT: even,
    Tool.ROUND_EACH: rounding,
}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.SPLIT_BILL: task.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
