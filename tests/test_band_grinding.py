"""SPEC20: four corrections of the grinding rules from the roll-grinding research.

Part 1: the feed-mark spacing ceiling (60 mm). Part 2: grinder chatter counts computed from
the grinder's settings (never rounded), the neutral case without grinder data (work roll only)
and the decisive case with it. Part 3: the de-trending order of a measured roll profile (the
report's cosine-crown check). Part 4: the station grid of a measured roll profile.
"""
import copy
import json
import math
import types
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from physicroll import band_signatures as bs
from physicroll import band_width as bw
from physicroll import roll_thermal as rt
from tests.test_band_lengthwise import V2_NULL_OBS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
SCEN = ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json'


def _facts(gaps_m, cv, spacing=None):
    obs = dict(V2_NULL_OBS, band_spacing_m=spacing)
    sp = {'gaps_m': gaps_m, 'coefficient_of_variation': cv,
          'mean_gap_m': sum(gaps_m) / len(gaps_m)}
    return types.SimpleNamespace(obs=obs, feed_pitch=None, grinding_supplied=False, gaps=None,
                                 spacing=sp)


class FeedMarkCeilingTests(unittest.TestCase):

    def _item(self, gap, cv=0.05):
        e, pred = bw._h_grinding(_facts([gap, gap, gap], cv))
        item = next(x for x in e if x['criterion'].startswith('regular fine spacing'))
        return item, pred

    def test_ceiling(self):
        self.assertEqual(bw.FEED_MARK_SPACING_CEILING_M, 0.060)
        for gap, verdict in ((0.045, 'SUPPORTS'), (0.053, 'SUPPORTS'), (0.070, 'NEUTRAL')):
            item, _ = self._item(gap)
            self.assertEqual(item['verdict'], verdict, gap)
            self.assertEqual(item['weight'], 'weak' if verdict == 'SUPPORTS' else None)
        item, _ = self._item(0.045, cv=0.3)              # irregular: unchanged neutral branch
        self.assertEqual(item['verdict'], 'NEUTRAL')

    def test_criterion_and_note(self):
        item, pred = self._item(0.045)
        crit = 'regular fine spacing (CV < 0.15, spacing < 60 mm)'
        self.assertEqual(item['criterion'], crit)
        self.assertIn(crit, bpl.CRITERIA)
        self.assertIn('[RG5]', pred['feed_range_note'])
        self.assertIn('[RG7, computed from the printed settings]', pred['feed_range_note'])
        self.assertIn('roll_surface_band', pred['feed_range_note'])


D_W = 0.28
CIRC = math.pi * D_W                 # forward slip 0 in these checks


def _ctx(pitches_m, marks=()):
    return types.SimpleNamespace(
        case={'kinematics': {'grinder_marks': list(marks)}}, kin_slip=0.0,
        pitches=[{'pitch_m': p, 'exit_speed_m_s': 10.0} for p in pitches_m])


