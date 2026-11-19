"""SPEC14 part 1: the process-temperature reference (sources PT-) and check_thermal."""
import contextlib
import io
import json
import math
import unittest
from pathlib import Path

from physicroll import band_products as bp
from physicroll.band_products import check_thermal, process_temperature_reference, sources

DOC = Path(__file__).resolve().parents[1] / 'docs' / 'thin-gauge-products.md'
C = 'battery_collector_foil'


def one(findings, item):
    hits = [f for f in findings if f['item'] == item]
    assert len(hits) == 1, (item, findings)
    return hits[0]


class ReferenceTests(unittest.TestCase):
    def test_sources_and_integrity(self):
        pt = sorted(int(k[4:]) for k in sources() if k.startswith('PT-'))
        self.assertEqual(pt, [n for n in range(1, 40) if n != 35])   # T35 is PK-S7
        self.assertEqual(sources()['PT-T16'].read_status, 'abstract_or_snippet')
        self.assertEqual(sources()['PT-T18'].read_status, 'excerpt')   # garbled mirror
        self.assertEqual(sources()['PT-T9'].read_status, 'full_text')
        self.assertEqual(sources()['PT-T10'].read_status, 'vendor_or_trade_page')
        ref = process_temperature_reference()
        self.assertEqual(json.loads(json.dumps(ref, allow_nan=False)), ref)
        self.assertEqual(len(ref['headline_findings']), 4)
        self.assertEqual(len(ref['temperature_map']), 8)
        self.assertEqual(len(ref['disagreements']), 4)
        self.assertIn('no roll-wear model', ref['not_a_model'])
        for f in bp._all_facts():
            for s in f.sources:
                self.assertIn(s, sources())

    def test_published_ranges_pinned(self):
        pins = ((bp.COIL_IN_FINAL_LIMIT, None, 75), (bp.COIL_OUT_FINAL_LIMIT, None, 80),
                (bp.COIL_OUT_FINAL_LIMIT_LOOSE, None, 90), (bp.OIL_ROUGHING, 30, 40),
                (bp.OIL_INTERMEDIATE, 40, 50), (bp.OIL_FINISHING, 50, 60),
                (bp.OIL_FINISHING_BATTERY, 40, 45), (bp.OIL_WINDOW_PLANT, 38, 55),
                (bp.OIL_CAP_FOIL, None, 71), (bp.OIL_CAP_COLD, None, 68),
                (bp.COIL_OUT_SHEET_TROUBLE, 150, 160), (bp.HOT_EDGE, None, 120))
        for r, lo, hi in pins:
            self.assertEqual((r.low, r.high), (lo, hi), r.note)
            self.assertEqual(r.unit, 'degC')
        self.assertEqual((bp.HEAT_STRIP_SHARE.low, bp.HEAT_STRIP_SHARE.high), (0.11, 0.33))
        self.assertEqual((bp.HEAT_ROLL_SHARE.low, bp.HEAT_ROLL_SHARE.high), (0.67, 0.89))
        self.assertEqual(bp.HEAT_STRIP_SHARE.effective_read_status(), 'abstract_or_snippet')
        self.assertEqual((bp.SPRAY_ROLL.low, bp.SPRAY_ROLL.high), (2500.0, 4300.0))
        self.assertAlmostEqual(bp.SPRAY_PLATE.low, 31e3 / 6, places=3)
        self.assertAlmostEqual(bp.SPRAY_PLATE.high, 38e3 / 3, places=3)
        self.assertEqual(bp.SPRAY_PLATE.read_status, 'computed')
        self.assertAlmostEqual(bp.VISC_40C.low, 1.5e-6)
        self.assertAlmostEqual(bp.VISC_40C.high, 2.0e-6)
        self.assertAlmostEqual(bp.VISC_PER_K.low, -0.017, places=3)
        self.assertAlmostEqual(bp.THERMAL_CROWN_MAX.high, 30e-6)
        self.assertEqual((bp.ZONE_AUTHORITY.low, bp.ZONE_AUTHORITY.high), (3.6e-6, 4.2e-6))
        self.assertEqual((bp.CONTACT_MODELS.low, bp.CONTACT_MODELS.high), (25e3, 40e3))
        self.assertEqual((bp.CONTACT_MEASURED.low, bp.CONTACT_MEASURED.high), (7e3, 800e3))
        self.assertAlmostEqual(bp.AXIAL_TAU.low, 0.104 ** 2 / (4 * math.pi ** 2 * 1.2e-5))
        self.assertTrue(20 <= bp.AXIAL_TAU.low <= 25)
        self.assertEqual((bp.RADIAL_TAU.low, bp.RADIAL_TAU.high), (240.0, 420.0))
        self.assertEqual(bp.RADIAL_TAU.read_status, 'computed')
        self.assertAlmostEqual(bp.FREE_EXPANSION.low, 3.0e-6)

    def test_overlap_rule(self):
        o, never, pitch = bp.SPRAY_OVERLAP.values
        self.assertEqual((o.low, o.high, never.high), (0.10, 0.30, 0.50))
        self.assertEqual((pitch.low, pitch.high), (0.025, 0.1))


