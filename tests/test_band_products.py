import json
import math
import re
import unittest
from pathlib import Path

from physicroll import band_products as bp
from physicroll.band_products import (
    BATTERY_SCHEDULE_CAVEAT, READ_STATUSES, TENSION_LINES, PassSchedule, Range, Statement,
    catalogue_dict, check_pass, nearest_published_schedules, product, product_ids, products,
    render_reference_markdown, sources)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs' / 'thin-gauge-products.md'
UM, MM = 1e-6, 1e-3


def schedule(product_id, label):
    for s in product(product_id).schedules:
        if s.label == label:
            return s
    raise AssertionError(f'no schedule {label!r} in {product_id}')


def walk_numbers(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from walk_numbers(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk_numbers(v)
    elif isinstance(value, float):
        yield value


def by_item(findings):
    return {f['item']: f for f in findings}


class IntegrityTests(unittest.TestCase):
    def test_ids_unique_and_expected(self):
        ids = product_ids()
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[0], 'battery_collector_foil')
        self.assertEqual(set(ids), {
            'battery_collector_foil', 'battery_pouch_laminate_foil',
            'capacitor_anode_foil_high_voltage', 'capacitor_anode_foil_low_voltage',
            'capacitor_cathode_foil', 'pharma_blister_lidding', 'pharma_cold_form_foil',
            'pharma_strip_pack_foil', 'household_foil', 'household_foil_heavy_duty',
            'converter_foil', 'cigarette_liner_foil', 'dairy_lidding_foil',
            'container_foil_wrinkle_wall', 'container_foil_smooth_wall',
            'container_foil_retortable', 'brazed_fin_stock', 'brazing_sheet_tube',
            'hvac_fin_stock', 'litho_sheet', 'can_body_stock', 'can_end_stock', 'closure_sheet',
            'transformer_strip'})
        self.assertEqual(len(set(sources())), len(sources()))

    def test_sources_have_urls_and_valid_status(self):
        for sid, s in sources().items():
            self.assertEqual(sid, s.id)
            self.assertRegex(sid, r'^(BF|PK|HX)-S\d+b?$')
            self.assertTrue(s.urls)
            for u in s.urls:
                self.assertRegex(u, r'^https?://\S+$')
            self.assertIn(s.read_status, READ_STATUSES)
            self.assertNotEqual(s.read_status, 'computed')
        self.assertEqual(sources()['BF-S17'].read_status, 'vendor_or_trade_page')

    def test_every_fact_sourced_and_status_never_upgraded(self):
        src = sources()
        rank = {'full_text': 0, 'excerpt': 1, 'abstract_or_snippet': 2,
                'vendor_or_trade_page': 3, 'memory_unverified': 4}
        facts = bp._all_facts()
        self.assertGreater(len(facts), 300)
        for f in facts:
            for s in f.sources:
                self.assertIn(s, src)
            if not f.sources:
                self.assertIsInstance(f, Statement)
                self.assertTrue(f.topic == 'not_found' or f.read_status == 'memory_unverified')
            own = getattr(f, 'read_status', None)
            if own not in (None, 'computed') and f.sources:
                weakest = max(rank[src[s].read_status] for s in f.sources)
                self.assertGreaterEqual(rank[own], weakest)

    def test_ranges_ordered_with_units(self):
        for f in bp._all_facts():
            if isinstance(f, Range):
                self.assertIn(f.unit, bp.UNITS)
                self.assertFalse(f.low is None and f.high is None)
                if f.low is not None and f.high is not None:
                    self.assertLessEqual(f.low, f.high)

    def test_products_validate_and_have_core_fields(self):
        for p in products():
            self.assertIs(p.validate(), p)
            self.assertIn(p.family, bp.FAMILIES)
            self.assertTrue(p.alloys and p.tempers)
            self.assertEqual(p.final_gauge_m.unit, 'm')

    def test_catalogue_json_round_trip(self):
        d = catalogue_dict()
        text = json.dumps(d, allow_nan=False, ensure_ascii=False)
        self.assertEqual(json.loads(text), d)
        self.assertEqual(d['schema'], 'physicroll.band_products.v1')
        self.assertEqual(d['status'], 'LITERATURE_SURVEY_UNVALIDATED')
        self.assertTrue(d['limitations'])
        self.assertEqual(d['counts']['products'], 24)
        self.assertEqual(d['counts']['sources'], len(sources()))
        for v in walk_numbers(d):
            self.assertTrue(math.isfinite(v))

    def test_battery_depth(self):
        p = product('battery_collector_foil')
        self.assertIn(BATTERY_SCHEDULE_CAVEAT, p.caveats)
        self.assertEqual(BATTERY_SCHEDULE_CAVEAT.sources, ('BF-S17',))
        self.assertEqual({s.topic for s in p.work_roll_roughness},
                         {'roughing', 'intermediate', 'finishing'})
        grades = {s.grade for s in p.strength}
        self.assertTrue({'standard', 'high_strength'} <= grades)
        self.assertEqual(len(p.pinholes), 4)
        self.assertTrue(p.wettability and p.flatness_requirement and p.thickness_tolerance)
        pitch, gauge = TENSION_LINES.values
        self.assertAlmostEqual(pitch.low, 5e-3)
        self.assertAlmostEqual(pitch.high, 20e-3)
        self.assertAlmostEqual(gauge.high, 15e-6)
        self.assertIn('Tension lines', [d.name for d in p.named_defects])
        self.assertEqual(p.rolled_mode, 'either')
        self.assertAlmostEqual(p.single_sheet_gauge_m.low, 9e-6)
        self.assertEqual(len([s for s in p.schedules if s.doubled_from_index is None]), 10)


class ReductionTests(unittest.TestCase):
    def assert_printed(self, sched, printed_pct, places=0):
        red = sched.reductions()
        self.assertEqual(len(red), len(printed_pct))
        tol = 0.5 * 10 ** -places + 1e-9
        for (lo, hi), p in zip(red, printed_pct):
            if isinstance(p, tuple):
                self.assertLessEqual(abs(lo * 100 - p[0]), tol, (sched.label, lo, p))
                self.assertLessEqual(abs(hi * 100 - p[1]), tol, (sched.label, hi, p))
            else:
                self.assertLessEqual(abs(lo * 100 - p), tol, (sched.label, lo, p))
                self.assertAlmostEqual(lo, hi)

    def test_battery_schedules(self):
        b = 'battery_collector_foil'
        self.assert_printed(schedule(b, 'BF-S12 1100, 4 passes from 300 µm'), [53, 53, 52, 53])
        self.assert_printed(schedule(b, 'BF-S12 1100, 4 passes from 270 µm'), [53, 55, 55, 50])
        self.assert_printed(schedule(b, 'BF-S12 1100, 4 passes from 260 µm'), [56, 52, 55, 52])
        self.assert_printed(schedule(b, 'BF-S11 5 passes from 240 µm'), [48, 49, 47, 41, 35])
        self.assert_printed(schedule(b, 'BF-S13 5 passes from 260 µm'), [50, 50, 51, 47, 29])
        self.assert_printed(schedule(b, 'BF-S14 5 passes from 250 µm'),
                            [60, 41, 49, 50, (33, 40)])
        self.assert_printed(schedule(b, 'BF-S15 1070, 5 passes from 360 µm'),
                            [44, 50, 50, 50, 40])
        self.assert_printed(schedule(b, 'BF-S15 1070, 4 passes from 360 µm'), [54, 61, 51, 38])
        self.assert_printed(schedule(b, 'BF-S16 3 passes from 220 µm'), [64, 63, 57])
        self.assert_printed(schedule(b, 'BF-S8 Speira, last 3 of 9 passes from 4.5 mm'),
                            [46, 60, 35])
        p = product(b)
        self.assertAlmostEqual(round(p.per_pass_reduction.low * 100), 29)
        self.assertAlmostEqual(round(p.per_pass_reduction.high * 100), 64)
        fp = p.final_pass
        self.assertAlmostEqual(fp.entry_gauge_m.low, 15 * UM)
        self.assertAlmostEqual(fp.entry_gauge_m.high, 32 * UM)
        self.assertEqual(round(fp.reduction.low * 100), 29)
        self.assertEqual(round(fp.reduction.high * 100), 57)
        dbl = schedule(b, 'BF-S17 plant 1, doubled last pass')
        self.assertTrue(dbl.is_doubled(3) and not dbl.is_doubled(2))
        self.assertAlmostEqual(dbl.reductions()[3][0], 0.5)

    def test_pouch_and_packaging(self):
        self.assert_printed(schedule('battery_pouch_laminate_foil', 'BF-S34 8021 foil passes'),
                            [48, 49, 53])
        hh = schedule('household_foil', 'PK-S2 household 450 µm → 2×10.5 µm')
        self.assert_printed(hh, [52, 53, 53, 51, 54])
        self.assertTrue(hh.is_doubled(4))
        c = 'converter_foil'
        self.assert_printed(schedule(c, 'PK-S2 converter 450 µm → 2×6.5 µm'),
                            [51, 50, 50, 53, 46, 54])
        trc = schedule(c, 'PK-S3 TRC 8079 8 mm → 2×6.35 µm')
        red = trc.reductions()
        for i, p in ((0, 50), (2, 53), (3, 60), (4, 44), (6, 55)):
            self.assertLessEqual(abs(red[i][0] * 100 - p), 0.5)
        means = {i: lo for i, lo, _, kind in trc.per_pass_reductions()
                 if kind == 'equal_split_mean'}
        self.assertLessEqual(abs(means[1] * 100 - 40), 0.5)  # "about 40 % each"
        self.assertLessEqual(abs(means[5] * 100 - 50), 0.5)  # "about 50 % each"
        self.assert_printed(schedule(c, 'PK-S16 Alcoa Yennora 1145, 29 µm → 2×6.5 µm'), [52, 54])
        span = bp._general_foil_span()
        self.assertAlmostEqual(span.low, 0.44)
        self.assertAlmostEqual(span.high, 0.60)

    def test_litho_published_reductions(self):
        for label, gauges in (('HX-S25 Hydro 2.8 mm, 3 passes', (2.8, 1.204, 0.566, 0.277)),
                              ('HX-S25 Hydro 2.3 mm, 3 passes', (2.3, 0.989, 0.494, 0.272)),
                              ('HX-S25 Hydro 3.0 mm, 3 passes', (3.0, 1.20, 0.564, 0.276))):
            s = schedule('litho_sheet', label)
            for (lo, hi), g in zip(s.gauges(), gauges):
                self.assertAlmostEqual(lo, hi)
                self.assertLessEqual(abs(lo / MM - g), 0.0006, (label, lo, g))
        lt = 'litho_sheet'
        self.assert_printed(schedule(lt, 'HX-S26 interanneal at 0.9–1.2 mm → 0.28 mm'),
                            [(69, 77)])
        self.assert_printed(schedule(lt, 'HX-S26 interanneal at 2.0–2.4 mm → 0.29 mm'),
                            [(85.5, 88)])  # report mixes 85.5 and 88
        self.assert_printed(schedule(lt, 'HX-S27 interanneal at 2.2 mm → 0.30 mm'), [86.4],
                            places=1)
        self.assert_printed(schedule(lt, 'HX-S28 TRC 4.5 → 1.5 → 0.28 mm'), [66.7, 81.3],
                            places=1)
        p = product(lt)
        self.assertAlmostEqual(p.per_pass_reduction.low, 0.45)
        self.assertAlmostEqual(p.per_pass_reduction.high, 0.60)

    def test_heat_exchanger(self):
        s = schedule('hvac_fin_stock', 'HX-S21 TRC 6.2 mm → 0.080–0.085 mm')
        for (lo, _), g in zip(s.gauges(), (6.2, 2.85, 1.45, 0.82, 0.42, 0.23, 0.13)):
            self.assertAlmostEqual(lo / MM, g)
        self.assertAlmostEqual(s.gauges()[-1][0], 0.080 * MM)
        self.assert_printed(s, [54.0, 49.1, 43.4, 48.8, 45.2, 43.5, (34.6, 38.5)], places=1)
        self.assertLessEqual(abs((1 - 0.080 / 6.2) * 100 - 98.7), 0.05)
        nov = schedule('hvac_fin_stock', 'HX-S22 Novelis belt-cast 1.7 → 0.10 mm in 3 passes')
        self.assertLessEqual(abs(nov.reductions()[0][0] * 100 - 94.1), 0.05)
        self.assertLessEqual(abs(nov.per_pass_reductions()[0][1] * 100 - 61), 0.5)
        s8014 = schedule('hvac_fin_stock', 'HX-S23 8014-H22 6.4–7.4 → 0.17–0.24 mm in 8 passes')
        _, lo, hi, kind = s8014.per_pass_reductions()[0]
        self.assertEqual(kind, 'equal_split_mean')
        self.assertEqual((round(lo * 100), round(hi * 100)), (34, 38))
        fin = 'brazed_fin_stock'
        self.assert_printed(schedule(fin, 'HX-S3 DC route 3.5–4 mm → 0.080 mm'),
                            [(71, 75), 87.7, 35.0], places=0)
        self.assert_printed(schedule(fin, 'HX-S4 TRC worked example 0.109 → 0.060 mm'), [45.0],
                            places=1)
        self.assertIsNone(product(fin).per_pass_reduction)

    def test_schedule_validation(self):
        with self.assertRaises(ValueError):
            PassSchedule('bad', (100e-6, 120e-6), ('BF-S12',)).validate()
        with self.assertRaises(ValueError):
            PassSchedule('bad', (100e-6, 50e-6), ('XX-S1',)).validate()
        with self.assertRaises(ValueError):
            PassSchedule('bad', (100e-6, 50e-6), ('BF-S12',), doubled_from_index=3).validate()
        with self.assertRaises(ValueError):
            Range(1.0, 0.5, 'm', ('BF-S1',)).validate()
        with self.assertRaises(ValueError):  # upgrading a vendor page to full text
            Range(1.0, 2.0, 'm', ('BF-S3',), read_status='full_text').validate()


class CheckPassTests(unittest.TestCase):
    def test_battery_50_to_30(self):
        f = by_item(check_pass('battery_collector_foil', 50e-6, 30e-6))
        self.assertEqual(f['per_pass_reduction']['verdict'], 'WITHIN_PUBLISHED_RANGE')
        self.assertAlmostEqual(f['per_pass_reduction']['value'], 0.4)
        self.assertNotIn('final_gauge', f)
        self.assertEqual(f['per_pass_reduction']['read_status'], 'vendor_or_trade_page')

    def test_final_pass_30_to_18(self):
        f = by_item(check_pass('battery_collector_foil', 30e-6, 18e-6, is_final_pass=True,
                               exit_speed_m_s=450 / 60, doubled=False))
        for item in ('final_gauge', 'final_pass_reduction', 'final_pass_entry_gauge',
                     'per_pass_reduction', 'exit_speed', 'rolled_mode',
                     'single_sheet_final_gauge'):
            self.assertEqual(f[item]['verdict'], 'WITHIN_PUBLISHED_RANGE', item)
        self.assertAlmostEqual(f['final_gauge']['published_low'], 8e-6)
        self.assertAlmostEqual(f['final_gauge']['published_high'], 20e-6)
        self.assertEqual(f['final_gauge']['read_status'], 'full_text')

    def test_seventy_percent_pass_above(self):
        f = by_item(check_pass('battery_collector_foil', 100e-6, 30e-6))
        self.assertEqual(f['per_pass_reduction']['verdict'], 'ABOVE_PUBLISHED_RANGE')
        f = by_item(check_pass('battery_collector_foil', 30e-6, 9e-6, is_final_pass=True))
        self.assertEqual(f['final_pass_reduction']['verdict'], 'ABOVE_PUBLISHED_RANGE')

    def test_mode_checks(self):
        f = by_item(check_pass('battery_collector_foil', 30e-6, 15e-6, doubled=True,
                               is_final_pass=True, surface='two_side_bright'))
        self.assertEqual(f['rolled_mode']['verdict'], 'INCONSISTENT_WITH_PUBLISHED_MODE')
        self.assertIn('PK-S6', f['rolled_mode']['sources'])
        f = by_item(check_pass('battery_collector_foil', 30e-6, 15e-6, doubled=True,
                               is_final_pass=True, surface='one_side_bright',
                               exit_speed_m_s=500 / 60))
        self.assertEqual(f['rolled_mode']['verdict'], 'WITHIN_PUBLISHED_RANGE')
        self.assertAlmostEqual(f['exit_speed']['published_high'], 650 / 60)
        f = by_item(check_pass('household_foil', 23e-6, 10.5e-6, doubled=False,
                               is_final_pass=True))
        self.assertEqual(f['rolled_mode']['verdict'], 'INCONSISTENT_WITH_PUBLISHED_MODE')
        f = by_item(check_pass('container_foil_wrinkle_wall', 80e-6, 50e-6, doubled=True))
        self.assertEqual(f['rolled_mode']['verdict'], 'INCONSISTENT_WITH_PUBLISHED_MODE')
        f = by_item(check_pass('can_body_stock', 0.5e-3, 0.3e-3, doubled=False))
        self.assertEqual(f['rolled_mode']['verdict'], 'NO_PUBLISHED_RANGE')

    def test_flow_stress_alloy_and_fallbacks(self):
        f = by_item(check_pass('battery_collector_foil', 50e-6, 30e-6, alloy='1085',
                               mean_flow_stress_pa=180e6))
        self.assertEqual(f['alloy']['verdict'], 'WITHIN_PUBLISHED_RANGE')
        ind = f['mean_flow_stress_indicator']
        self.assertEqual(ind['verdict'], 'WITHIN_PUBLISHED_RANGE')
        self.assertIn('INDICATOR ONLY', ind['basis'])
        f = by_item(check_pass('battery_collector_foil', 50e-6, 30e-6, alloy='9999',
                               mean_flow_stress_pa=180e6))
        self.assertEqual(f['alloy']['verdict'], 'NO_PUBLISHED_RANGE')
        self.assertEqual(f['mean_flow_stress_indicator']['verdict'], 'NO_PUBLISHED_RANGE')
        f = by_item(check_pass('pharma_blister_lidding', 40e-6, 20e-6))
        self.assertIn('general packaging foil', f['per_pass_reduction']['basis'])
        f = by_item(check_pass('brazed_fin_stock', 0.12e-3, 0.08e-3))
        self.assertEqual(f['per_pass_reduction']['verdict'], 'NO_PUBLISHED_RANGE')

    def test_errors_and_json(self):
        with self.assertRaises(ValueError) as cm:
            check_pass('no_such_product', 50e-6, 30e-6)
        for pid in product_ids():
            self.assertIn(pid, str(cm.exception))
        with self.assertRaises(ValueError):
            product('nope')
        for bad in ((30e-6, 50e-6), (float('nan'), 1e-6), (True, 1e-6), (-1.0, 1e-6)):
            with self.assertRaises(ValueError):
                check_pass('battery_collector_foil', *bad)
        with self.assertRaises(ValueError):
            check_pass('battery_collector_foil', 50e-6, 30e-6, doubled=1)
        with self.assertRaises(ValueError):
            check_pass('battery_collector_foil', 50e-6, 30e-6, surface='matt')
        for pid in product_ids():
            out = check_pass(pid, 2e-3 if 'litho' in pid else 60e-6,
                             1e-3 if 'litho' in pid else 40e-6, exit_speed_m_s=10.0,
                             mean_flow_stress_pa=150e6, doubled=True, is_final_pass=True,
                             alloy='8011', temper='O')
            json.dumps(out, allow_nan=False)
            for f in out:
                self.assertIn(f['verdict'], bp.VERDICTS)

    def test_nearest_published(self):
        near = nearest_published_schedules('battery_collector_foil', 50e-6, 30e-6, n=10)
        self.assertEqual(len(near), 10)
        pairs = {(round(c['entry_m'][0] / UM), round(c['exit_m'][0] / UM)) for c in near}
        self.assertTrue({(64, 34), (66, 32), (50, 25)} <= pairs)
        d = [c['log_gauge_distance'] for c in near]
        self.assertEqual(d, sorted(d))
        self.assertEqual(near[0]['read_status'], 'computed')
        json.dumps(near, allow_nan=False)
        with self.assertRaises(ValueError):
            nearest_published_schedules('battery_collector_foil', 50e-6, 30e-6, n=0)


class DocumentTests(unittest.TestCase):
    def test_document_matches_and_is_complete(self):
        text = render_reference_markdown()
        self.assertEqual(text, render_reference_markdown())
        self.assertEqual(DOC.read_text(encoding='utf-8'), text,
                         'regenerate: python -m physicroll.band_products --write '
                         'docs/thin-gauge-products.md')
        for p in products():
            self.assertIn(p.name, text)
        for s in sources().values():
            for u in s.urls:
                self.assertIn(u, text)
        self.assertNotRegex(text, r'\b(nan|inf)\b')
        self.assertIn('## 1. Li-ion cathode current-collector foil (`battery_collector_foil`)',
                      text)
        self.assertIn('302→152', text)

    def test_cli(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(bp.main(['--list']), 0)
        self.assertEqual(len(buf.getvalue().strip().splitlines()), 24)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bp.main(['--json'])
        self.assertEqual(json.loads(buf.getvalue())['schema'], 'physicroll.band_products.v1')
        self.assertTrue(re.search(r'\d+ sourced facts', render_reference_markdown()))


if __name__ == '__main__':
    unittest.main()
