from __future__ import annotations

import json

import pytest

from contract import CalculateInput, CouponKind, Kind, ReceiptInput, RoundInput
from plugin import bill
from plugin.bill import calculate, even_split, load_receipt, read_receipt, round_each


def test_read_receipt_gives_the_receipt_as_written() -> None:
    receipt = read_receipt(ReceiptInput(receipt="dinner-2.json"))
    assert receipt.people == ["Dana", "Eli", "Fay", "Gus"]
    wine = receipt.lines[3]
    assert (wine.item, wine.price, wine.qty, wine.kind, wine.shared_by) == ("House wine", "9.00", "2", Kind.ALCOHOL, ["Fay", "Gus"])
    assert [(c.kind, c.value, c.items) for c in receipt.coupons] == [(CouponKind.PERCENT, "25", ["Steak", "Nachos"])]
    assert read_receipt(ReceiptInput(receipt="dinner-4.json")).treat == ["Lena"]


def test_the_answer_key_and_the_agent_tool_agree() -> None:
    key = load_receipt(ReceiptInput(receipt="dinner-4.json"))
    read = read_receipt(ReceiptInput(receipt="dinner-4.json"))
    assert (key.people, key.lines, key.coupons, key.treat, key.tip) == (read.people, read.lines, read.coupons, read.treat, read.tip)
    assert [share.person for share in key.shares] == key.people


@pytest.mark.parametrize(
    ("expression", "exact", "approx"),
    [
        ("(13 / 3) * 0.75", "3.25", "3.25"),
        ("10 / 3", "10/3", "3.333333"),
        ("-2 / 3", "-2/3", "-0.666667"),
        ("2 - 5 * (1 + 1)", "-8", "-8"),
        ("17.675 * 100", "1767.5", "1767.5"),
        ("0.0000004", "0.0000004", "0"),
        (" 1 ", "1", "1"),
        ("--1", "1", "1"),
    ],
)
def test_calculate_is_exact(expression: str, exact: str, approx: str) -> None:
    [value] = calculate(CalculateInput(expressions=[expression])).values
    assert (value.exact, value.approx) == (exact, approx)


@pytest.mark.parametrize(
    ("expression", "match"),
    [
        ("1 / 0", "divides by zero"),
        ("1 / (2 - 2)", "divides by zero"),
        ("(1 + 2", "unclosed"),
        ("1 + 2)", "where it should end"),
        ("2 ** 3", "a number or"),
        ("1e3", "only numbers"),
        ("abs(1)", "only numbers"),
        ("", "1 to 400"),
        ("1+" * 300, "1 to 400"),
    ],
)
def test_calculate_refuses_what_is_not_arithmetic(expression: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        calculate(CalculateInput(expressions=[expression]))


def test_even_split_divides_the_rounded_total_equally() -> None:
    split = even_split(ReceiptInput(receipt="dinner-3.json"))
    assert (split.total, split.each, split.people) == ("10.00", "3.33", ["Hana", "Ivan", "Jo"])
    assert even_split(ReceiptInput(receipt="dinner-4.json")).each == "13.78"  # 55.10 / 4 = 13.775, half up


def test_round_each_rounds_half_up_on_its_own() -> None:
    assert round_each(RoundInput(amounts=["10403/300", "17.675", "0", "13/3"])).rounded == ["34.68", "17.68", "0.00", "4.33"]
    for bad in ["-1", "1/4", "2/4", "1.50", "abc", "13/1"]:
        with pytest.raises(ValueError, match="as calculate writes it"):
            round_each(RoundInput(amounts=[bad]))


@pytest.mark.parametrize(
    ("call", "error"),
    [
        (lambda: read_receipt(ReceiptInput(receipt="../dinner-1.json")), ValueError),
        (lambda: read_receipt(ReceiptInput(receipt="dinner-9.json")), FileNotFoundError),
        (lambda: even_split(ReceiptInput(receipt="Dinner-1.json")), ValueError),
    ],
)
def test_unknown_receipts_raise(call, error: type[Exception]) -> None:
    with pytest.raises(error):
        call()


GOOD = {
    "people": ["A", "B"],
    "lines": [{"item": "Soup", "price": "4.00", "qty": "1", "kind": "food", "shared_by": ["A"]}],
    "food_tax": "8",
    "alcohol_tax": "10",
    "tip": "15",
    "coupons": [],
    "treat": [],
}


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"people": ["A"]}, "at least 2 people"),
        ({"people": ["A", "A"]}, "twice"),
        ({"people": ["A", " B"]}, "trimmed"),
        ({"lines": [{**GOOD["lines"][0], "price": "4"}]}, "two decimals"),
        ({"lines": [{**GOOD["lines"][0], "price": "0.00"}]}, "above 0"),
        ({"lines": [{**GOOD["lines"][0], "qty": "0"}]}, "at least 1"),
        ({"lines": [{**GOOD["lines"][0], "shared_by": ["C"]}]}, "not on the receipt"),
        ({"lines": [{**GOOD["lines"][0], "shared_by": []}]}, "non-empty"),
        ({"lines": [GOOD["lines"][0], GOOD["lines"][0]]}, "twice"),
        ({"tip": "101"}, "0 to 100"),
        ({"food_tax": "8.0"}, "canonical"),
        ({"coupons": [{"kind": "percent", "value": "0", "items": ["Soup"]}]}, "above 0"),
        ({"coupons": [{"kind": "amount", "value": "5", "items": ["Soup"]}]}, "two decimals"),
        ({"coupons": [{"kind": "amount", "value": "5.00", "items": ["Bread"]}]}, "not on the receipt"),
        ({"coupons": [{"kind": "amount", "value": "5.00", "items": ["Soup"]}] * 2}, "at most 1"),
        ({"treat": ["C"]}, "not on the receipt"),
        ({"treat": ["A", "B"]}, "at most 1"),
    ],
)
def test_a_bad_receipt_file_raises(tmp_path, monkeypatch, change: dict, match: str) -> None:
    (tmp_path / "receipts").mkdir()
    (tmp_path / "receipts" / "bad.json").write_text(json.dumps({**GOOD, **change}))
    monkeypatch.setattr(bill, "DATA", tmp_path)
    with pytest.raises(ValueError, match=match):
        read_receipt(ReceiptInput(receipt="bad.json"))
