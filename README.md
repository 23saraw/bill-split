# Bill Splitter

A `nanoagent.plugin/v0001` plugin. Its task, `split-bill`, has an agent split a
group dinner's bill to the cent: given a bundled receipt (who was at the
table, each line's price, quantity, kind and who shared it, the food and
alcohol tax rates, the tip, a coupon and a treated guest), it works out what
each person owes, and the total. No network. Every number is a decimal
string, and every computation is exact (`Fraction`, never floats). The
verifier recomputes the bill in its own code and judges every share.

## Tools

| Tool | Does | Code |
|---|---|---|
| `load_receipt` | The answer key: the receipt, its total and each person's share under the rules. The agent never sees it | `src/plugin/bill.py`, `src/plugin/rules.py` |
| `read_receipt` | A receipt's people, lines (item, price, qty, food or alcohol, shared_by), tax rates, tip, coupon and treat, exactly as written | `src/plugin/bill.py` |
| `calculate` | Exact arithmetic: decimal numbers, `+ - * /` and parentheses, each result as an exact decimal or fraction (`13/3`) and rounded to 6 places | `src/plugin/bill.py` |
| `even_split` | A distractor: the rounded total divided equally among everyone, half up to the cent. True about itself, but rules 1 and 7 never split evenly | `src/plugin/bill.py` |
| `round_each` | A distractor: rounds each amount on its own, half up to the cent. True about itself, but rule 7 cuts down and hands out leftover cents, so rounded shares can miss the total | `src/plugin/bill.py` |

No tool splits, discounts, taxes, tips or hands out cents: the agent applies
the rules itself. Its plan is `read_receipt`, one or two `calculate` calls
with many expressions each, then `submit`.

### Tasks

| Task | Does | Runner |
|---|---|---|
| `split-bill` | Splits a bundled receipt's bill to the cent: each person's share and the total | `agent`, with `read_receipt`, `calculate`, `even_split` and `round_each`; reference `load_receipt` |

## The rules

1. **Lines.** A line costs price × qty. Its cost is split equally among only
   the people in its `shared_by`.
2. **Coupon** (at most one). A `percent` coupon takes `value` percent off
   each item it names. An `amount` coupon takes `value` dollars off the
   items it names together, but never more than they cost together, spread
   over those items in proportion to their cost.
3. **Tax.** Each line is taxed at its kind's rate (`food_tax` or
   `alcohol_tax`) on its cost after the coupon.
4. **Tip.** The tip is the `tip` percent of each line's cost *before* the
   coupon and before tax.
5. **Shares.** Each person owes their part of every line they share: the
   line's cost after the coupon, plus its tax, plus its tip, divided among
   its `shared_by`.
6. **Treat.** A treated person owes 0.00, and what they would have owed is
   split equally among everyone else at the table, including anyone who ate
   nothing.
7. **Rounding.** The total is the exact sum of everyone's amounts, rounded
   half up to the cent, once. Each person's exact amount is cut down to the
   cent; the cents still missing from the total go one each to the people
   with the largest cut-off remainders, ties going to the name first in A to
   Z order (plain character order). The shares then add up to the total
   exactly. Nothing is rounded before this rule.
8. **The submission.** One share per person at the table, named exactly as
   on the receipt, including anyone who owes 0.00. Order does not matter.
   Every amount is dollars with exactly two decimals: `"23.41"` and
   `"0.00"`, not `"23.4"`, `"0"`, `"$23.41"` or `" 23.41"`.

## Receipts

The bundled receipts, in `src/plugin/data/receipts/`, each built around
traps. The expectations were derived by hand (`tests/expected.py`) and both
implementations are tested against them.

**dinner-1:** Pasta 14 (Ana), Burger 12 (Ben), Salad 10 (Cleo), Fries 6
(all three); food tax 8.25%, tip 18%; no coupon.

