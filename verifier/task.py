"""The split-bill task's verdict: 8 named constraints, in order. 1 to 4 guard the answer key and the
submission's integrity and score 0 when one fails; 5 to 8 judge the answer and score partially."""

from .checks import constraint, key_problem, result, shares_problem, summary
from .rules import cents, judge, money, shown

GATES = 4
TEXTS = [
    ("answer-key", "The answer key is this receipt's and well formed"),
    ("answer-key-rules", "The answer key's total and shares follow the rules, recomputed independently"),
    ("submitted-receipt", "The submission is for this receipt"),
    ("shares-shaped", "Every amount is dollars with two decimals, and each person has at most one share"),
    ("everyone-listed", "Everyone at the table has a share, even who owes nothing"),
    ("no-strangers", "Nobody has a share who is not on the receipt"),
    ("total-exact", "The total is the exact bill rounded half up to the cent, once"),
    ("shares-exact", "Each person's share is right to the cent"),
]


def expected_shares(outcome):
    return money(outcome["total"]), {person: money(entry["cents"]) for person, entry in outcome["people"].items()}


def given_shares(total, shares):
    return total, {share.person: share.owes for share in shares}


def why(person, outcome):
    """How a person's share follows: 'exact ≈23.576667, 23.57 cut to the cent, plus 1 of the 2 leftover cents'."""
    entry = outcome["people"][person]
    if entry["treated"]:
        return "the group treats them: their share is split among everyone else"
    text = f"exact {shown(entry['exact'])}"
    left = outcome["left"]
    if entry["extra"]:
        extra = "the 1 leftover cent" if left == 1 else f"1 of the {left} leftover cents"
        return f"{text}, {money(entry['floor'])} cut to the cent, plus {extra}"
    if entry["exact"] * 100 == entry["floor"]:
        return text
    if not left:
        return f"{text}, cut to the cent; no cents are left over"
    goes = "the 1 leftover cent goes to a larger remainder" if left == 1 else f"the {left} leftover cents go to larger remainders"
    return f"{text}, cut to the cent; {goes}"


def _first(problems):
    return problems[0] + (f" (and {len(problems) - 1} more)" if len(problems) > 1 else "") if problems else ""


def verify_task(arguments, output, reference, workspace):
    entries = []

    def add(index, ok, expected=None, actual=None, message=""):
        entries.append(constraint(*TEXTS[index], ok, expected, actual, message))
        return ok

    # 1 to 4: the gates.
    key = reference
    if key is None:
        problem = "No answer key: load_receipt never ran for this task."
    elif key.receipt != arguments.receipt:
        problem = f"The answer key is for {key.receipt!r}, not {arguments.receipt!r}."
    else:
        problem = key_problem(key)
    blocker = None if add(0, problem is None, message=problem or "") else TEXTS[0][0]
    outcome = None

    def rules_problem():
        nonlocal outcome
        outcome = judge(key)
        if given_shares(key.total, key.shares) != expected_shares(outcome):
            return "the answer key's total or shares differ from the rules' recomputation"
        return None

    gates = [
        rules_problem,
        lambda: None
        if output.receipt == arguments.receipt
        else f"the submission is for {output.receipt!r}, not {arguments.receipt!r}",
        lambda: shares_problem(output.total, output.shares),
    ]
    for index, check in enumerate(gates, 1):
        if blocker:
            entries.append(constraint(*TEXTS[index], None, message=f"Not checked: {blocker} did not hold."))
            continue
        problem = check()
        if not add(index, problem is None, message=problem or ""):
            blocker = TEXTS[index][0]
    if blocker:
        for index in range(GATES, len(TEXTS)):
            entries.append(constraint(*TEXTS[index], None, message=f"Not checked: {blocker} did not hold."))
        return result(False, summary(entries), score=0.0, constraints=entries)

    # 5 to 8: the answer, against the verifier's own recomputation.
    want_total, want = expected_shares(outcome)
    got_total, got = given_shares(output.total, output.shares)

    missing = [person for person in key.people if person not in got]
    add(
        4, not missing, [f"{p} {want[p]}" for p in missing], None,
        _first([f"{p} has no share: the rules give {want[p]} ({why(p, outcome)})" for p in missing]),
    )
    strangers = sorted(person for person in got if person not in want)
    add(5, not strangers, None, strangers, _first([f"{p} has a share, but is not on the receipt" for p in strangers]))
    summed = money(sum(cents(owes) for owes in got.values()))
    add(
        6, got_total == want_total, want_total, got_total,
        f"the total is reported {got_total}, but the rules give {want_total} (the exact bill"
        f" {shown(outcome['exact'])}, rounded half up once)"
        + ("" if summed == got_total else f"; the shares submitted add up to {summed}"),
    )
    wrong = [person for person in key.people if person in got and got[person] != want[person]]
    add(
        7, not wrong, [f"{p} {want[p]}" for p in wrong], [f"{p} {got[p]}" for p in wrong],
        _first([f"{p} is reported {got[p]}, but the rules give {want[p]} ({why(p, outcome)})" for p in wrong]),
    )

    if all(entry["ok"] for entry in entries):
        treated = "".join(f", {person} treated" for person in key.treat)
        message = f"All 8 checks hold: {len(want)} shares adding up to {want_total}{treated}."
        return result(True, message, constraints=entries)
    names = set(want) | set(got)
    right = sum(1 for person in names if person in want and got.get(person) == want[person])
    return result(False, summary(entries), score=min(right / len(names), 0.99), constraints=entries)
