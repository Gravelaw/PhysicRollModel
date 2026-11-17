import json
import math
import unittest

from physicroll.band_signatures import (
    MillKinematics, bearing_defect_orders, bending_surface_strain, coil_locked_pitch_m,
    film_ratio_regime, fixed_frequency_pitch_m, flat_fan_footprint_width_m, forward_slip_screen,
    free_thermal_radius_growth_m, herringbone_screen, inlet_angle_rad,
    inlet_film_thickness_wilson_walowit, local_gap_closure_fraction, luders_susceptibility,
    match_band_positions, match_observed_pitch, order_locked_pitch_m, pass_reduction_vs_luders,
    pitch_speed_exponent, resonance_speeds, roll_mark_pitch_m, source_catalogue, spray_coverage,
    stretched_pitch_m, thermal_stripe_screen, yield_point_bending_window)

DW, DB, SLIP, SPEED = 0.4, 1.2, 0.05, 10.0
BEARING = {'name': 'wr_chock', 'shaft': 'work_roll', 'elements': 9,
           'element_diameter_m': 0.02, 'pitch_diameter_m': 0.1, 'contact_angle_rad': 0.2}
MILL = MillKinematics(
    work_roll_diameter_m=DW, backup_roll_diameter_m=DB,
    gear_meshes=({'name': 'pinion', 'teeth': 25, 'shaft_speed_ratio_to_work_roll': 1.0},),
    bearings=(BEARING,),
    grinder_marks=({'roll': 'backup_roll', 'marks_per_circumference': 3},),
    deflector_roll_diameters_m=(0.3,), entry_coil_diameter_m=1.5, exit_coil_diameter_m=1.0,
    structural_modes_hz=({'name': 'third_octave', 'frequency_hz': 150.0,
                          'family': 'third_octave'},))


def dumps(value):
    return json.dumps(value, allow_nan=False)


class PitchLawTests(unittest.TestCase):
    def test_speed_doubling(self):
        self.assertAlmostEqual(fixed_frequency_pitch_m(20, 150) / fixed_frequency_pitch_m(10, 150),
                               2.0)
        self.assertAlmostEqual(roll_mark_pitch_m(DW, SLIP), math.pi * DW * 1.05)
        self.assertAlmostEqual(roll_mark_pitch_m(DB, SLIP, 3), math.pi * DB * 1.05 / 3)
        self.assertAlmostEqual(order_locked_pitch_m(DW, SLIP, 2), math.pi * DW * 1.05 / 2)
        self.assertAlmostEqual(coil_locked_pitch_m(1.0), math.pi)
        self.assertAlmostEqual(stretched_pitch_m(0.02, 0.6e-3, 0.42e-3), 0.02 * 0.6 / 0.42)
        slow = source_catalogue(MILL, SPEED, SLIP)
        fast = {e['id']: e for e in source_catalogue(MILL, 2 * SPEED, SLIP)}
        for e in slow:
            if e['strip_pitch_m'] is None:
                continue
            ratio = fast[e['id']]['strip_pitch_m'] / e['strip_pitch_m']
            if e['pitch_speed_law'] == 'proportional_to_speed':
                self.assertAlmostEqual(ratio, 2.0)
            else:
                self.assertAlmostEqual(ratio, 1.0)

    def test_exponent_classification(self):
        fixed = pitch_speed_exponent([(u, u / 100.0) for u in (5.0, 10.0, 20.0)])
        self.assertAlmostEqual(fixed['slope'], 1.0, places=12)
        self.assertEqual(fixed['status'], 'FIXED_FREQUENCY')
        for f in fixed['implied_frequency_hz']:
            self.assertAlmostEqual(f, 100.0)
        flat = pitch_speed_exponent([{'exit_speed_m_s': u, 'pitch_m': 0.022} for u in (4, 8)])
        self.assertAlmostEqual(flat['slope'], 0.0, places=12)
        self.assertEqual(flat['classification'], 'SPEED_INDEPENDENT_PITCH')
        self.assertIn('TWO_POINT_FIT_NO_RESIDUAL_CHECK', flat['flags'])
        mid = pitch_speed_exponent([(u, 0.01 * u ** 0.5) for u in (2.0, 4.0, 8.0)])
        self.assertAlmostEqual(mid['slope'], 0.5, places=12)
        self.assertEqual(mid['status'], 'INDETERMINATE')
        self.assertIn('ANALYST_CHOICE', mid['threshold_basis'])
        for bad in ([(5, 0.1)], [(5, 0.1), (5, 0.2)], [(5, 0.1), (True, 0.2)],
                    [(5, 0.1), (6, float('nan'))], 'ab', [(5, 0.1), (6, -0.1)]):
            with self.assertRaises(ValueError):
                pitch_speed_exponent(bad)