| Person | Working | Owes |
|---|---|---|
| Ana | 16 + 1.32 tax + 2.88 tip | 20.20 |
| Ben | 14 + 1.155 + 2.52 = 17.675 | 17.68 (the 1 leftover cent) |
| Cleo | 12 + 0.99 + 2.16 | 15.15 |
| Total | 53.025, rounded once | 53.03 |

**dinner-2:** Nachos 13 (Dana, Eli, Fay), Steak 30 (Dana), Tacos 15 (Eli),
House wine 2 × 9 alcohol (Fay, Gus), Soda 3 (Gus); food tax 8%, alcohol 10%,
tip 20%; 25% off Steak and Nachos.

| Person | Working | Owes |
|---|---|---|
| Dana | 25.75 after the coupon + 2.06 tax + 20% of 34.333… before it | 34.676… → 34.68 |
| Eli | 18.25 + 1.46 + 20% of 19.333… | 23.576… → 23.58 |
| Fay | 3.25 + 0.26 (food) + 9 + 0.90 (wine at 10%) + 20% of 13.333… | 16.076… → 16.07 |
| Gus | 9 + 0.90 + 3 + 0.24 + 2.40 | 15.54 |
| Total | 89.87; 2 leftover cents, a three-way tie at ⅔ cent: Dana, Eli | 89.87 |

Rounding each share on its own gives 89.88; tipping after the coupon gives
Dana 32.96; one tax rate for everything gives Gus 15.36.

**dinner-3:** Pizza 10 (Hana, Ivan, Jo), Brownie 4 (Ivan); 5.00 off the
Brownie; no tax, 0% tip. The coupon takes only the brownie's 4.00, so each
owes 10/3; 1 leftover cent in a three-way tie goes to Hana: 3.34, 3.33,
3.33, total 10.00. Splitting evenly gives 3.33 each; an uncapped coupon
gives a 9.00 total.

**dinner-4:** Curry 16 (Kai), Birthday cake 8 (Kai, Lena, Mo), Beer 2 × 6
alcohol (Mo), Noodles 14 (Lena); Noor ate nothing; food tax 7.5%, alcohol
10%, tip 15%; 6.00 off Curry and Noodles; Lena is treated.

| Person | Working | Owes |
|---|---|---|
| Kai | 58.28/3 own (the coupon takes 3.20 off the curry) + 52.22/9 of Lena's | 25.228… → 25.23 |
| Lena | treated: their 52.22/3 goes to Kai, Mo and Noor | 0.00 |
| Mo | 54.8/3 own + 52.22/9 | 24.068… → 24.07 |
| Noor | ate nothing; 52.22/9 of Lena's | 5.802… → 5.80 |
| Total | 55.10; 2 leftover cents: Kai and Mo | 55.10 |

## Constraints

`verifier/task.py` judges the submission against 8 constraints, in order.
Every entry of the verdict's `details.constraints` has the keys
`{id, constraint, ok, expected, actual, message}`; `ok` is `true`, `false`, or
`null` when a check it needs did not hold.

| # | id | What it checks | Example failure message |
|---|---|---|---|
| 1 | `answer-key` | The answer key is this receipt's and well formed: known people, canonical prices and rates, at most one coupon and one treat | 'Pasta''s shared_by names 'Zed', who or which is not on the receipt |
| 2 | `answer-key-rules` | The key's total and shares equal the verifier's own recomputation | the answer key's total or shares differ from the rules' recomputation |
| 3 | `submitted-receipt` | The submission is for this receipt | the submission is for 'dinner-2.json', not 'dinner-1.json' |
| 4 | `shares-shaped` | Every amount is dollars with two decimals, and each person has at most one share | Ana owes '20.2': dollars with two decimals, such as '23.41' or '0.00' |
| 5 | `everyone-listed` | Everyone at the table has a share, even who owes nothing | Noor has no share: the rules give 5.80 (exact ≈5.802222, cut to the cent; the 2 leftover cents go to larger remainders) |
| 6 | `no-strangers` | Nobody has a share who is not on the receipt | Zed has a share, but is not on the receipt |
| 7 | `total-exact` | The total is the exact bill rounded half up to the cent, once | the total is reported 89.88, but the rules give 89.87 (the exact bill 89.87, rounded half up once) |
| 8 | `shares-exact` | Each person's share is right to the cent | Hana is reported 3.33, but the rules give 3.34 (exact ≈3.333333, 3.33 cut to the cent, plus the 1 leftover cent) |

