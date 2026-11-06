from __future__ import annotations

import copy
import json
import random

import pytest
from expected import RECEIPTS, answer
from slimconfig import build_output, plain_output

import verifier
from contract import (
    CalculateInput,
    CalculateOutput,
    EvenSplitOutput,
    KeyOutput,
    ReceiptInput,
    ReceiptOutput,
    RoundInput,
    RoundOutput,
    SplitOutput,
    Tool,
)
from plugin.bill import calculate, even_split, load_receipt, read_receipt, round_each

IDS = [
    "answer-key", "answer-key-rules", "submitted-receipt", "shares-shaped",
    "everyone-listed", "no-strangers", "total-exact", "shares-exact",
]


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def key_json(receipt: str) -> dict:
    return plain_output(load_receipt(ReceiptInput(receipt=receipt)))


def judge(receipt: str, submitted: dict, key: dict | None = None, arguments: str | None = None) -> dict:
    reference = build_output(key_json(receipt) if key is None else key, KeyOutput)
    given = build_output({"receipt": arguments or receipt}, ReceiptInput)
    return verifier.verify_task("split-bill", given, build_output(submitted, SplitOutput), reference, ".")


def failing(verdict: dict) -> list[str]:
    return [entry["id"] for entry in verdict["details"]["constraints"] if entry["ok"] is False]


def share(submitted: dict, person: str) -> dict:
    return next(entry for entry in submitted["shares"] if entry["person"] == person)


def test_every_tool_resolves_to_a_module_with_both_checks() -> None:
    # The host calls verify_input and verify_output on every tool call; a missing one only fails a real run.
    assert set(verifier.TOOLS) == set(Tool)
    for module in verifier.TOOLS.values():
        assert callable(module.verify_input) and callable(module.verify_output)


@pytest.mark.parametrize("receipt", sorted(RECEIPTS))
def test_the_hand_derived_answer_holds_every_constraint(receipt: str) -> None:
    verdict = judge(receipt, answer(receipt))
    assert verdict["valid"] is True and verdict["score"] == 1.0, verdict["message"]
    assert [entry["id"] for entry in verdict["details"]["constraints"]] == IDS


def test_order_does_not_matter_and_the_message_names_the_outcome() -> None:
    submitted = answer("dinner-4.json")
    submitted["shares"].reverse()
    assert judge("dinner-4.json", submitted)["message"] == "All 8 checks hold: 4 shares adding up to 55.10, Lena treated."
    assert judge("dinner-1.json", answer("dinner-1.json"))["message"] == "All 8 checks hold: 3 shares adding up to 53.03."


def test_each_tool_approves_its_own_real_output() -> None:
    receipt = build_output({"receipt": "dinner-2.json"}, ReceiptInput)
    expressions = build_output({"expressions": ["13 / 3 * 0.75", "10 / 3", "-2/3"]}, CalculateInput)
    amounts = build_output({"amounts": ["10403/300", "17.675", "0"]}, RoundInput)
    cases = [
        ("load_receipt", receipt, load_receipt(receipt), KeyOutput),
        ("read_receipt", receipt, read_receipt(receipt), ReceiptOutput),
        ("calculate", expressions, calculate(expressions), CalculateOutput),
        ("even_split", receipt, even_split(receipt), EvenSplitOutput),
        ("round_each", amounts, round_each(amounts), RoundOutput),
    ]
    for tool, given, made, cls in cases:
        assert verifier.verify_input(tool, given)["valid"] is True, tool
        verdict = verifier.verify_output(tool, given, build_output(plain_output(made), cls), ".")
        assert verdict["valid"] is True, (tool, verdict["message"])


# Wrong answers: the traps the receipts are built around.
def test_trusting_even_split_fails_shares_exact() -> None:
    submitted = {"receipt": "dinner-3.json", "total": "10.00", "shares": [
        {"person": person, "owes": "3.33"} for person in ("Hana", "Ivan", "Jo")
    ]}
    verdict = judge("dinner-3.json", submitted)
    assert failing(verdict) == ["shares-exact"]
    assert verdict["message"] == (
        "shares-exact: Hana is reported 3.33, but the rules give 3.34"
        " (exact ≈3.333333, 3.33 cut to the cent, plus the 1 leftover cent)"
    )
    assert verdict["score"] == pytest.approx(2 / 3)


