#!/usr/bin/env python3
"""Toll Bench verifier (spec v1, §10).

Reads ONLY the public file data/deals.csv and recomputes every headline figure
from it, so anyone can check the board against the public record. Stdlib only.

Usage:
    python3 verify.py deals.csv

Definitions (from the paper, https://bookofhouses.com/static/toll-bench.html):
  S  success rate per agent      = (1/n) * sum(outcome)              [eq. 2]
  R  bench rating per agent      = sum(outcome - p_frozen)           [eq. 3]
  W  week points per week        = sum(outcome - p_frozen) over that week's
                                    resolutions                       [eq. 10]
  Toll per band (over DELIVERED targets in the band):
       median agent-court time in whole floored minutes,
       median cost to the person in USD,
       count of crossings, and share delivered at $0 (free share).

Bands are recomputable from the frozen probability (short/long/moonshot). This
script trusts the band already in the file (it is defined directly on p_frozen
and published), and independently checks the boundary where p_frozen is present.
"""
import csv
import json
import statistics
import sys


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def band_of(p):
    """short: p >= 0.50 / long: 0.15 <= p < 0.50 / moonshot: p < 0.15."""
    if p is None:
        return None
    if p >= 0.50:
        return 'short'
    if p >= 0.15:
        return 'long'
    return 'moonshot'


def load(path):
    with open(path, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def verify(rows):
    out = {'row_count': len(rows), 'by_agent': {}, 'by_week': {},
           'by_band': {}, 'by_model': {}, 'band_check': []}

    # Per agent: S and R over every accepted (resolved) target.
    agents = {}
    for r in rows:
        a = r.get('agent') or '(unknown)'
        o = _f(r.get('outcome'))
        p = _f(r.get('p_frozen'))
        if o is None:
            continue
        d = agents.setdefault(a, {'n': 0, 'sum_o': 0.0, 'R': 0.0})
        d['n'] += 1
        d['sum_o'] += o
        if p is not None:
            d['R'] += (o - p)
    for a, d in agents.items():
        out['by_agent'][a] = {
            'n': d['n'],
            'S': round(d['sum_o'] / d['n'], 4) if d['n'] else None,
            'R': round(d['R'], 4),
        }

    # Per week: W = sum(o - p) over that week's resolutions.
    weeks = {}
    for r in rows:
        wk = r.get('week_resolved') or '(none)'
        o = _f(r.get('outcome'))
        p = _f(r.get('p_frozen'))
        if o is None or p is None:
            continue
        weeks[wk] = weeks.get(wk, 0.0) + (o - p)
    out['by_week'] = {k: round(v, 4) for k, v in sorted(weeks.items())}

    # Per band: the Toll over DELIVERED targets (outcome == 1).
    bands = {}
    for r in rows:
        b = r.get('band') or '(unbanded)'
        o = _f(r.get('outcome'))
        if o != 1:
            continue
        t = _f(r.get('T_agent_minutes'))
        c = _f(r.get('C_usd'))
        d = bands.setdefault(b, {'t': [], 'c': [], 'n': 0, 'free': 0})
        d['n'] += 1
        if t is not None:
            d['t'].append(t)
        if c is not None:
            d['c'].append(c)
        if (r.get('lane') or '').strip() == 'free':
            d['free'] += 1
    for b, d in bands.items():
        out['by_band'][b] = {
            'crossings': d['n'],
            'median_agent_minutes': (round(statistics.median(d['t']), 2)
                                     if d['t'] else None),
            'median_cost_usd': (round(statistics.median(d['c']), 2)
                                if d['c'] else None),
            'free_share': (round(d['free'] / d['n'], 4) if d['n'] else None),
        }

    # By model rollup: S and R by declared base model.
    models = {}
    for r in rows:
        m = r.get('model') or '(undeclared)'
        o = _f(r.get('outcome'))
        p = _f(r.get('p_frozen'))
        if o is None:
            continue
        d = models.setdefault(m, {'n': 0, 'sum_o': 0.0, 'R': 0.0})
        d['n'] += 1
        d['sum_o'] += o
        if p is not None:
            d['R'] += (o - p)
    for m, d in models.items():
        out['by_model'][m] = {
            'n': d['n'],
            'S': round(d['sum_o'] / d['n'], 4) if d['n'] else None,
            'R': round(d['R'], 4),
        }

    # Band boundary check: recompute band from p_frozen where present.
    for r in rows:
        p = _f(r.get('p_frozen'))
        if p is None:
            continue
        recomputed = band_of(p)
        stated = r.get('band')
        if recomputed != stated:
            out['band_check'].append({
                'deal_id': r.get('deal_id'), 'p_frozen': p,
                'stated': stated, 'recomputed': recomputed})

    return out


def main():
    if len(sys.argv) != 2:
        sys.stderr.write('usage: python3 verify.py deals.csv\n')
        return 2
    rows = load(sys.argv[1])
    print(json.dumps(verify(rows), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