class GrinderChatterTests(unittest.TestCase):

    def test_no_grinder_data_work_roll_is_neutral_inside_the_range(self):
        ctx = _ctx([0.006])                       # implied 146.6 marks per circumference
        e = bd._roll_mark(ctx, D_W, 'work_roll', 'w')
        self.assertEqual(e['verdict'], 'NEUTRAL')
        self.assertIn('cannot be excluded', e['observed'])
        self.assertIn('[RG25 AB, RG26 AB, RG24 VP', e['observed'])
        self.assertIn('wheel and roll speeds', e['observed'])
        self.assertTrue(ctx.grinder_chatter_not_excluded)
        chk = bd.grinder_pitch_check(ctx, D_W, 'work_roll')
        self.assertFalse(chk['grinder_data_entered'])
        self.assertAlmostEqual(chk['pitches'][0]['implied_marks_per_circumference'],
                               CIRC / 0.006, delta=1e-9)
        self.assertTrue(chk['pitches'][0]['in_typical_grinder_chatter_range'])
        self.assertIn('turns this into a test', chk['note'])

    def test_backup_roll_and_outside_the_range_keep_todays_rule(self):
        ctx = _ctx([0.006])
        self.assertEqual(bd._roll_mark(ctx, D_W, 'backup_roll', 'b')['verdict'], 'CONTRADICTS')
        self.assertFalse(getattr(ctx, 'grinder_chatter_not_excluded', False))
        for pitch in (CIRC / 10.0, CIRC / 300.0):        # 8 < n < 12 and n > 240
            ctx = _ctx([pitch])
            self.assertEqual(bd._roll_mark(ctx, D_W, 'work_roll', 'w')['verdict'],
                             'CONTRADICTS', pitch)
        ctx = _ctx([CIRC / 3])                              # a simple count still supports
        self.assertEqual(bd._roll_mark(ctx, D_W, 'work_roll', 'w')['verdict'], 'SUPPORTS')

    def test_computed_count_decides(self):
        n = 146.6
        wheel_hz, roll_hz = 1000.0 / 60, 1000.0 / 60 / n
        g = {'roll': 'work_roll', 'wheel_rotation_hz': wheel_hz, 'roll_rotation_hz': roll_hz}
        ctx = _ctx([CIRC / n], [g])
        e = bd._roll_mark(ctx, D_W, 'work_roll', 'w')
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertIn('computed from wheel and roll speed', e['observed'])
        cnt, _, how, marks = bd._mark_count(ctx, D_W, 'work_roll')
        self.assertAlmostEqual(cnt, n, delta=1e-9)          # not rounded
        self.assertNotEqual(cnt, round(cnt))
        # entered data that does not fit: decisive CONTRADICTS, never the neutral case
        bad = dict(g, roll_rotation_hz=wheel_hz / 100.0)
        ctx = _ctx([CIRC / n], [bad])
        e = bd._roll_mark(ctx, D_W, 'work_roll', 'w')
        self.assertEqual(e['verdict'], 'CONTRADICTS')
        self.assertFalse(getattr(ctx, 'grinder_chatter_not_excluded', False))
        chk = bd.grinder_pitch_check(ctx, D_W, 'work_roll')
        self.assertTrue(chk['grinder_data_entered'])
        self.assertEqual(chk['grinder_counts'][0]['obtained'],
                         'computed from wheel and roll speed')
        # vibration frequency in place of the wheel rotation
        vib = {'roll': 'backup_roll', 'vibration_frequency_hz': 120.0, 'roll_rotation_hz': 0.8}
        self.assertEqual(bs.grinder_mark_count(vib)[:2],
                         (150.0, 'computed from vibration frequency and roll speed'))

    def test_validation(self):
        for g, msg in (
                ({'roll': 'work_roll', 'marks_per_circumference': 3, 'roll_rotation_hz': 0.1,
                  'wheel_rotation_hz': 15.0}, 'give exactly one of'),
                ({'roll': 'work_roll'}, 'give exactly one of'),
                ({'roll': 'work_roll', 'roll_rotation_hz': 0.1}, 'need roll_rotation_hz and'),
                ({'roll': 'work_roll', 'wheel_rotation_hz': 15.0}, 'need roll_rotation_hz and'),
                ({'roll': 'work_roll', 'wheel_rotation_hz': -1.0, 'roll_rotation_hz': 0.1},
                 'wheel_rotation_hz'),
                ({'roll': 'side_roll', 'marks_per_circumference': 3}, "'work_roll' or")):
            with self.assertRaises(ValueError) as cm:
                bs.validate_grinder_mark(g, 1)
            self.assertIn('grinder_marks[1]', str(cm.exception))
            self.assertIn(msg, str(cm.exception))
        bs.validate_grinder_mark({'roll': 'work_roll', 'wheel_rotation_hz': 15.0,
                                  'roll_rotation_hz': 0.1}, 0)

    def test_catalogue_uses_the_computed_count(self):
        mill = bs.MillKinematics(work_roll_diameter_m=0.28, backup_roll_diameter_m=1.2,
                                 grinder_marks=({'roll': 'work_roll', 'wheel_rotation_hz': 15.0,
                                                 'roll_rotation_hz': 0.1},))
        mill.validate()
        cat = bs.source_catalogue(mill, 10.0, 0.0)
        e = next(x for x in cat if x['id'] == 'grinder_marks:work_roll:0')
        self.assertAlmostEqual(e['order_of_work_roll_rotation'], 150.0, delta=1e-9)
        self.assertIn('computed from wheel and roll speed', e['description'])

    def test_app_question_round_trip(self):
        q = bpl.QUESTION_BY_ID['grinder_marks']
        self.assertEqual(bpl.ADDON_BY_QUESTION['grinder_marks'], 'grinder_report')
        rows = bpl.answer_to_si(q, [{'roll': 'work_roll', 'marks_per_circumference': None,
                                     'wheel_rotation_hz': 900.0, 'roll_rotation_hz': 6.0}])
        self.assertEqual(rows, [{'roll': 'work_roll', 'wheel_rotation_hz': 15.0,
                                 'roll_rotation_hz': 0.1}])
        back = bpl.answer_from_si(q, rows)
        self.assertEqual((back[0]['wheel_rotation_hz'], back[0]['roll_rotation_hz'],
                          back[0]['marks_per_circumference']), (900.0, 6.0, None))
        self.assertIn('cannot rule a grinder pattern in or out', q.help)