def test_trusting_round_each_overshoots_the_total() -> None:
    submitted = answer("dinner-2.json")
    share(submitted, "Fay")["owes"] = "16.08"
    submitted["total"] = "89.88"
    verdict = judge("dinner-2.json", submitted)
    assert failing(verdict) == ["total-exact", "shares-exact"]
    assert verdict["message"] == (
        "total-exact: the total is reported 89.88, but the rules give 89.87 (the exact bill 89.87, rounded half up once)"
        " (+1 more)"
    )
    assert verdict["details"]["constraints"][7]["message"] == (
        "Fay is reported 16.08, but the rules give 16.07"
        " (exact ≈16.076667, cut to the cent; the 2 leftover cents go to larger remainders)"
    )
    assert verdict["score"] == pytest.approx(3 / 4)


def test_shares_that_do_not_add_up_to_the_total_say_so() -> None:
    submitted = answer("dinner-2.json")
    share(submitted, "Fay")["owes"] = "16.08"
    submitted["total"] = "89.86"
    assert judge("dinner-2.json", submitted)["details"]["constraints"][6]["message"].endswith(
        "; the shares submitted add up to 89.88"
    )


def test_tipping_after_the_coupon_fails() -> None:
    submitted = answer("dinner-2.json")
    share(submitted, "Dana")["owes"] = "32.96"  # 25.75 + 2.06 + 20% of 25.75
    verdict = judge("dinner-2.json", submitted)
    assert failing(verdict) == ["shares-exact"]
    assert verdict["message"] == (
        "shares-exact: Dana is reported 32.96, but the rules give 34.68"
        " (exact ≈34.676667, 34.67 cut to the cent, plus 1 of the 2 leftover cents)"
    )


def test_one_tax_rate_for_everything_fails() -> None:
    submitted = answer("dinner-2.json")
    share(submitted, "Gus")["owes"] = "15.36"  # the wine taxed at 8%
    verdict = judge("dinner-2.json", submitted)
    assert verdict["message"] == "shares-exact: Gus is reported 15.36, but the rules give 15.54 (exact 15.54)"


def test_an_uncapped_coupon_fails_the_total_and_the_share() -> None:
    submitted = answer("dinner-3.json")
    share(submitted, "Ivan")["owes"] = "2.33"  # 1.00 more off than the brownie cost
    submitted["total"] = "9.00"
    verdict = judge("dinner-3.json", submitted)
    assert failing(verdict) == ["total-exact", "shares-exact"]
    assert verdict["message"].startswith("total-exact: the total is reported 9.00, but the rules give 10.00 (the exact bill 10,")


def test_charging_the_treated_guest_fails() -> None:
    submitted = answer("dinner-4.json")
    share(submitted, "Lena")["owes"] = "17.41"
    verdict = judge("dinner-4.json", submitted)
    assert failing(verdict) == ["shares-exact"]
    assert verdict["message"] == (
        "shares-exact: Lena is reported 17.41, but the rules give 0.00"
        " (the group treats them: their share is split among everyone else)"
    )


# Missing and extra people.
def test_leaving_out_who_ate_nothing_fails() -> None:
    submitted = answer("dinner-4.json")
    submitted["shares"] = [entry for entry in submitted["shares"] if entry["person"] != "Noor"]
    verdict = judge("dinner-4.json", submitted)
    assert failing(verdict) == ["everyone-listed"]
    assert verdict["message"] == (
        "everyone-listed: Noor has no share: the rules give 5.80"
        " (exact ≈5.802222, cut to the cent; the 2 leftover cents go to larger remainders)"
    )
    assert verdict["score"] == pytest.approx(3 / 4)


def test_leaving_out_the_treated_guest_fails() -> None:
    submitted = answer("dinner-4.json")
    submitted["shares"] = [entry for entry in submitted["shares"] if entry["person"] != "Lena"]
    assert failing(judge("dinner-4.json", submitted)) == ["everyone-listed"]


def test_a_stranger_or_a_misspelt_name_fails() -> None:
    submitted = answer("dinner-1.json")
    submitted["shares"].append({"person": "Zed", "owes": "0.00"})
    verdict = judge("dinner-1.json", submitted)
    assert failing(verdict) == ["no-strangers"]
    assert verdict["message"] == "no-strangers: Zed has a share, but is not on the receipt"
    submitted = answer("dinner-1.json")
    share(submitted, "Ana")["person"] = "ana"
    assert failing(judge("dinner-1.json", submitted)) == ["everyone-listed", "no-strangers"]


def test_no_shares_at_all_scores_zero() -> None:
    verdict = judge("dinner-1.json", {"receipt": "dinner-1.json", "total": "53.03", "shares": []})
    assert failing(verdict) == ["everyone-listed"]
    assert verdict["score"] == 0.0