class BearingTests(unittest.TestCase):
    def test_identities(self):
        o = bearing_defect_orders(9, 0.02, 0.1, 0.2)
        r = 0.02 / 0.1 * math.cos(0.2)
        self.assertAlmostEqual(o['bpfo_order'] + o['bpfi_order'], 9)
        self.assertAlmostEqual(o['bpfo_order'], 9 * o['ftf_order'])
        self.assertAlmostEqual(o['bsf_order'], 0.1 / 0.04 * (1 - r * r))
        dumps(o)
        for args in ((2, 0.02, 0.1, 0), (9, 0.1, 0.1, 0), (9, 0.02, 0.1, math.pi / 2),
                     (9.0, 0.02, 0.1, 0), (True, 0.02, 0.1, 0), (30, 0.02, 0.1, 0)):
            with self.assertRaises(ValueError):
                bearing_defect_orders(*args)


class CatalogueTests(unittest.TestCase):
    def test_entries_and_consistency(self):
        cat = source_catalogue(MILL, SPEED, SLIP, entry_exit_thickness_ratio=1.25)
        dumps(cat)
        ids = {e['id']: e for e in cat}
        for expected in ('work_roll_1x', 'work_roll_2x', 'backup_roll_1x', 'backup_roll_2x',
                         'gear_mesh:pinion', 'bearing:wr_chock:bpfo', 'bearing:wr_chock:bpfi',
                         'bearing:wr_chock:bsf', 'bearing:wr_chock:ftf',
                         'bearing:wr_chock:2x_bpfi', 'grinder_marks:backup_roll:0',
                         'deflector_roll:0', 'exit_coil', 'entry_coil',
                         'structural_mode:third_octave'):
            self.assertIn(expected, ids)
        for e in cat:
            self.assertAlmostEqual(e['strip_pitch_m'] * e['frequency_hz'], SPEED)
        fwr = SPEED / 1.05 / (math.pi * DW)
        self.assertAlmostEqual(ids['work_roll_1x']['frequency_hz'], fwr)
        self.assertAlmostEqual(ids['backup_roll_1x']['strip_pitch_m'], math.pi * DB * 1.05)
        self.assertAlmostEqual(ids['grinder_marks:backup_roll:0']['strip_pitch_m'],
                               math.pi * DB * 1.05 / 3)
        self.assertAlmostEqual(ids['gear_mesh:pinion']['frequency_hz'], 25 * fwr)
        bpfi = bearing_defect_orders(9, 0.02, 0.1, 0.2)['bpfi_order']
        self.assertAlmostEqual(ids['bearing:wr_chock:2x_bpfi']['order_of_work_roll_rotation'],
                               2 * bpfi)
        self.assertAlmostEqual(ids['deflector_roll:0']['strip_pitch_m'], math.pi * 0.3)
        self.assertAlmostEqual(ids['exit_coil']['strip_pitch_m'], math.pi * 1.0)
        self.assertAlmostEqual(ids['entry_coil']['strip_pitch_m'], math.pi * 1.5 * 1.25)
        self.assertAlmostEqual(ids['structural_mode:third_octave']['strip_pitch_m'], SPEED / 150)
        self.assertEqual(ids['structural_mode:third_octave']['family'], 'third_octave')
        self.assertIsNone(ids['exit_coil']['order_of_work_roll_rotation'])
        no_ratio = {e['id']: e for e in source_catalogue(MILL, SPEED, SLIP)}
        self.assertIsNone(no_ratio['entry_coil']['strip_pitch_m'])
        self.assertIsNone(no_ratio['entry_coil']['frequency_hz'])

    def test_match_observed_pitch(self):
        cat = source_catalogue(MILL, SPEED, SLIP)
        hits = match_observed_pitch(cat, SPEED / 150 * 1.03)
        self.assertEqual(hits[0]['id'], 'structural_mode:third_octave')
        self.assertAlmostEqual(hits[0]['relative_pitch_mismatch'], abs(1 / 1.03 - 1))
        self.assertEqual([h['relative_pitch_mismatch'] for h in hits],
                         sorted(h['relative_pitch_mismatch'] for h in hits))
        self.assertEqual(match_observed_pitch(cat, 50.0), [])
        with self.assertRaises(ValueError):
            match_observed_pitch(cat, 0.01, tolerance_fraction=0)

    def test_resonance_round_trip(self):
        res = resonance_speeds(MILL, SLIP, 150.0)
        dumps(res)
        self.assertTrue(res)
        speeds = [r['resonant_exit_speed_m_s'] for r in res]
        self.assertEqual(speeds, sorted(speeds))
        wr = {r['id']: r for r in res}['work_roll_1x']
        self.assertAlmostEqual(wr['resonant_exit_speed_m_s'], 150.0 * math.pi * DW * 1.05)
        self.assertFalse({r['id']: r for r in res}['backup_roll_1x']['within_speed_envelope'])
        for r in res:
            if not r['within_speed_envelope']:
                continue
            at = {e['id']: e for e in source_catalogue(MILL, r['resonant_exit_speed_m_s'], SLIP)}
            self.assertAlmostEqual(at[r['id']]['frequency_hz'], 150.0)
            self.assertAlmostEqual(at[r['id']]['strip_pitch_m'], r['strip_pitch_m'])
        self.assertNotIn('exit_coil', {r['id'] for r in res})
        self.assertNotIn('structural_mode:third_octave', {r['id'] for r in res})

    def test_mill_validation(self):
        bad = [dict(work_roll_diameter_m=0.4, backup_roll_diameter_m=0.3),
               dict(work_roll_diameter_m=float('nan'), backup_roll_diameter_m=1.2),
               dict(work_roll_diameter_m=True, backup_roll_diameter_m=1.2),
               dict(work_roll_diameter_m=0.4, backup_roll_diameter_m=1.2,
                    gear_meshes=({'name': 'g', 'teeth': 0,
                                  'shaft_speed_ratio_to_work_roll': 1.0},)),
               dict(work_roll_diameter_m=0.4, backup_roll_diameter_m=1.2,
                    bearings=(dict(BEARING, shaft='spindle'),)),
               dict(work_roll_diameter_m=0.4, backup_roll_diameter_m=1.2,
                    bearings=(BEARING, BEARING)),
               dict(work_roll_diameter_m=0.4, backup_roll_diameter_m=1.2,
                    structural_modes_hz=({'name': 'm', 'frequency_hz': -1, 'family': 'x'},)),
               dict(work_roll_diameter_m=0.4, backup_roll_diameter_m=1.2,
                    exit_coil_diameter_m=float('inf'))]
        for kwargs in bad:
            with self.assertRaises(ValueError):
                MillKinematics(**kwargs).validate()
        for args in ((MILL, 0, SLIP), (MILL, 10, 0.6), (MILL, 10, float('nan')),
                     ('mill', 10, SLIP)):
            with self.assertRaises(ValueError):
                source_catalogue(*args)