def _cosine(x, length, crown_radius, half_angle_rad):
    """The research script's curve (prototypes/grinding-research/detrend_check.py): radius drop
    Cr*(1 - cos(a*u))/(1 - cos(a)), u = 2x/L - 1 over the barrel, a = half angle."""
    u = 2 * x / length - 1
    return -crown_radius * (1 - math.cos(half_angle_rad * u)) / (1 - math.cos(half_angle_rad))


class DetrendTests(unittest.TestCase):

    def test_cosine_crown_residual(self):
        """40 um crown on radius, 70 degree half angle, 1.7 m barrel, strip 0.79 of it."""
        length = 1.7
        z = [(i + 0.5) * 0.005 for i in range(340)]
        vals = [_cosine(x, length, 40e-6, math.radians(70)) for x in z]
        res = {}
        for order in (2, 4):
            loc = rt.local_stripes(z, vals, length / 2, 0.79 * length, threshold_m=1e-7,
                                   smooth_order=order)
            d = loc['local_radius_deviation_m']
            res[order] = max(d) - min(d)
        self.assertLess(abs(res[2] / 0.68e-6 - 1), 0.10)
        self.assertLess(res[4], 0.02e-6)
        self.assertEqual(bw.ROLL_PROFILE_DETREND_ORDER_DEFAULT, 4)

    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ART / 'battery-foil-demo.result.json').read_text(encoding='utf-8'))
        cls.raw = json.loads(SCEN.read_text(encoding='utf-8'))
        iu = cls.r['width']['inputs_used']
        cls.supplied = {k: iu[k] for k in ('strip_stiffness_per_width_pa', 'bite_half_length_m',
                                           'exit_tension_force_sensitivity_per_width_m')}
        cls.ts = cls.r['width']['thermal_steady']
        cls.th = types.SimpleNamespace(centre=0.75, width=1.2)
        cls.bite = types.SimpleNamespace(separating_force_n=958605 * 1.2)

    def _section(self, prof, band_width=None):
        raw = copy.deepcopy(self.raw)
        raw['width_model']['roll_ground_profile'] = prof
        raw['observation']['band_width_m'] = band_width
        case = bd.validate_case(raw)
        w = case['width_model']
        sp = bw.shape_params(case, None, w, None, supplied=self.supplied)
        return bw.roll_profile_section(case, w, sp, None, self.ts['z_m'], self.th, self.ts,
                                       self.bite)

    def test_cosine_crown_gives_no_band_with_the_default_order(self):
        pos = [round(0.01 * i, 10) for i in range(151)]
        dev = [_cosine(x, 1.5, 40e-6, math.radians(70)) for x in pos]
        s = self._section({'positions_m': pos, 'radius_deviation_m': dev,
                           'provenance': 'cosine crown (SPEC20 check)'})
        self.assertEqual(s['detrend_order'], 4)
        self.assertEqual(s['levels']['with_feedback']['bands'], [])
        ds = s['detrend_sensitivity']
        self.assertEqual(ds['bands_order_4'], [])
        self.assertEqual(ds['bands_depend_on_order'], bool(ds['bands_order_2']))
        if ds['bands_depend_on_order']:
            self.assertIn(bw.RP_FLAG_ORDER, s['flags'])
            self.assertIn("subtract the grinder's target curve", ds['sentence'])
        self.assertNotIn(bw.RP_FLAG_GRID, s['flags'])           # 10 mm stations
        self.assertAlmostEqual(s['grid']['smallest_resolvable_width_m'], 0.02, delta=1e-9)
        lim = ' '.join(s['limitations'])
        self.assertIn('3.3 um per K', lim)
        self.assertIn('halved for the radius input', lim)

    def test_grid(self):
        pos = [round(0.05 + 0.07 * i, 10) for i in range(21)]     # a 21-station report
        dev = [0.0] * 21
        s = self._section({'positions_m': pos, 'radius_deviation_m': dev, 'provenance': 'x'})
        g = s['grid']
        self.assertAlmostEqual(g['largest_spacing_inside_strip_m'], 0.07, delta=1e-9)
        self.assertAlmostEqual(g['smallest_resolvable_width_m'], 0.14, delta=1e-9)
        self.assertIn(bw.RP_FLAG_GRID, s['flags'])
        self.assertIn('cannot show a mark narrower than 140 mm', g['sentence'])
        s = self._section({'positions_m': pos, 'radius_deviation_m': dev, 'provenance': 'x'},
                          band_width=0.2)                            # observed wide band
        self.assertNotIn(bw.RP_FLAG_GRID, s['flags'])
        self.assertEqual(s['grid']['reference_width_basis'], 'observation.band_width_m')

    def test_flags_have_plain_sentences(self):
        for f in (bd.GRINDER_CHATTER_FLAG, bw.RP_FLAG_ORDER, bw.RP_FLAG_GRID):
            self.assertIn(f, bpl.FLAGS)


if __name__ == '__main__':
    unittest.main()
