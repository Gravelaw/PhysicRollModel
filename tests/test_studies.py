from dataclasses import replace
import unittest
from physicroll.studies import Constraints, rank_candidates
from test_model import BASE


class StudyTests(unittest.TestCase):
    def test_constraint_ranking(self):
        c=Constraints(.0015,3e6,300e3,8)
        result=rank_candidates([replace(BASE,name=f'speed_{v}',entry_speed_m_s=v) for v in [1,2,3]],c)
        self.assertEqual(result['selected_scenario'],'speed_2')
        self.assertEqual([r['feasible'] for r in result['candidates']],[False,True,False])

    def test_no_feasible_and_invalid_constraints(self):
        r=rank_candidates([BASE],Constraints(.001,3e6,300e3,8))
        self.assertIsNone(r['selected_scenario'])
        with self.assertRaises(ValueError):
            rank_candidates([BASE],Constraints(.0015,float('nan'),300e3,8))