# Malformed: gates that score 0.
@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s.update(receipt="dinner-2.json"), "submitted-receipt: the submission is for 'dinner-2.json', not 'dinner-1.json'"),
        (lambda s: s.update(total="53.0"), "shares-shaped: the total is '53.0'"),
        (lambda s: s.update(total="53"), "shares-shaped: the total is '53'"),
        (lambda s: s.update(total="$53.03"), "shares-shaped: the total is '$53.03'"),
        (lambda s: share(s, "Ana").update(owes="20.2"), "shares-shaped: Ana owes '20.2'"),
        (lambda s: share(s, "Ana").update(owes="20.200"), "shares-shaped: Ana owes '20.200'"),
        (lambda s: share(s, "Ana").update(owes="-20.20"), "shares-shaped: Ana owes '-20.20'"),
        (lambda s: share(s, "Ana").update(owes=" 20.20"), "shares-shaped: Ana owes ' 20.20'"),
        (lambda s: share(s, "Ana").update(owes="020.20"), "shares-shaped: Ana owes '020.20'"),
        (lambda s: share(s, "Ana").update(owes="2.02e1"), "shares-shaped: Ana owes '2.02e1'"),
        (lambda s: s["shares"].append(dict(share(s, "Ana"))), "shares-shaped: Ana has more than one share"),
    ],
)
def test_a_malformed_submission_fails_its_gate_and_scores_zero(change, message: str) -> None:
    submitted = copy.deepcopy(answer("dinner-1.json"))
    change(submitted)
    verdict = judge("dinner-1.json", submitted)
    assert verdict["valid"] is False and verdict["score"] == 0.0
    assert verdict["message"].startswith(message), verdict["message"]
    later = verdict["details"]["constraints"][IDS.index(failing(verdict)[0]) + 1 :]
    assert all(entry["ok"] is None and entry["message"].startswith("Not checked") for entry in later)


def test_zero_is_written_with_two_decimals() -> None:
    submitted = answer("dinner-4.json")
    share(submitted, "Lena")["owes"] = "0"
    assert judge("dinner-4.json", submitted)["message"].startswith("shares-shaped: Lena owes '0'")


# The answer key.
def test_no_answer_key_fails_first() -> None:
    given = build_output({"receipt": "dinner-1.json"}, ReceiptInput)
    verdict = verifier.verify_task("split-bill", given, build_output(answer("dinner-1.json"), SplitOutput), None, ".")
    assert verdict["message"] == "answer-key: No answer key: load_receipt never ran for this task." and verdict["score"] == 0.0


def test_an_answer_key_for_another_receipt_fails() -> None:
    verdict = judge("dinner-1.json", answer("dinner-1.json"), arguments="dinner-2.json")
    assert verdict["message"] == "answer-key: The answer key is for 'dinner-1.json', not 'dinner-2.json'."


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda k: k["lines"][0].update(shared_by=["Zed"]), "answer-key: 'Pasta''s shared_by names 'Zed'"),
        (lambda k: k.update(tip="18.0"), "answer-key: tip is '18.0'"),
        (lambda k: k["shares"].reverse(), "answer-key: the answer key's shares are not one per person"),
        (lambda k: k.update(treat=["Ana", "Ben"]), "answer-key: the receipt treats 2 people"),
    ],
)
def test_a_malformed_answer_key_fails(change, message: str) -> None:
    key = key_json("dinner-1.json")
    change(key)
    assert judge("dinner-1.json", answer("dinner-1.json"), key=key)["message"].startswith(message)


def test_a_tampered_answer_key_fails_its_rules_check() -> None:
    key = key_json("dinner-2.json")
    key["shares"][2]["owes"] = "16.08"
    verdict = judge("dinner-2.json", answer("dinner-2.json"), key=key)
    assert failing(verdict) == ["answer-key-rules"]
    output = verifier.verify_output(
        "load_receipt", build_output({"receipt": "dinner-2.json"}, ReceiptInput), build_output(key, KeyOutput), "."
    )
    assert output["valid"] is False


# The tools' own checks.
@pytest.mark.parametrize(
    ("tool", "given", "cls"),
    [
        ("read_receipt", {"receipt": "../dinner-1.json"}, ReceiptInput),
        ("calculate", {"expressions": []}, CalculateInput),
        ("calculate", {"expressions": ["  "]}, CalculateInput),
        ("round_each", {"amounts": ["1/4"]}, RoundInput),
        ("round_each", {"amounts": ["-1"]}, RoundInput),
        ("round_each", {"amounts": []}, RoundInput),
    ],
)
def test_tool_inputs_are_checked(tool, given, cls) -> None:
    assert verifier.verify_input(tool, build_output(given, cls))["valid"] is False


