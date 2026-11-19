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
            'battery_thick_collector_foil', 'battery_carbon_coated_base_foil', 'battery_tab_foil',
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
            self.assertRegex(sid, r'^((BF|PK|HX)-S\d+b?|BG-G\d+|PT-T\d+)$')
            self.assertTrue(s.urls)
            for u in s.urls:
                self.assertRegex(u, r'^https?://\S+$')
            self.assertIn(s.read_status, READ_STATUSES)
            self.assertNotEqual(s.read_status, 'computed')
        self.assertEqual(sources()['BF-S17'].read_status, 'vendor_or_trade_page')
        bg = sorted(int(k[4:]) for k in sources() if k.startswith('BG-'))
        self.assertEqual(bg, list(range(1, 45)))
        tag = {'FT': 'full_text', 'EX': 'excerpt', 'SN': 'abstract_or_snippet',
               'VP': 'vendor_or_trade_page'}
        for n, t in ((1, 'EX'), (2, 'VP'), (3, 'FT'), (14, 'FT'), (21, 'EX'), (37, 'SN'),
                     (42, 'VP')):
            self.assertEqual(sources()[f'BG-G{n}'].read_status, tag[t])
        for n in (30, 39, 40):  # two tags: recorded at the weaker one
            self.assertEqual(sources()[f'BG-G{n}'].read_status, 'vendor_or_trade_page')

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
        self.assertEqual(d['counts']['products'], 27)
        self.assertEqual(d['battery_grades']['status'],
                         'LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT')
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
        # the 8011 correction: 180 MPa, marked, both sources; the 1C30/1100 group keeps 220-230
        hs = [s for s in p.strength if s.condition == 'GB/T 33143 high-strength minima']
        self.assertEqual(len(hs), 1)
        self.assertNotIn('8011', hs[0].alloys)
        c = [s for s in p.strength if s.alloys == ('8011',) and 'corrected' in s.condition]
        self.assertEqual(len(c), 1)
        self.assertAlmostEqual(c[0].rm_pa.low, 180e6)
        self.assertEqual(set(c[0].sources), {'BG-G2', 'BF-S2'})
        self.assertTrue(c[0].note.startswith('CORRECTED'))
        self.assertEqual(set(bp.CORRECTIONS[0].sources), {'BG-G2', 'BF-S2'})
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
        dbl = schedule(b, 'BF-S17 trade-page plant 1 schedule, doubled last pass')
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
        i = text.index('## Battery foil: alloy and temper by gauge')
        self.assertLess(i, text.index('## 1. Li-ion cathode current-collector foil'))
        sec = text[i:text.index('## 1. Li-ion')]
        for want in ('### Three findings first', '### Collector foil: selection table by gauge '
                     'band', 'The two bands that matter for a 17–19 µm and a 12 µm product',
                     '**>15–20 µm** band', '**>10–13 µm** band', '### The 25–60 µm battery '
                     'products', '### Why alloy and temper change with gauge',
                     '### How each temper is produced', '### Strength after heating',
                     '### Disagreements (second survey)', '### Not found (second survey)',
                     '252 MPa', '50→30→18 µm', '50→24.5→12 µm'):
            self.assertIn(want, sec)

    def test_cli(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(bp.main(['--list']), 0)
        self.assertEqual(len(buf.getvalue().strip().splitlines()), 27)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(bp.main(['--grades', 'battery_collector_foil', '--gauge-um', '18']),
                             0)
        text = buf.getvalue()
        self.assertIn('band >15–20 µm', text)
        self.assertIn('Proposal (standard): 1235-H18', text)
        self.assertIn('Proposal (high-strength): 1100-H18', text)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bp.main(['--grades', 'battery_collector_foil', '--gauge-um', '12', '--json'])
        d = json.loads(buf.getvalue())
        self.assertEqual(d['options']['band_id'], '10_13')
        self.assertEqual(d['proposals']['high_strength']['alloy'], '1100')
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            bp.main(['--grades', 'battery_collector_foil'])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bp.main(['--json'])
        self.assertEqual(json.loads(buf.getvalue())['schema'], 'physicroll.band_products.v1')
        self.assertTrue(re.search(r'\d+ sourced facts', render_reference_markdown()))


def _opt(pid, gauge_um, alloy, **kw):
    for o in bp.grade_options(pid, gauge_um * UM, **kw)['options']:
        if o['alloy'] == alloy:
            return o
    raise AssertionError(f'{alloy} not an option at {gauge_um} µm')


class GradeTableTests(unittest.TestCase):
    """SPEC13 part 1: alloy and temper by gauge (second battery survey)."""
    PID = 'battery_collector_foil'

    def test_band_lookup(self):
        for um, band in ((8, 'le10'), (9, 'le10'), (10, 'le10'), (10.001, '10_13'),
                         (12, '10_13'), (13, '10_13'), (13.001, '13_15'), (15, '13_15'),
                         (15.001, '15_20'), (18, '15_20'), (20, '15_20'), (20.001, '20_30'),
                         (25, '20_30'), (30, '20_30')):
            g = bp.gauge_band(self.PID, um * UM)
            self.assertEqual(g['status'], 'IN_BAND', um)
            self.assertEqual(g['band_id'], band, um)
        for um in (7.99, 5, 30.01, 40):
            g = bp.gauge_band(self.PID, um * UM)
            self.assertEqual(g['status'], 'OUTSIDE_PUBLISHED_BANDS', um)
            self.assertIsNone(g['band'])
            self.assertIn('every published band', g['reason'])
        self.assertEqual(bp.gauge_band('household_foil', 10 * UM)['status'], 'NO_GRADE_TABLE')
        self.assertEqual(bp.gauge_band('battery_pouch_laminate_foil', 40 * UM)['band_id'],
                         'pouch_35_55')
        self.assertEqual(bp.gauge_band('battery_thick_collector_foil', 45 * UM)['band_id'],
                         'thick_20_50')
        with self.assertRaises(ValueError):
            bp.gauge_band(self.PID, -1.0)

    def test_gb_minima_pinned(self):
        want = {
            8: {'1070': 185, '1100': 230, '1C30': 220, '8011': 180, '1060': None,
                '1050': None, '1235': None},
            12: {'1070': 185, '1060': 190, '1050': 190, '1235': 180, '1100': 230, '1C30': 230,
                 '8011': 180},
            15: {'1070': 180, '1060': 190, '1050': 190, '1235': 185, '1100': 220, '1C30': 225,
                 '8011': 180, '8A21': 165},
            18: {'1070': 175, '1060': 185, '1050': 185, '1235': 175, '1100': 220, '1C30': 220,
                 '8011': None},
            25: {'1235': None, '1N30': None, '1085': None, '3003': None},
        }
        for um, table in want.items():
            for alloy, v in table.items():
                o = _opt(self.PID, um, alloy)
                if v is None:
                    self.assertIsNone(o['standard_min_rm_pa'], (um, alloy))
                else:
                    self.assertAlmostEqual(o['standard_min_rm_pa'], v * 1e6, msg=(um, alloy))
                    self.assertEqual(o['standard_min_sources'], ['BG-G2'])
        # the 8011 correction: 180 at every band that sets a value, never 220-230
        for um in (10, 12, 15):
            self.assertAlmostEqual(_opt(self.PID, um, '8011')['standard_min_rm_pa'], 180e6)
            self.assertEqual(_opt(self.PID, um, '8011')['grade'], 'standard')

    def test_grade_options_marks_not_removes(self):
        g = bp.grade_options(self.PID, 12 * UM, min_tensile_strength_pa=200e6)
        alloys = [o['alloy'] for o in g['options']]
        self.assertEqual(len(alloys), len(bp.BAND_10_13.options))
        by = {o['alloy']: o for o in g['options']}
        self.assertEqual(by['1235']['requested_minimum_check'], 'BELOW_REQUESTED_MINIMUM')
        self.assertTrue(by['1235']['below_requested_minimum'])
        self.assertEqual(by['1060']['requested_minimum_check'], 'NOT_GUARANTEED')
        self.assertEqual(by['1100']['requested_minimum_check'], 'MEETS_REQUESTED_MINIMUM')
        self.assertIn('never a claim that one alloy is best', g['ordering_rule'])
        self.assertTrue(by['1100']['usual'] and by['1235']['usual'])
        self.assertFalse(by['1C30']['usual'])
        usual_first = [o['usual'] for o in g['options']]
        self.assertEqual(usual_first, sorted(usual_first, reverse=True))
        self.assertEqual(by['1100']['evidence'], 'medium')
        self.assertEqual(by['1100']['temper_labels'], ['H18', 'H19'])
        self.assertAlmostEqual(by['1100']['conductivity_iacs_fraction'][0], 0.56)
        none = bp.grade_options(self.PID, 12 * UM)
        self.assertTrue(all(o['requested_minimum_check'] is None for o in none['options']))
        # surface: 8021 at 10 µm is usual only for one-side-bright foil
        self.assertTrue(_opt(self.PID, 10, '8021')['surface_mismatch'])
        self.assertFalse(_opt(self.PID, 10, '8021', surface='one_side_bright')['surface_mismatch'])
        # pouch alloy outside its own gauge span is marked
        self.assertTrue(_opt('battery_pouch_laminate_foil', 36, '8079')['outside_alloy_gauge_span'])
        json.dumps(g, allow_nan=False)

    def _prop(self, um, grade, **kw):
        p = bp.proposed_material(self.PID, um * UM, grade=grade, **kw)
        self.assertEqual(p['status'], 'LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT')
        self.assertTrue(p['rule'])
        json.dumps(p, allow_nan=False)
        return p

    def test_proposals(self):
        p = self._prop(18, 'standard')
        self.assertEqual((p['alloy'], p['temper'], p['band_id']), ('1235', 'H18', '15_20'))
        self.assertAlmostEqual(p['tensile_strength_pa']['value_pa'], 210e6)
        self.assertEqual(p['tensile_strength_pa']['range_pa'], [175e6, 220e6])
        self.assertFalse(p['proof_strength']['published'])
        self.assertIn('not published', p['proof_strength']['basis'])
        p = self._prop(12, 'standard')
        self.assertEqual(p['alloy'], '1235')
        self.assertAlmostEqual(p['tensile_strength_pa']['value_pa'], 180e6)
        self.assertEqual(p['evidence'], 'medium')
        p = self._prop(12, 'high_strength')
        self.assertEqual(p['alloy'], '1100')
        self.assertAlmostEqual(p['tensile_strength_pa']['value_pa'], 250e6)
        self.assertAlmostEqual(p['tensile_strength_pa']['standard_min_pa'], 230e6)
        self.assertIn('usual high-strength choice', p['rule'])
        p = self._prop(18, 'high_strength')  # no usual high-strength choice at >15-20
        self.assertEqual(p['alloy'], '1100')
        self.assertEqual(p['evidence'], 'weak')
        self.assertIn('no usual choice', p['rule'])
        p = self._prop(15, 'standard', alloy='1085')
        self.assertTrue(p['proof_strength']['published'])
        self.assertAlmostEqual(p['proof_strength']['value_pa'], 164e6)
        self.assertEqual(self._prop(10, 'standard', surface='one_side_bright')['alloy'], '8021')
        self.assertEqual(self._prop(10, 'standard')['alloy'], '1070')
        no = bp.proposed_material(self.PID, 40 * UM)
        self.assertEqual(no['status'], 'NO_LITERATURE_PROPOSAL')
        no = bp.proposed_material('battery_pouch_laminate_foil', 40 * UM, grade='high_strength')
        self.assertEqual(no['status'], 'NO_LITERATURE_PROPOSAL')
        self.assertEqual(bp.proposed_material('battery_pouch_laminate_foil', 40 * UM)['alloy'],
                         '8021')
        with self.assertRaises(ValueError):
            bp.proposed_material(self.PID, 12 * UM, grade='strong')

    def test_temper_naming_and_band_aware_check(self):
        for t in ('H18', 'H19'):
            f = by_item(check_pass(self.PID, 30 * UM, 12 * UM, temper=t, is_final_pass=True))
            self.assertEqual(f['temper']['verdict'], 'WITHIN_PUBLISHED_RANGE', t)
            self.assertIn('H18 and H19 are both consistent', f['temper']['basis'])
            self.assertIn('European sources call the same product H19', f['temper']['note'])
        f = by_item(check_pass(self.PID, 30 * UM, 12 * UM, temper='O'))
        self.assertEqual(f['temper']['verdict'], 'NO_PUBLISHED_RANGE')
        # 1235 at 12 µm is judged against the >10-13 µm row (minimum 180, no typical top)
        f = by_item(check_pass(self.PID, 25 * UM, 12 * UM, alloy='1235',
                               mean_flow_stress_pa=175e6))
        ind = f['mean_flow_stress_indicator']
        self.assertEqual(ind['verdict'], 'BELOW_PUBLISHED_RANGE')
        self.assertAlmostEqual(ind['published_low'], 180e6)
        self.assertIn('>10–13 µm', ind['basis'])
        self.assertIn('INDICATOR ONLY', ind['basis'])
        self.assertIn('>10–13 µm', f['alloy']['basis'])
        f = by_item(check_pass(self.PID, 30 * UM, 18 * UM, alloy='1235',
                               mean_flow_stress_pa=230e6))
        self.assertEqual(f['mean_flow_stress_indicator']['verdict'], 'ABOVE_PUBLISHED_RANGE')
        self.assertAlmostEqual(f['mean_flow_stress_indicator']['published_high'], 220e6)
        f = by_item(check_pass(self.PID, 30 * UM, 18 * UM, alloy='3003'))
        self.assertEqual(f['alloy']['verdict'], 'NO_PUBLISHED_RANGE')
        self.assertIn('listed for the product at other gauges', f['alloy']['basis'])

    def test_general_grade_facts(self):
        self.assertEqual(len(bp.GRADE_REASONS), 8)
        self.assertEqual(len(bp.GRADE_DISAGREEMENTS), 8)
        self.assertEqual(len(bp.GRADE_NOT_FOUND), 7)
        self.assertEqual([t.temper for t in bp.TEMPER_TABLE],
                         ['H18', 'H19', 'High-strength grades', 'H2x', 'O'])
        red = [v.low for v in bp.TEMPER_TABLE[0].route.values]
        self.assertAlmostEqual(red[0], 0.97)
        self.assertAlmostEqual(red[1], 0.988)
        losses = [sh.loss_fraction() for sh in bp.STRENGTH_AFTER_HEATING[:3]]
        self.assertEqual(round(losses[0][0] * 100), 10)
        self.assertEqual(round(losses[1][0] * 100), 27)
        self.assertEqual((round(losses[2][0] * 100), round(losses[2][1] * 100)), (23, 28))
        self.assertEqual(bp.STRENGTH_AFTER_HEATING[0].steps[3].temperature_c, 200)
        for p in ('battery_thick_collector_foil', 'battery_carbon_coated_base_foil',
                  'battery_tab_foil'):
            self.assertTrue(product(p).evidence)
        self.assertNotIn('cell_case', [p for p in product_ids() if 'case' in p])
        self.assertIn('not foil', bp.CELL_CASE_STOCK.text)


class PackagedSurveyDefaultsTests(unittest.TestCase):
    """Packaging review: the product survey's default mills ship inside the package
    (``physicroll.band_survey_mills``), not as files read from the repository checkout."""

    SCEN = Path(__file__).resolve().parents[1] / 'scenarios'

    def test_packaged_mills_equal_the_demo_machine_sections(self):
        if not self.SCEN.is_dir():
            self.skipTest('scenarios directory not present (installed package): no drift '
                          'guard source')
        from physicroll import band_diagnosis as bd
        from physicroll import band_survey as bs
        from physicroll.band_survey_mills import MACHINES
        for kind, meta in bs.MILLS.items():
            case = bd.load_case(self.SCEN / meta['scenario'])
            for sec, keys in bs.MACHINE_KEYS.items():
                want = case.get(sec)
                if want is not None and keys != 'all':
                    want = {k: want[k] for k in keys if k in want}
                self.assertEqual(MACHINES[kind][sec], want, f'{kind}.{sec}')
            # the default mill case carries exactly those machine values
            mc = bs.default_mill_case(kind)
            self.assertEqual(bs.machine_keys_taken(mc), bs.machine_keys_taken(case))

    def test_survey_and_entry_points_run_without_the_checkout(self):
        import shutil
        import subprocess
        import sys
        import tempfile
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(root / 'physicroll', Path(tmp) / 'physicroll',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            outside = Path(tmp) / 'outside'
            outside.mkdir()
            code = ("import json, sys; sys.path.insert(0, %r); "
                    "from physicroll import band_survey as bs; "
                    "r = bs.survey(['litho_sheet', 'battery_pouch_laminate_foil']); "
                    "assert [x['mill'] for x in r['rows']] == ['foil', 'sheet']; "
                    "assert all(x['bite_status'] == 'BITE' for x in r['rows']); "
                    "bs.render_survey_report(r); print('ok')") % tmp
            out = subprocess.run([sys.executable, '-I', '-c', code], cwd=outside,
                                 capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout.strip(), 'ok')
            env_code = ("import sys; sys.path.insert(0, %r); "
                        "from physicroll import band_products; "
                        "band_products.main(['--list'])") % tmp
            out = subprocess.run([sys.executable, '-I', '-c', env_code], cwd=outside,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn('battery_collector_foil', out.stdout)
            self.assertFalse((Path(tmp) / 'scenarios').exists())


if __name__ == '__main__':
    unittest.main()
