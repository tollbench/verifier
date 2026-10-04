#!/usr/bin/env python3
"""Independent Toll Bench public-v2 verifier. Standard library only.

Recomputes official S/R/W and Toll v3 from raw time/cost inputs, validates
eligibility metadata and bands, and compares the complete published aggregate.
Legacy files may be inspected with an older verifier but cannot produce a v2
verification pass. Never treats supplied final_toll as an input to its math.
"""
import argparse
import csv
import json
import math
import statistics
import urllib.request
from collections import defaultdict

SCHEMA = 'toll-bench.public.v2'
FORMULA = 'time-cost.v3'
LIVE_KEYS = ('row_count', 'scored_row_count', 'by_agent', 'by_week', 'by_band', 'by_model')


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def band_of(p):
    return 'short' if p >= .5 else 'long' if p >= .15 else 'moonshot'


def load(path):
    with open(path, encoding='utf-8', newline='') as handle:
        if path.endswith('.jsonl'):
            return [json.loads(line) for line in handle if line.strip()]
        return list(csv.DictReader(handle))


def verify(rows):
    out = dict(row_count=len(rows), scored_row_count=0, by_agent={}, by_week={}, by_band={}, by_model={})
    errors = []
    scored = []
    for index, row in enumerate(rows):
        label = row.get('deal_id') or str(index)
        if row.get('schema_version') != SCHEMA:
            errors.append(f'{label}: missing or unsupported schema_version')
            continue
        flag = row.get('is_scored')
        if flag not in (True, False, 'true', 'false'):
            errors.append(f'{label}: missing or invalid is_scored')
            continue
        eligible = flag is True or flag == 'true'
        if eligible and row.get('integrity_state') != 'official':
            errors.append(f'{label}: scored row is not official')
            continue
        if eligible and row.get('resolution') in ('lapsed', 'withdrawn'):
            errors.append(f'{label}: neutral outcome marked scored')
            continue
        if not eligible:
            continue
        outcome = number(row.get('outcome'))
        p = number(row.get('p_frozen'))
        if outcome not in (0, 1):
            errors.append(f'{label}: outcome must be 0 or 1')
            continue
        if p is not None and (not 0 <= p <= 1 or band_of(p) != row.get('band')):
            errors.append(f'{label}: probability/band mismatch')
        if not row.get('week_resolved'):
            errors.append(f'{label}: scored outcome has no resolution week')
        if row.get('model_attribution') == 'unavailable' and row.get('model') not in ('', 'undeclared'):
            errors.append(f'{label}: model attributed without frozen provenance')
        scored.append(row)
    out['scored_row_count'] = len(scored)
    for field, dest, missing in [('agent', 'by_agent', '(unknown)'), ('model', 'by_model', '(undeclared)')]:
        groups = defaultdict(list)
        for row in scored:
            groups[row.get(field) or missing].append(row)
        for key, group in groups.items():
            wins = sum(number(r['outcome']) for r in group)
            points = sum(number(r['outcome']) - number(r['p_frozen']) for r in group if number(r.get('p_frozen')) is not None)
            out[dest][key] = dict(n=len(group), S=round(wins/len(group), 4), R=round(points, 4))
    weeks = defaultdict(float)
    bands = defaultdict(list)
    for row in scored:
        o, p = number(row['outcome']), number(row.get('p_frozen'))
        if p is not None:
            weeks[row.get('week_resolved') or '(none)'] += o-p
        if o == 1:
            bands[row.get('band') or '(unbanded)'].append(row)
    out['by_week'] = {k:round(v,4) for k,v in sorted(weeks.items())}
    def median(values, digits):
        return round(statistics.median(values), digits) if values else None
    for band, group in bands.items():
        times = [number(r.get('T_agent_minutes')) for r in group if number(r.get('T_agent_minutes')) is not None]
        costs = [number(r.get('C_usd')) for r in group if number(r.get('C_usd')) is not None]
        dollars, days, tolls = [], [], []
        for row in group:
            cents, day = number(row.get('toll_dollars_cents')), number(row.get('toll_days'))
            if row.get('toll_formula_version') != FORMULA or cents is None or day is None:
                errors.append(f"{row.get('deal_id')}: incomplete or unsupported Toll inputs")
                continue
            if cents < 0 or day < 0:
                errors.append(f"{row.get('deal_id')}: negative Toll input")
                continue
            calculated = round(math.log2(1+cents/5000) + math.log2(1+day/3), 2)
            if number(row.get('final_toll')) != calculated:
                errors.append(f"{row.get('deal_id')}: final_toll differs from raw-input calculation")
            if number(row.get('C_usd')) != round(cents/100, 2):
                errors.append(f"{row.get('deal_id')}: cost differs from Toll cost input")
            dollars.append(cents/100)
            days.append(day)
            tolls.append(calculated)
        out['by_band'][band] = dict(
            crossings=len(group), median_agent_minutes=median(times,2), median_cost_usd=median(costs,2),
            free_share=round(sum(number(r.get('C_usd'))==0 for r in group)/len(group),4),
            median_toll=median(tolls,2), median_toll_n=len(tolls),
            median_dollars_usd=median(dollars,2), median_dollars_n=len(dollars),
            median_agent_days=median([t/1440 for t in times],4), median_agent_days_n=len(times),
            median_toll_days=median(days,6), median_toll_days_n=len(days), toll_formula_version=FORMULA)
    return out, errors


def differences(left, right, path=''):
    if isinstance(left,dict) and isinstance(right,dict):
        return [d for key in sorted(set(left)|set(right)) for d in differences(left.get(key),right.get(key),f'{path}.{key}')]
    if number(left) is not None and number(right) is not None and abs(number(left)-number(right)) < 1e-6:
        return []
    return [] if left == right else [f'{path}: calculated={left!r} published={right!r}']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data',help='receipts.jsonl or deals.csv')
    parser.add_argument('--live',help='base URL whose /api/bench/board.json is compared')
    parser.add_argument('--board-file',help='compare a saved board.json snapshot')
    args=parser.parse_args()
    rows=load(args.data)
    report,errors=verify(rows)
    live=None
    if args.live:
        with urllib.request.urlopen(args.live.rstrip('/')+'/api/bench/board.json',timeout=30) as response:
            live=json.load(response)
    elif args.board_file:
        with open(args.board_file,encoding='utf-8') as handle:
            live=json.load(handle)
    if live is not None:
        if live.get('schema_version') != SCHEMA or live.get('toll_formula_version') != FORMULA:
            errors.append('published board has an unsupported schema or formula version')
        for key in LIVE_KEYS:
            errors.extend(differences(report.get(key),live.get(key),key))
    print(json.dumps(dict(status='FAIL' if errors else 'PASS', aggregates=report, errors=errors),indent=2,sort_keys=True))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