class CheckThermalTests(unittest.TestCase):
    def test_coil_limits_battery_only(self):
        f = one(check_thermal(C, coil_temperature_leaving_final_pass_c=78),
                'coil_temperature_leaving_final_pass')
        self.assertEqual(f['verdict'], 'WITHIN_PUBLISHED_RANGE')
        f = one(check_thermal(C, coil_temperature_leaving_final_pass_c=85),
                'coil_temperature_leaving_final_pass')
        self.assertEqual(f['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        self.assertEqual(f['published_high'], 80)
        self.assertNotIn('above 90', f['note'])
        f = one(check_thermal(C, coil_temperature_leaving_final_pass_c=98),
                'coil_temperature_leaving_final_pass')
        self.assertIn('above 90 °C', f['note'])
        f = one(check_thermal(C, coil_temperature_entering_final_pass_c=76),
                'coil_temperature_entering_final_pass')
        self.assertEqual(f['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        for pid in ('household_foil', 'battery_pouch_laminate_foil'):
            f = one(check_thermal(pid, coil_temperature_leaving_final_pass_c=98),
                    'coil_temperature_leaving_final_pass')
            self.assertEqual(f['verdict'], 'NO_PUBLISHED_RANGE')
        f = one(check_thermal('litho_sheet', coil_temperature_leaving_final_pass_c=155),
                'coil_temperature_leaving_final_pass')
        self.assertEqual(f['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        self.assertIn('150–160', f['basis'])

    def test_oil_and_inputs(self):
        f = one(check_thermal(C, oil_supply_temperature_c=42), 'oil_supply_temperature')
        self.assertEqual((f['verdict'], f['published_low'], f['published_high']),
                         ('WITHIN_PUBLISHED_RANGE', 40, 45))
        f = one(check_thermal('household_foil', oil_supply_temperature_c=42),
                'oil_supply_temperature')
        self.assertEqual((f['verdict'], f['published_low']), ('BELOW_PUBLISHED_RANGE', 50))
        f = one(check_thermal(C, oil_supply_temperature_c=35, stand='roughing'),
                'oil_supply_temperature')
        self.assertEqual(f['verdict'], 'WITHIN_PUBLISHED_RANGE')
        self.assertIn('ladder', f['note'])
        f = one(check_thermal(C, oil_supply_temperature_c=75), 'oil_supply_temperature')
        self.assertEqual(f['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        f = one(check_thermal(C, strip_heat_fraction=0.84), 'strip_heat_fraction')
        self.assertEqual(f['verdict'], 'ABOVE_PUBLISHED_RANGE')
        self.assertEqual(f['read_status'], 'abstract_or_snippet')
        self.assertIn('net balance', f['basis'])
        self.assertEqual(one(check_thermal(C, strip_heat_fraction=0.2),
                             'strip_heat_fraction')['verdict'], 'WITHIN_PUBLISHED_RANGE')
        f = one(check_thermal(C, spray_htc_w_m2k=2000), 'spray_heat_transfer_coefficient')
        self.assertEqual(f['verdict'], 'BELOW_PUBLISHED_RANGE')
        self.assertIn('SIMULATED', f['basis'])
        self.assertEqual(one(check_thermal(C, oil_viscosity_40c_m2_s=2.5e-6),
                             'oil_viscosity_40c')['verdict'], 'ABOVE_PUBLISHED_RANGE')
        self.assertEqual(one(check_thermal(C, thermal_crown_m=35e-6),
                             'thermal_crown')['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        self.assertEqual(one(check_thermal(C, stripe_height_diameter_m=1e-6),
                             'stripe_height_on_diameter')['verdict'], 'BELOW_PUBLISHED_RANGE')
        self.assertEqual(one(check_thermal(C, bite_contact_conductance_w_m2k=3e4),
                             'bite_contact_conductance')['verdict'], 'WITHIN_PUBLISHED_RANGE')

    def test_shape_errors_and_empty(self):
        self.assertEqual(check_thermal(C), [])
        out = check_thermal(C, coil_temperature_leaving_final_pass_c=90, strip_heat_fraction=0.5,
                            spray_htc_w_m2k=3e3, oil_supply_temperature_c=50)
        for f in out:
            self.assertEqual(set(f), {'item', 'value', 'published_low', 'published_high',
                                      'unit', 'verdict', 'basis', 'sources', 'read_status',
                                      'note'})
            self.assertIn(f['verdict'], bp.VERDICTS)
        for bad in (dict(strip_heat_fraction=1.5), dict(strip_heat_fraction=-0.1),
                    dict(spray_htc_w_m2k=float('nan')), dict(stand='finish')):
            with self.assertRaises(ValueError):
                check_thermal(C, **bad)
        with self.assertRaises(ValueError):
            check_thermal('nope', strip_heat_fraction=0.2)


class DocumentTests(unittest.TestCase):
    def test_document_section(self):
        text = bp.render_reference_markdown()
        self.assertEqual(DOC.read_text(encoding='utf-8'), text)
        i = text.index('## Process temperatures in foil rolling')
        self.assertLess(i, text.index('## 1. Li-ion cathode current-collector foil'))
        sec = text[i:text.index('## 1. Li-ion')]
        self.assertLess(sec.index('### Temperature map'), sec.index('### Four findings first'))
        for want in ('≤80 °C', '67–89 %', '2.5–4.3', 'no roll-wear model', '10–30 %',
                     '### Not found (process temperatures)'):
            self.assertIn(want, sec)

    def test_cli_prints_the_map(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(bp.main(['--temperatures']), 0)
        self.assertIn('Coil off the final pass, battery foil', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
