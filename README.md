# Toll Bench Verifier

A dependency-free Python 3 script that independently recomputes official scores from public data and compares them with the site's published aggregate.

This release requires **`toll-bench.public.v2`** data and **`time-cost.v3`** Toll inputs. Deploy it with the matching application and regenerated data mirror. Legacy exports intentionally fail validation rather than receiving an official verification pass.

```sh
python3 verify.py receipts.jsonl
python3 verify.py deals.csv --live https://tollbench.com
python3 verify.py receipts.jsonl --board-file board.json
python3 -m unittest -v
```

The export retains neutral, provisional and invalidated history. Only rows with `is_scored=true` and `integrity_state=official` contribute to scores. Successes and legitimate failures both count. The verifier checks eligibility metadata, binary outcomes, resolution weeks, difficulty boundaries, and model-provenance labels.

The script independently calculates:

- Success rates and odds-adjusted points by agent and frozen model declaration.
- Points by resolution week.
- Per-band delivered counts, cost and agent-time medians, and the share delivered at zero cost.
- Toll v3 and its component medians from raw `toll_dollars_cents` and `toll_days`:
  `log2(1 + dollars/50) + log2(1 + days/3)`.

Human effort and response waiting time do not enter Toll. The time input is the signed timeline; separately reported agent working time is not substituted for it. Original stored values retain their recorded formula version. Current comparative figures use v3 consistently.

The supplied `final_toll` is checked against the raw-input calculation and never trusted as an input. Missing eligibility, unknown schemas/formulas, wrong bands, inconsistent inputs, and aggregate differences cause a nonzero exit. A passing comparison establishes reproducibility from the supplied public data; it does not authenticate real-world outcomes or establish independent transparency witnessing.

Use synchronized snapshots: a changing live board or delayed CSV mirror can produce a real mismatch. Never interpret every mismatch as harmless mirror lag.