class MaterialTests(unittest.TestCase):
    def test_aa5182_bending_window(self):
        eps_y = 139e6 / 70e9
        w = yield_point_bending_window(0.002, 0.5, 139e6, 70e9, 0.01, 0.0)
        self.assertEqual(w['status'], 'IN_YIELD_POINT_WINDOW')
        self.assertAlmostEqual(w['window_min_diameter_m'], 0.002 / (eps_y + 0.01))
        self.assertAlmostEqual(w['window_max_diameter_m'], 0.002 / eps_y)
        # 0.002 / 0.0119857 = 0.16687 m ; 0.002 / 0.0019857 = 1.00719 m (spec: ~167-1007 mm)
        self.assertAlmostEqual(w['window_min_diameter_m'], 0.16687, places=5)
        self.assertAlmostEqual(w['window_max_diameter_m'], 1.00719, places=5)
        self.assertEqual(yield_point_bending_window(0.002, 1.2, 139e6, 70e9, 0.01, 0)['status'],
                         'ELASTIC_NO_YIELD')
        self.assertEqual(yield_point_bending_window(0.002, 0.1, 139e6, 70e9, 0.01, 0)['status'],
                         'BEYOND_PLATEAU_UNIFORM_YIELD')
        tensioned = yield_point_bending_window(0.002, 1.2, 139e6, 70e9, 0.01, 50e6)
        self.assertEqual(tensioned['status'], 'IN_YIELD_POINT_WINDOW')
        self.assertAlmostEqual(tensioned['window_max_diameter_m'], 0.002 * 70e9 / 89e6)
        thin = yield_point_bending_window(0.0002, 0.5, 139e6, 70e9, 0.01, 0)
        self.assertEqual(thin['status'], 'ELASTIC_NO_YIELD')
        self.assertAlmostEqual(bending_surface_strain(0.0002, 0.5), 4e-4)
        dumps(w)
        for args in ((0.002, 0.5, 139e6, 70e9, 0.01, 139e6), (0.002, 0.5, -1, 70e9, 0.01, 0),
                     (0.6, 0.5, 139e6, 70e9, 0.01, 0), (0.002, 0.5, 139e6, 70e9, True, 0)):
            with self.assertRaises(ValueError):
                yield_point_bending_window(*args)

    def test_susceptibility_rules(self):
        cases = [(('AA5182', 'O', None, 30e-6), 'SUSCEPTIBLE_FINE_GRAIN'),
                 (('5182', 'O', None, 50e-6), 'SUSCEPTIBLE_WEAKENED_COARSE_GRAIN'),
                 (('EN AW-5754', 'O'), 'SUSCEPTIBLE'),
                 (('AA5182', 'H19'), 'NOT_SUSCEPTIBLE_COLD_WORKED'),
                 (('AA3104', 'O'), 'NOT_SUSCEPTIBLE_ALLOY'),
                 (('custom Al-Mg', 'O', 3.0), 'SUSCEPTIBLE'),
                 (('AA5182', 'T4'), 'INDETERMINATE_TEMPER'),
                 (('mystery', 'O'), 'INDETERMINATE_ALLOY')]
        for args, status in cases:
            r = luders_susceptibility(*args)
            self.assertEqual(r['status'], status, args)
            self.assertTrue(r['reasons'])
            dumps(r)
        self.assertEqual(luders_susceptibility('AA5182', 'O', prior_cold_work_fraction=0.02)
                         ['status'], 'NOT_SUSCEPTIBLE_COLD_WORKED')
        self.assertIn('GRAIN_SIZE_BEYOND_STATED_40_70_UM_RULE_RANGE',
                      luders_susceptibility('AA5182', 'O', grain_size_m=100e-6)['flags'])
        for args in (('', 'O'), ('AA5182', 'O', -1.0), ('AA5182', 'O', None, 0.0),
                     ('AA5182', 3)):
            with self.assertRaises(ValueError):
                luders_susceptibility(*args)

    def test_pass_reduction(self):
        r = pass_reduction_vs_luders(0.3, 0.01)
        self.assertEqual(r['status'], 'BITE_CANNOT_LEAVE_LUDERS_BANDS')
        self.assertAlmostEqual(r['thickness_true_strain'], -math.log(0.7))
        self.assertEqual(pass_reduction_vs_luders(0.01, 0.01)['status'],
                         'LIGHT_REDUCTION_LUDERS_BANDS_POSSIBLE')
        with self.assertRaises(ValueError):
            pass_reduction_vs_luders(1.0, 0.01)


