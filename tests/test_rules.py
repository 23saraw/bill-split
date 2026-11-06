"""Both implementations of the rules (the plugin's and the verifier's) against the hand-derived answers."""

from __future__ import annotations

from fractions import Fraction

import pytest
from expected import RECEIPTS

from contract import ReceiptInput
from plugin.bill import load, load_receipt
from plugin.rules import cents_text, exact_shares, split
from verifier import rules as verifier_rules


@pytest.mark.parametrize("receipt", sorted(RECEIPTS))
def test_the_plugin_splits_each_bill_as_derived_by_hand(receipt: str) -> None:
    total, cents = split(load(receipt))
    assert (cents_text(total), {person: cents_text(owed) for person, owed in cents.items()}) == RECEIPTS[receipt]


@pytest.mark.parametrize("receipt", sorted(RECEIPTS))
def test_the_verifier_splits_each_bill_as_derived_by_hand(receipt: str) -> None:
    outcome = verifier_rules.judge(load_receipt(ReceiptInput(receipt=receipt)))
    shares = {person: verifier_rules.money(entry["cents"]) for person, entry in outcome["people"].items()}
    assert (verifier_rules.money(outcome["total"]), shares) == RECEIPTS[receipt]


def test_both_implementations_agree_on_every_exact_amount() -> None:
    for receipt in RECEIPTS:
        outcome = verifier_rules.judge(load_receipt(ReceiptInput(receipt=receipt)))
        assert exact_shares(load(receipt)) == {person: entry["exact"] for person, entry in outcome["people"].items()}


def test_the_exact_amounts_behind_the_traps() -> None:
    dinner2 = exact_shares(load("dinner-2.json"))
    assert dinner2["Dana"] == Fraction("34.67") + Fraction(2, 300)  # the tip is on the cost before the coupon
    assert dinner2["Gus"] == Fraction("15.54")  # the wine is taxed at 10%, not 8%
    dinner3 = exact_shares(load("dinner-3.json"))
    assert dinner3["Ivan"] == Fraction(10, 3)  # 5.00 off a 4.00 brownie takes 4.00
    dinner4 = exact_shares(load("dinner-4.json"))
    assert dinner4["Lena"] == 0 and dinner4["Noor"] == Fraction("52.22") / 9  # the treat reaches who ate nothing
    assert sum(dinner4.values()) == Fraction("55.10")


def test_leftover_cents_go_to_the_largest_remainders_then_by_name() -> None:
    outcome = verifier_rules.judge(load_receipt(ReceiptInput(receipt="dinner-2.json")))
    assert outcome["left"] == 2
    assert [p for p, entry in outcome["people"].items() if entry["extra"]] == ["Dana", "Eli"]
    assert outcome["people"]["Fay"]["floor"] == 1607 and not outcome["people"]["Fay"]["extra"]


@pytest.mark.parametrize(
    ("value", "text"),
    [(Fraction("34.67"), "34.67"), (Fraction(10, 3), "≈3.333333"), (Fraction(0), "0"), (Fraction("17.675"), "17.675")],
)
def test_amounts_are_shown_exactly_when_they_end(value: Fraction, text: str) -> None:
    assert verifier_rules.shown(value) == text