@pytest.mark.parametrize(
    ("tool", "given", "made", "input_class", "cls"),
    [
        ("calculate", {"expressions": ["10/3"]}, {"values": [{"exact": "10/3", "approx": "3.333334"}]}, CalculateInput, CalculateOutput),
        ("calculate", {"expressions": ["1/4"]}, {"values": [{"exact": "1/4", "approx": "0.25"}]}, CalculateInput, CalculateOutput),
        ("calculate", {"expressions": ["2/4"]}, {"values": [{"exact": "2/6", "approx": "0.333333"}]}, CalculateInput, CalculateOutput),
        ("calculate", {"expressions": ["1", "2"]}, {"values": [{"exact": "1", "approx": "1"}]}, CalculateInput, CalculateOutput),
        (
            "even_split", {"receipt": "dinner-3.json"},
            {"receipt": "dinner-3.json", "people": ["Hana", "Ivan", "Jo"], "total": "10.00", "each": "3.34"},
            ReceiptInput, EvenSplitOutput,
        ),
        ("round_each", {"amounts": ["17.675"]}, {"rounded": ["17.67"]}, RoundInput, RoundOutput),
        ("round_each", {"amounts": ["2"]}, {"rounded": ["2"]}, RoundInput, RoundOutput),
        (
            "read_receipt", {"receipt": "dinner-1.json"},
            {**plain_output(read_receipt(ReceiptInput(receipt="dinner-1.json"))), "people": ["Ana"]},
            ReceiptInput, ReceiptOutput,
        ),
    ],
)
def test_a_wrong_tool_output_is_refused(tool, given, made, input_class, cls) -> None:
    verdict = verifier.verify_output(tool, build_output(given, input_class), build_output(made, cls), ".")
    assert verdict["valid"] is False


# Determinism, size and robustness.
def test_the_verdict_is_deterministic_and_small() -> None:
    empty = {"receipt": "dinner-2.json", "total": "0.00", "shares": []}
    first, second = judge("dinner-2.json", empty), judge("dinner-2.json", empty)
    assert first == second
    assert len(json.dumps(first)) < 8_000


def mutate(value, rng: random.Random):
    """``value`` with one random change somewhere inside it."""
    if isinstance(value, dict) and value:
        key = rng.choice(sorted(value))
        return {**value, key: mutate(value[key], rng)}
    if isinstance(value, list) and value and rng.random() < 0.7:
        index = rng.randrange(len(value))
        choice = rng.random()
        if choice < 0.3:
            return value[:index] + value[index + 1 :]
        if choice < 0.5:
            return [*value, copy.deepcopy(value[index])]
        return value[:index] + [mutate(value[index], rng)] + value[index + 1 :]
    # Mostly a value of the same type, so most mutations reach the verifier rather than build_output's refusal.
    same = {
        str: ["", "0", "0.00", "1", "3.34", "100", "101", "8.25", "-1.00", "Ana", "Kai", "Zed", "food", "alcohol",
              "percent", "amount", "Pizza", "dinner-1.json"],
        list: [[]],
    }.get(type(value))
    if same and rng.random() < 0.85:
        return rng.choice(same)
    return rng.choice([None, "", 0, True, []])


@pytest.mark.parametrize("receipt", sorted(RECEIPTS))
def test_a_mutated_submission_or_key_always_gets_a_verdict(receipt: str) -> None:
    rng = random.Random(receipt)
    checked = 0
    for _ in range(300):
        submitted, key = answer(receipt), key_json(receipt)
        for _ in range(rng.randint(1, 3)):
            if rng.random() < 0.6:
                submitted = mutate(submitted, rng)
            else:
                key = mutate(key, rng)
        try:
            built_output, built_key = build_output(submitted, SplitOutput), build_output(key, KeyOutput)
        except (TypeError, ValueError, KeyError):
            continue  # the sandbox refuses it before the verifier sees it
        given = build_output({"receipt": receipt}, ReceiptInput)
        verdict = verifier.verify_task("split-bill", given, built_output, built_key, ".")
        assert set(verdict) == {"valid", "score", "message", "details"}
        assert 0.0 <= verdict["score"] <= 1.0 and verdict["message"]
        json.dumps(verdict)
        checked += 1
    assert checked > 150
