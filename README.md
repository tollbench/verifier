# Toll Bench Verifier

A single, dependency-free Python 3 script that recomputes the Toll Bench
headline figures from the public data file — so anyone can check the board
against the public record.

## Usage

```
python3 verify.py deals.csv
```

Give it a copy of `data/deals.csv` from
[`tollbench/toll-bench-data`](https://github.com/tollbench/toll-bench-data). It
reads only that file and prints a JSON report.

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

Stdlib only (`csv`, `statistics`, `json`). No install step.
