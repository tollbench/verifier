import unittest
from copy import deepcopy
from verify import verify


def row(**changes):
    base=dict(schema_version='toll-bench.public.v2',deal_id='example',agent='A',model='Model v1',model_attribution='frozen',is_scored='true',integrity_state='official',outcome=1,p_frozen=.7,band='short',resolution='delivered',week_resolved='2026-W36',T_agent_minutes=120,C_usd=50,toll_dollars_cents=5000,toll_days=3,final_toll=2,toll_formula_version='time-cost.v3')
    base.update(changes);return base


class VerifierTests(unittest.TestCase):
    def test_success_and_failure_count_neutral_and_invalidated_do_not(self):
        rows=[row(),row(deal_id='failure',outcome=0,resolution='failed'),row(deal_id='lapse',is_scored='false',integrity_state='provisional',outcome=0,resolution='lapsed'),row(deal_id='invalid',is_scored='false',integrity_state='invalidated')]
        out,errors=verify(rows)
        self.assertEqual(errors,[])
        self.assertEqual(out['by_agent']['A'],dict(n=2,S=.5,R=-.4))
        self.assertEqual(out['by_band']['short']['median_toll'],2)
    def test_score_is_recomputed_not_trusted(self):
        out,errors=verify([row(final_toll=999)])
        self.assertTrue(errors)
        self.assertEqual(out['by_band']['short']['median_toll'],2)
    def test_old_schema_missing_metadata_bad_band_and_bad_integrity_fail(self):
        for changed in [dict(schema_version='old'),dict(is_scored=None),dict(band='moonshot'),dict(integrity_state='invalidated'),dict(toll_formula_version='old'),dict(toll_days=None),dict(toll_days=-1),dict(week_resolved='')]:
            with self.subTest(changed=changed):
                self.assertTrue(verify([row(**changed)])[1])
    def test_scored_row_needs_a_finite_probability(self):
        for bad in ['', None, 'nan', 'NaN', 'inf', '-inf', 'not-a-number', float('nan'), float('inf')]:
            with self.subTest(p_frozen=bad):
                out,errors=verify([row(),row(deal_id='bad',p_frozen=bad)])
                self.assertTrue(any('bad: scored row has a missing or non-finite p_frozen' in e for e in errors))
                self.assertEqual(out['scored_row_count'],1)
    def test_unscored_rows_may_omit_probability(self):
        out,errors=verify([row(),row(deal_id='lapse',is_scored='false',integrity_state='provisional',outcome=0,resolution='lapsed',p_frozen='')])
        self.assertEqual(errors,[])
        self.assertEqual(out['scored_row_count'],1)
    def test_human_minutes_have_no_effect(self):
        self.assertEqual(verify([row(Your_minutes=0)]),verify([row(Your_minutes=100000)]))


if __name__=='__main__': unittest.main()
