"""Expected answers, derived by hand from the README's rules before any code ran. Never generate these."""

from __future__ import annotations

RECEIPTS = {
    # Pasta 14 Ana, Burger 12 Ben, Salad 10 Cleo, Fries 6 shared by all three (2 each); food tax 8.25%, tip 18%.
    # Ana 16 + 1.32 + 2.88 = 20.20. Ben 14 + 1.155 + 2.52 = 17.675. Cleo 12 + 0.99 + 2.16 = 15.15.
    # Exact sum 53.025 -> 53.03. Cut: 20.20 + 17.67 + 15.15 = 53.02; 1 cent left, Ben's half cent is the only
    # remainder: Ben 17.68.
    "dinner-1.json": ("53.03", {"Ana": "20.20", "Ben": "17.68", "Cleo": "15.15"}),
    # Nachos 13 by Dana, Eli, Fay (13/3 each); Steak 30 Dana; Tacos 15 Eli; House wine 2 x 9 = 18, alcohol, by Fay
    # and Gus (9 each); Soda 3 Gus. Food tax 8%, alcohol 10%, tip 20%; 25% off Steak and Nachos.
    # Nachos after the coupon: 13/3 x 0.75 = 3.25 each.
    # Dana: food 22.5 + 3.25 = 25.75, tax 2.06; tip 20% of 30 + 13/3 = 20.6/3. 27.81 + 6.8666... = 34.67666...
    # Eli: food 15 + 3.25 = 18.25, tax 1.46; tip 20% of 15 + 13/3 = 11.6/3. 19.71 + 3.8666... = 23.57666...
    # Fay: food 3.25 + 0.26 tax; wine 9 + 0.90 tax; tip 20% of 9 + 13/3 = 8/3. 13.41 + 2.6666... = 16.07666...
    # Gus: wine 9 + 0.90; soda 3 + 0.24; tip 20% of 12 = 2.40. 15.54.
    # Exact sum 89.87 (three 2/3-cent remainders make 2 cents). Cut: 34.67 + 23.57 + 16.07 + 15.54 = 89.85;
    # 2 cents left for a three-way tie at 2/3 cent: Dana and Eli, A to Z. Rounding each alone gives 89.88.
    "dinner-2.json": ("89.87", {"Dana": "34.68", "Eli": "23.58", "Fay": "16.07", "Gus": "15.54"}),
    # Pizza 10 by Hana, Ivan, Jo; Brownie 4 Ivan; 5.00 off the Brownie, capped at its 4.00; no tax, no tip.
    # Each owes 10/3 = 3.333...; total 10.00. Cut: 3 x 3.33 = 9.99; 1 cent left, a three-way tie: Hana.
    "dinner-3.json": ("10.00", {"Hana": "3.34", "Ivan": "3.33", "Jo": "3.33"}),
    # Curry 16 Kai; Birthday cake 8 by Kai, Lena, Mo (8/3 each); Beer 2 x 6 = 12, alcohol, Mo; Noodles 14 Lena.
    # Food tax 7.5%, alcohol 10%, tip 15%; 6.00 off Curry and Noodles (30 together): Curry -3.20, Noodles -2.80.
    # Kai: food 12.8 + 8/3 = 46.4/3, tax 3.48/3 = 1.16; tip 15% of 16 + 8/3 = 2.80. 58.28/3.
    # Lena: food 11.2 + 8/3 = 41.6/3, tax 1.04; tip 15% of 14 + 8/3 = 2.50. 52.22/3.
    # Mo: cake 8/3 + 0.20 tax; beer 12 + 1.20 tax; tip 15% of 12 + 8/3 = 2.20. 54.8/3.
    # Noor ate nothing: 0. Exact sum 165.3/3 = 55.10.
    # Lena is treated: 52.22/3 split among Kai, Mo and Noor, 52.22/9 each.
    # Kai 227.06/9 = 25.2288..., Mo 216.62/9 = 24.0688..., Noor 52.22/9 = 5.8022..., Lena 0.
    # Cut: 25.22 + 24.06 + 5.80 = 55.08; 2 cents left: Kai and Mo (8/9 cent each).
    "dinner-4.json": ("55.10", {"Kai": "25.23", "Lena": "0.00", "Mo": "24.07", "Noor": "5.80"}),
}


def answer(receipt: str) -> dict:
    """The right submission for ``receipt``, as JSON."""
    total, shares = RECEIPTS[receipt]
    return {"receipt": receipt, "total": total, "shares": [{"person": p, "owes": o} for p, o in shares.items()]}