class LubricationTests(unittest.TestCase):
    def test_slip_screen(self):
        self.assertEqual(forward_slip_screen(-0.01)['status'],
                         'SKIDDING_NEUTRAL_POINT_AT_OR_BEYOND_EXIT')
        self.assertEqual(forward_slip_screen(0)['status'],
                         'SKIDDING_NEUTRAL_POINT_AT_OR_BEYOND_EXIT')
        marginal = forward_slip_screen(0.003)
        self.assertEqual(marginal['status'], 'MARGINAL_FORWARD_SLIP')
        self.assertIn('ANALYST', marginal['threshold_basis'])
        self.assertEqual(forward_slip_screen(0.05)['status'], 'NORMAL')
        for bad in (True, float('nan'), 0.9):
            with self.assertRaises(ValueError):
                forward_slip_screen(bad)

    def test_herringbone(self):
        self.assertEqual(herringbone_screen(0.3, 0.008)['risk_level'], 'LOW')
        self.assertEqual(herringbone_screen(0.42, 0.008)['status'], 'HERRINGBONE_RISK_ELEVATED')
        hit = herringbone_screen(0.5, 0.008, observed_pitch_m=0.01)
        self.assertEqual(hit['risk_level'], 'HIGH')
        self.assertAlmostEqual(hit['pitch_to_contact_length_ratio'], 1.25)
        self.assertTrue(hit['pitch_consistent_with_contact_length'])
        miss = herringbone_screen(0.5, 0.008, 0.05)
        self.assertFalse(miss['pitch_consistent_with_contact_length'])
        self.assertIsNone(herringbone_screen(0.5, 0.008)['pitch_consistent_with_contact_length'])
        self.assertTrue(hit['sources'])
        with self.assertRaises(ValueError):
            herringbone_screen(0.5, 0)

    def test_film_formula(self):
        theta = inlet_angle_rad(0.6e-3, 0.42e-3, 0.2)
        self.assertAlmostEqual(theta, math.sqrt(0.18e-3 / 0.2))
        base = dict(viscosity_pa_s=0.005, pressure_viscosity_coefficient_per_pa=1e-8,
                    roll_surface_speed_m_s=5.0, strip_entry_speed_m_s=3.5,
                    inlet_angle_rad=0.03, plane_strain_yield_pa=2.9e8)
        r = inlet_film_thickness_wilson_walowit(**base)
        expected = 3 * 0.005 * 1e-8 * 8.5 / (0.03 * (1 - math.exp(-2.9)))
        self.assertAlmostEqual(r['film_thickness_m'] / expected, 1.0, places=12)
        self.assertIn('FORMULA_QUOTED_FROM_MEMORY_VERIFY_BEFORE_USE', r['flags'])
        faster = inlet_film_thickness_wilson_walowit(**dict(base, roll_surface_speed_m_s=10.0,
                                                            strip_entry_speed_m_s=7.0))
        thicker = inlet_film_thickness_wilson_walowit(**dict(base, viscosity_pa_s=0.01))
        self.assertAlmostEqual(faster['film_thickness_m'] / r['film_thickness_m'], 2.0)
        self.assertGreater(thicker['film_thickness_m'], r['film_thickness_m'])
        dumps(r)
        for key, value in (('viscosity_pa_s', 0), ('inlet_angle_rad', float('inf')),
                           ('pressure_viscosity_coefficient_per_pa', True)):
            with self.assertRaises(ValueError):
                inlet_film_thickness_wilson_walowit(**dict(base, **{key: value}))

    def test_film_ratio(self):
        mixed = film_ratio_regime(0.5e-6, 0.3e-6, 0.4e-6)
        self.assertAlmostEqual(mixed['film_ratio'], 1.0)
        self.assertEqual(mixed['regime'], 'MIXED')
        self.assertEqual(film_ratio_regime(0.4e-6, 0.3e-6, 0.4e-6)['status'],
                         'BOUNDARY_LUBRICATION')
        hydro = film_ratio_regime(2e-6, 0.3e-6, 0.4e-6)
        self.assertEqual(hydro['regime'], 'HYDRODYNAMIC')
        self.assertIn('THICK_FILM_SKIDDING_MATTE_RISK', hydro['flags'])
        with self.assertRaises(ValueError):
            film_ratio_regime(1e-6, 0, 0)


