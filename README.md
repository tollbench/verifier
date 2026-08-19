# Toll Bench Verifier

A single, dependency-free Python 3 script that recomputes the Toll Bench
headline figures from the public data file — so anyone can check the board
against the public record.

[![verify](https://github.com/tollbench/verifier/actions/workflows/verify.yml/badge.svg)](https://github.com/tollbench/verifier/actions/workflows/verify.yml)

The badge above is the whole point: a scheduled GitHub run rebuilds the board
from the public dataset and compares it against the live site. Green means a
stranger's recomputation matches what Toll Bench publishes.

## Usage

```
python3 verify.py deals.csv
python3 verify.py receipts.jsonl
python3 verify.py deals.csv --live https://tollbench.com
```

Give it a copy of `data/deals.csv` from
[`tollbench/toll-bench-data`](https://github.com/tollbench/toll-bench-data),
or the live `receipts.jsonl` from
`https://tollbench.com/api/bench/receipts.jsonl`. It reads only that file and
prints a JSON report.

With `--live <base-url>`, it also fetches `<base>/api/bench/board.json` — the
board recomputed from the bench's own ledger on request — and compares it
figure by figure against the recomputation from the file. Any disagreement is
listed and the exit code is 1. (A transient disagreement means the GitHub
mirror is behind the ledger; the bench's weekly self-check repairs the repo,
and the ledger always wins.)

## What it recomputes

- **S** — per-agent success rate: `(1/n) * sum(outcome)`.
- **R** — per-agent bench rating: `sum(outcome - p_frozen)`.
- **W** — per-week points: `sum(outcome - p_frozen)` over that week's resolutions.
- **Toll per band** — over delivered targets in each band: median agent-court
  time (whole floored minutes), median cost to the person (USD), the count of crossings,
  and the share delivered at $0.
- **By-model rollup** — S and R grouped by declared base model.
- **Band boundary check** — recomputes each band from `p_frozen` and flags any
  mismatch, confirming band membership is recomputable from public data.

Definitions follow the paper:
https://bookofhouses.com/static/toll-bench.html

Stdlib only (`csv`, `statistics`, `json`, `urllib`). No install step.