How it is scored:

- **Valid** only when all 8 hold; the score is then 1.0.
- **Score 0** when any of 1 to 4 fails: they guard the answer key and the submission's integrity.
- **Otherwise** the score is the share of people (expected or submitted) whose share is exactly right, at most 0.99.
- **The message** names the first failing constraint, why, and how many more fail.

`verifier/rules.py` is a second implementation of the rules that shares no
code with `src/plugin/rules.py`: the plugin charges line by line, applying
the coupon to each line; the verifier works person by person, keeping each
person's food and alcohol apart and spreading the coupon by each person's
eligible spend, and reads numbers through `Decimal`. Constraint 2 checks that
the answer key agrees with it, so a wrong rule would have to be written the
same wrong way twice to pass. Every tool call is checked as well:
`verify_input` refuses a malformed receipt name, an empty or oversized list
and an amount `calculate` would not write, and `verify_output` holds each
tool's output to what it promises (`calculate`'s approximation is its exact
value rounded, `even_split`'s share is its total divided, `round_each`'s
amounts are rounded half up).

## Limitations

- **Only the bundled receipts.** The task input names one of the receipts in
  `src/plugin/data/receipts/`; a person cannot bring a receipt of their own.
- **No provenance gate.** The plugin writes no files, so the verifier cannot
  prove the agent called the tools. The answer depends on data only the tools
  give, so a correct answer without them would be a guess.
- **One convention among many.** Real groups tip on the bill after the
  coupon, round each person up, or settle by who paid. The rules pin one
  convention so there is exactly one right answer; they do not claim it is
  the only fair one.
- **No settling up.** The plugin says what each person owes the bill, not who
  pays whom.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (none), tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable names this plugin needs (none)
├── src/plugin/      # the MCP server (__main__.py), the tools (bill.py), the rules (rules.py)
│   └── data/        # receipts/, the bundled receipts
├── tests/           # hand-derived answers (expected.py), both rule implementations, the tools, the verifier
├── ui/              # how the page draws outputs: drawn from the JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier: one module per tool, rules.py, and the task's 8 constraints in task.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv lock --check
```

With the `nanoagent` CLI installed in a separate environment:

```bash
nanoagent plugin inspect .                        # every plugin rule
nanoagent plugin agent config=run.yaml home=out   # the agent task; needs OPENROUTER_API_KEY
```

A `run.yaml` for one receipt (`args.json` holds the task input, e.g.
`{"receipt": "dinner-1.json"}`; give `plugin` and `arguments` as absolute
paths). The run folder gets `result.json`, `reference.json`,
`messages.json` and `verdict.json`, and the command exits 1 unless the
verdict is valid:

```yaml
_ > nanoagent.cli.plugin.PluginOpenRouterAgentConfig:
plugin: /path/to/bill-split
task: split-bill
arguments: /path/to/args.json
inputs: []
timeout: 60
llm > nanoagent.llm.openrouter.OpenRouterConfig:
  model: deepseek/deepseek-v4-flash-0731
  max_tokens: null
  temperature: null
  max_attempts: 3
  read_timeout: 180
  input_price: 0.0
  output_price: 0.0
harness > nanoagent.harness.nanoagent.NanoAgentConfig:
  max_steps: 8
  cost_limit: null
  token_limit: null
  context_window: null
  hooks: []
  skills: null
  context_files: []
  events: null
```

The correct- and incorrect-answer checks run without a model; each trap
above has its own test, and its verdict message names the share and why:

```bash
uv run pytest tests/test_verifier.py -v -k "hand_derived or trusting or tipping or tax_rate or uncapped or treated"
```