class SprayTests(unittest.TestCase):
    def test_footprint(self):
        self.assertAlmostEqual(flat_fan_footprint_width_m(0.15, math.radians(60)),
                               2 * 0.15 * math.tan(math.radians(30)))
        for args in ((0, 1.0), (0.1, 0), (0.1, math.pi), (True, 1.0)):
            with self.assertRaises(ValueError):
                flat_fan_footprint_width_m(*args)

    def test_uniform_header_fully_covered(self):
        # W = 2*0.1*tan(45 deg) = 0.2 = 2 x pitch: interior coverage exactly 2.
        r = spray_coverage(1.0, 0.1, 0.1, math.pi / 2)
        dumps(r)
        self.assertEqual(r['nozzle_count'], 10)
        self.assertAlmostEqual(r['nozzle_positions_m'][0], 0.05)
        self.assertTrue(r['fully_covered'])
        self.assertEqual(r['status'], 'UNIFORM_COVERAGE')
        self.assertEqual(r['modal_coverage_count'], 2)
        self.assertAlmostEqual(r['overlap_fraction'], 0.5)
        self.assertTrue(all(s['at_barrel_edge'] for s in r['stripes']))
        pattern = spray_coverage(1.0, 0.1, 0.15, math.radians(60))
        self.assertTrue(pattern['fully_covered'])
        self.assertEqual(pattern['status'], 'PERIODIC_COVERAGE_VARIATION_AT_NOZZLE_PITCH')
        offset = spray_coverage(1.0, 0.1, 0.1, math.pi / 2, offset_angle_rad=math.radians(10))
        self.assertAlmostEqual(offset['effective_footprint_width_m'],
                               0.2 * math.cos(math.radians(10)))

    def test_non_overlapping_fans_keep_every_gap(self):
        # SPEC6 6.0 bug 1: 1 m barrel, 0.1 m pitch, 0.02 m footprint -> gaps dominate, the modal
        # coverage count is 0, and every zero-coverage zone must still be reported.
        r = spray_coverage(1.0, 0.1, 0.1, 2 * math.atan(0.1))
        dumps(r)
        self.assertAlmostEqual(r['effective_footprint_width_m'], 0.02)
        self.assertEqual(r['modal_coverage_count'], 0)
        self.assertEqual(r['status'], 'UNCOVERED_STRIPES_PRESENT')
        gaps = [s for s in r['stripes'] if s['coverage_count'] == 0]
        interior = [s for s in gaps if not s['at_barrel_edge']]
        self.assertEqual(len(gaps), 11)
        self.assertEqual(len(interior), 9)
        self.assertTrue(all(s['cause'] == 'NOZZLE_PATTERN' and s['kind'] == 'UNCOVERED'
                            for s in interior))
        self.assertAlmostEqual(interior[0]['start_m'], 0.06)
        self.assertAlmostEqual(interior[0]['end_m'], 0.14)
        self.assertFalse(any(s['coverage_count'] > 0 for s in r['stripes']))
        blocked = spray_coverage(1.0, 0.1, 0.1, 2 * math.atan(0.1), blocked_nozzle_indices=(4,))
        merged = [s for s in blocked['stripes'] if s['cause'] == 'BLOCKED_NOZZLE']
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0]['start_m'], 0.36)
        self.assertAlmostEqual(merged[0]['end_m'], 0.54)

    def test_blocked_nozzle_stripe(self):
        w = 2 * 0.15 * math.tan(math.radians(30))
        r = spray_coverage(1.0, 0.1, 0.15, math.radians(60), blocked_nozzle_indices=(4,))
        self.assertEqual(r['status'], 'UNCOVERED_STRIPES_PRESENT')
        self.assertFalse(r['fully_covered'])
        holes = [s for s in r['stripes'] if s['coverage_count'] == 0]
        self.assertEqual(len(holes), 1)
        self.assertAlmostEqual(holes[0]['start_m'], 0.35 + w / 2)
        self.assertAlmostEqual(holes[0]['end_m'], 0.55 - w / 2)
        self.assertAlmostEqual(holes[0]['center_m'], 0.45)
        self.assertEqual(holes[0]['cause'], 'BLOCKED_NOZZLE')
        partial = spray_coverage(1.0, 0.1, 0.1, math.pi / 2, blocked_nozzle_indices=(4,))
        self.assertEqual(partial['status'], 'BLOCKED_NOZZLE_STRIPES_PRESENT')
        self.assertTrue(partial['fully_covered'])
        under = [s for s in partial['stripes'] if not s['at_barrel_edge']]
        self.assertEqual(len(under), 1)
        self.assertAlmostEqual(under[0]['start_m'], 0.35)
        self.assertAlmostEqual(under[0]['end_m'], 0.55)
        self.assertEqual(under[0]['coverage_count'], 1)
        match = match_band_positions(r['stripes'], [0.452, 0.8], 0.005)
        self.assertEqual(match['status'], 'SOME_OBSERVED_POSITIONS_MATCHED')
        self.assertEqual(match['unmatched_positions_m'], [0.8])
        dumps(match)
        for kwargs in (dict(blocked_nozzle_indices=(10,)), dict(blocked_nozzle_indices=(True,)),
                       dict(nozzle_pitch_m=2.0), dict(offset_angle_rad=-0.1)):
            with self.assertRaises(ValueError):
                spray_coverage(**dict(dict(barrel_length_m=1.0, nozzle_pitch_m=0.1,
                                           standoff_m=0.15, spray_angle_rad=1.0), **kwargs))
        with self.assertRaises(ValueError):
            match_band_positions(r['stripes'], [], 0.005)

    def test_thermal_growth_grows_with_thinner_gauge(self):
        dr = free_thermal_radius_growth_m(0.2, 1.2e-5, 0.2)
        self.assertAlmostEqual(dr, 4.8e-7)
        self.assertAlmostEqual(local_gap_closure_fraction(dr, 2e-3), 4.8e-4)
        thick = thermal_stripe_screen(0.2, 1.2e-5, 0.2, 2e-3)
        thin = thermal_stripe_screen(0.2, 1.2e-5, 0.2, 1e-4)
        self.assertEqual(thick['status'], 'LOCAL_GAP_EFFECT_SMALL')
        self.assertEqual(thin['status'], 'LOCAL_GAP_EFFECT_NOT_NEGLIGIBLE')
        self.assertAlmostEqual(thin['local_gap_closure_fraction'], 9.6e-3)
        self.assertIn('UPPER_BOUND_FREE_EXPANSION', thin['flags'])
        dumps(thin)
        with self.assertRaises(ValueError):
            free_thermal_radius_growth_m(0.2, float('nan'), 1)


class JsonTests(unittest.TestCase):
    def test_every_result_serialises(self):
        results = [pitch_speed_exponent([(5, 0.05), (10, 0.1)]),
                   bearing_defect_orders(9, 0.02, 0.1, 0.0),
                   source_catalogue(MILL, SPEED, SLIP), resonance_speeds(MILL, SLIP, 800.0),
                   yield_point_bending_window(0.002, 0.5, 139e6, 70e9, 0.01, 139e6 - 1),
                   luders_susceptibility('AA5182', 'O'), pass_reduction_vs_luders(0.3, 0.01),
                   forward_slip_screen(0.01), herringbone_screen(0.3, 0.01, 0.01),
                   film_ratio_regime(1e-6, 1e-7, 1e-7), spray_coverage(1.5, 0.1, 0.2, 1.0),
                   thermal_stripe_screen(0.2, 1.2e-5, 1, 1e-3)]
        for r in results:
            dumps(r)
        for r in results:
            if isinstance(r, dict):
                self.assertIn('status', r)
                self.assertIn('flags', r)
                self.assertIn('limitations', r)


if __name__ == '__main__':
    unittest.main()
