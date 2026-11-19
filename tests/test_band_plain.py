"""Tests of the plain-language layer of the band app (SPEC16 Part 1): questions, unit
conversion, answers <-> case, presets, the plain summary and the trust rule.

Software verification only: these tests check that the interface layer maps answers to the
engine's case keys and reads the engine's result faithfully. They say nothing about whether
the screening is right on a plant (it has not been compared with plant data).
"""
import copy
import json
import math
import re
from pathlib import Path
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from physicroll import band_process as bproc
from physicroll import band_thermal as bthermal
from physicroll import band_width as bw
from physicroll import roll_thermal as rt

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts' / 'band_diagnosis'
DIAGNOSIS_ARTIFACTS = ('battery-foil-demo', 'bearing-order-demo', 'lengthwise-bands-demo',
                       'thin-gauge-chatter-demo')

# The two plant dry-run results (SPEC15, kept outside the repository) are reproduced here by
# the features the plain layer reads: their flag lists, their tied leaders and scores, their
# observations, and a not-credible thin pass. Copied from the dry-run result files.
DRY_RUN_18UM_FLAGS = [
    'AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF', 'BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL',
    'BITE_MODEL_AUTO', 'CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT',
    'CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED',
    'CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS', 'DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL',
    'EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN', 'EXPERIMENTAL_MATTRESS_FOIL_MODEL',
    'FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES',
    'FOUNDATION_MODULUS_FROM_MEMORY_FORMULA', 'LUDERS_STRAIN_NOT_SUPPLIED_ZERO_USED_IN_WINDOWS',
    'MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN', 'MATTRESS_REGIME_FOIL', 'SYNTHETIC_INPUTS',
    'THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN']
DRY_RUN_12UM_FLAGS = sorted(
    set(DRY_RUN_18UM_FLAGS) - {'CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT'}
    | {'CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE',
       'REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN'})
DRY_RUN_18UM_TOP = (('cooling_zone_switching_transient', 6), ('heat_streak_or_film_variation', 6),
                    ('tension_troughs_or_creases', 6), ('nozzle_thermal_stripe', 5),
                    ('foil_tension_lines', 4))
DRY_RUN_12UM_TOP = (('cooling_zone_switching_transient', 6), ('tension_troughs_or_creases', 6),
                    ('foil_tension_lines', 5), ('nozzle_thermal_stripe', 5),
                    ('heat_streak_or_film_variation', 4))


def load_artifact(name):
    return json.loads((ARTIFACTS / f'{name}.result.json').read_text(encoding='utf-8'))


_CACHE = {}


def artifact(name):
    if name not in _CACHE:
        _CACHE[name] = load_artifact(name)
    return copy.deepcopy(_CACHE[name])


def dry_run_like(flags, top):
    """A battery-foil result reshaped to carry the dry-run features (tie, flags, observations,
    a not-credible thin pass in the gauge trend)."""
    r = artifact('battery-foil-demo')
    r['flags'] = list(flags)
    by_id = {h['id']: h for h in r['hypotheses']}
    lead = max(s for _, s in top)
    ordered = []
    for i, (hid, score) in enumerate(top, 1):
        h = by_id.pop(hid)
        h['score'] = score
        h['standing'] = 'CONSISTENT_LEADING' if score == lead else 'CONSISTENT'
        ordered.append(h)
    for h in by_id.values():
        if h['standing'] == 'CONSISTENT_LEADING':
            h['standing'] = 'CONSISTENT'
        h['score'] = min(h['score'], 3)
    r['hypotheses'] = ordered + sorted(by_id.values(), key=lambda h: (
        h['standing'] == 'CONTRADICTED', -h['score'], h['id']))
    for i, h in enumerate(r['hypotheses'], 1):
        h['rank'] = i
    r['leading_hypotheses'] = [h for h, s in top if s == lead]
    ob = r['inputs']['observation']
    for k in ob:
        ob[k] = [] if isinstance(ob[k], list) else None
    ob.update(orientation='longitudinal', lengthwise_continuity='both',
              worse_at_thinner_gauge=True)
    rows = r['width']['gauge_trend']['rows']
    if 'CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE' in flags:
        rows[-1]['bite_credibility'] = 'FORCE_OUTSIDE_REPORTED_RANGE'
    return r


def all_results():
    out = {n: artifact(n) for n in DIAGNOSIS_ARTIFACTS}
    out['dry-run-18um'] = dry_run_like(DRY_RUN_18UM_FLAGS, DRY_RUN_18UM_TOP)
    out['dry-run-12um'] = dry_run_like(DRY_RUN_12UM_FLAGS, DRY_RUN_12UM_TOP)
    return out


def worked_examples():
    return {pid: json.loads((ROOT / 'scenarios' / fn).read_text(encoding='utf-8'))
            for pid, fn, _, _ in bpl.WORKED_EXAMPLES}


_PRESETS = []


def all_presets():
    if not _PRESETS:
        _PRESETS.extend(bpl.presets(worked_examples()))
    return copy.deepcopy(_PRESETS)


def preset(pid):
    return next(p for p in all_presets() if p['id'] == pid)


def section_53_keys():
    """Dotted keys of section 5.3 (a), (b) and (c) of docs/band-diagnosis.md, expanded to the
    leaves of the sections it names whole (lists of records stay one key)."""
    t = json.loads((ROOT / 'scenarios' / 'band_diagnosis_template.json').read_text())
    keys = ['pass.work_roll_radius_m', 'pass.width_m', 'pass.friction_coefficient',
            'kinematics.backup_roll_diameter_m', 'kinematics.gear_meshes',
            'kinematics.bearings', 'kinematics.grinder_marks',
            'kinematics.deflector_roll_diameters_m', 'kinematics.entry_coil_diameter_m',
            'kinematics.exit_coil_diameter_m',
            'gauge_control.compensation_gain', 'gauge_control.bandwidth_hz',
            'gauge_control.force_filter_hz', 'drive.inertias_kg_m2', 'drive.stiffnesses_n_m_rad',
            'width_model.coolant_temperature_k', 'width_model.roll_heat_fraction_per_roll',
            'width_model.rolls_carrying_stripe', 'width_model.shape_disturbing_coefficient',
            'width_model.heredity_coefficient', 'width_model.cooling_zone_pitch_m',
            'width_model.strip_centre_m', 'width_model.deflector_roll_radius_m',
            'width_model.coil.inner_radius_m', 'width_model.coil.outer_radius_m',
            'width_model.coil.winding_tension_pa', 'width_model.coil.compaction_factor',
            'width_model.grinding.traverse_speed_m_s', 'width_model.grinding.roll_rotation_hz',
            'width_model.numerics.axial_cell_m', 'width_model.numerics.radial_cells',
            'width_model.numerics.time_step_s',
            # (b) the product and the pass
            'pass.entry_thickness_m', 'pass.exit_thickness_m', 'pass.mean_flow_stress_pa',
            'pass.entry_tension_pa', 'pass.exit_tension_pa', 'pass.exit_speed_m_s',
            'material.alloy', 'material.temper', 'material.yield_stress_pa',
            'material.youngs_modulus_pa', 'material.luders_strain', 'material.magnesium_wt_pct',
            'material.grain_size_m', 'material.final_pass_doubled', 'material.product',
            'schedule', 'incoming_variation.flow_stress_variation_fraction',
            'incoming_variation.coil_synchronous', 'width_model.bite_heat_per_width_w_m',
            'width_model.gap_crown_m', 'width_model.entry_crown_m',
            'width_model.incoming_ridges', 'width_model.previous_strip_widths_m',
            'width_model.lateral_compressive_stress_pa',
            # (c) known fault state of the cooling system
            'width_model.blocked_nozzle_indices', 'width_model.nozzle_levels',
            'width_model.events', 'coolant.blocked_nozzle_indices']
    keys += [f'stand.{k}' for k in bd.STAND_KEYS] + [f'spans.{k}' for k in bd.SPAN_KEYS]
    keys += [f'lubrication.{k}' for k in bd.LUB_KEYS]
    keys += [f'coolant.{k}' for k in bd.COOLANT_KEYS if k != 'blocked_nozzle_indices']
    keys += [f'model_options.{k}' for k in bd.OPTION_KEYS + bd.OPTION_OPTIONAL
             if k != 'bite_response_override']
    keys += [f'width_model.roll.{k}' for k in t['width_model']['roll']]
    keys += [f'width_model.spray_header.{k}' for k in t['width_model']['spray_header']]
    keys += [f'width_model.shape_inputs.{k}' for k in bw.SHAPE_INPUT_KEYS]
    keys += [f'tribology.lubricant.{k}' for k in bproc.LUBRICANT_KEYS
             + ('conductivity_w_mk', 'name')]
    keys += [f'tribology.surface_finish.{k}' for k in t['tribology']['surface_finish']]
    keys += [f'tribology.friction_closure.{k}' for k in ('mu_b', 'mu_v', 'lambda0')]
    keys += [f'tribology.{k}' for k in bproc.TRIBOLOGY_KEYS + bproc.TRIBOLOGY_OPTIONAL
             if k not in ('lubricant', 'surface_finish', 'friction_closure')]
    keys += [f'hardening.{k}' for k in bproc.HARDENING_COMMON]
    keys += [f'hardening.{k}' for ks in bproc.HARDENING_LAW_KEYS.values() for k in ks]
    return keys


def numbers_in(obj, out=None):
    """Every number of a JSON structure (bools excluded)."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for v in obj.values():
            numbers_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            numbers_in(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(obj)
    return out


class QuestionTableTest(unittest.TestCase):
    def test_every_observation_key_has_a_question(self):
        t = json.loads((ROOT / 'scenarios' / 'band_diagnosis_template.json').read_text())
        obs = set(t['observation'])
        self.assertEqual(len(obs), 31)
        asked = {q.key.split('.', 1)[1] for q in bpl.QUESTIONS if q.key.startswith('observation.')}
        self.assertEqual(obs - asked, set())
        for q in bpl.QUESTIONS:
            if q.key.startswith('observation.'):
                self.assertIn(q.unknown, ('null', 'empty'), q.id)

    def test_every_section_53_key_has_a_question(self):
        missing = [k for k in section_53_keys() if k not in bpl.QUESTION_BY_KEY]
        self.assertEqual(missing, [])

    def test_choices_are_the_engine_lists(self):
        def values(qid):
            return tuple(v for v, _ in bpl.QUESTION_BY_ID[qid].choices)
        self.assertEqual(values('orientation'), bd.ORIENTATIONS)
        self.assertEqual(values('first_seen'), bd.FIRST_SEEN)
        self.assertEqual(values('continuity'), bw.CONTINUITY)
        self.assertEqual(values('appearance'), bw.APPEARANCES)
        self.assertEqual(values('bite_model'), bd.BITE_MODELS)
        self.assertEqual(values('thermal_sensitivity'), bthermal.MODES)
        self.assertEqual(values('roll_constraint'), rt.EXPANSION_CONSTRAINTS)
        self.assertEqual(values('hardening_law'), tuple(bproc.HARDENING_LAW_KEYS))
        # the two literal lists of the engine: probe its validator with each value
        case = bpl.as_v2(json.loads((ROOT / 'scenarios'
                                     / 'band_diagnosis_template.json').read_text()))
        for v in values('faces'):
            c = copy.deepcopy(case)
            c['observation']['faces'] = v
            bd.validate_case(c)
        c['observation']['faces'] = 'top'
        with self.assertRaises(ValueError):
            bd.validate_case(c)
        for v in bpl.ROLL_VALUES:
            c = copy.deepcopy(case)
            c['kinematics']['grinder_marks'] = [{'roll': v, 'marks_per_circumference': 3}]
            bd.validate_case(c)

    def test_ask_first_subset_is_short_and_kind_specific(self):
        lw = bpl.ask_first_ids('lengthwise', 0.21e-3)
        tr = bpl.ask_first_ids('transverse', 0.21e-3)
        foil = bpl.ask_first_ids('lengthwise', 18e-6)
        self.assertIn('band_positions', lw)
        self.assertNotIn('pitch_observations', lw)
        self.assertIn('pitch_observations', tr)
        self.assertNotIn('band_positions', tr)
        self.assertIn('worse_at_lower_tension', foil)
        self.assertNotIn('worse_at_lower_tension', lw)
        self.assertLessEqual(len(foil), 12)
        mill_first = [q for q in bpl.QUESTIONS if q.step == 'mill' and q.ask_first]
        self.assertLessEqual(len(mill_first), 10)

    def test_questions_are_json_and_plain(self):
        text = json.dumps(bpl.questions()).lower()
        for w in bpl.FORBIDDEN:
            self.assertNotIn(w, text)
        self.assertEqual({q['step'] for q in bpl.questions()}, {'see', 'rolling', 'mill'})


class UnitTest(unittest.TestCase):
    def test_exact_conversions(self):
        self.assertEqual(bpl.to_si(18, 'um'), 1.8e-05)
        self.assertEqual(bpl.to_si(600, 'm_min'), 10.0)
        self.assertEqual(bpl.to_si(270, 'mm_dia'), 0.135)
        self.assertEqual(bpl.to_si(45, 'degc'), 318.15)
        self.assertEqual(bpl.to_si(175, 'mpa'), 175e6)
        self.assertEqual(bpl.to_si(6000, 'kn_mm'), 6e9)        # 6 GN/m
        self.assertEqual(bpl.to_si(22, 'percent'), 0.22)
        self.assertEqual(bpl.to_si(12, 'nozzle_no'), 11)
        self.assertAlmostEqual(bpl.to_si(45, 'deg'), math.pi / 4, places=15)

    def test_round_trip_every_unit(self):
        for unit in bpl.UNITS:
            if unit == 'pos_mm':
                continue
            for v in (0.0, 1.0, 18.0, 123.456, 0.03, 815.0, 1e-3):
                if unit in bpl.INTEGER_UNITS:
                    v = int(v) + 1
                back = bpl.from_si(bpl.to_si(v, unit), unit)
                self.assertEqual(back, v, f'{unit} {v}')

    def test_positions_are_measured_from_the_strip_edge(self):
        p = preset('foil_mill')
        edge = bpl.strip_edge_m(p['case'])            # barrel 1.5 m, strip 1.2 m centred
        self.assertAlmostEqual(edge, 0.15, places=12)
        c = bpl.case_from_answers({'values': {'orientation': 'longitudinal',
                                              'band_positions': [100.0, 473.0]}}, p)
        got = c['observation']['band_positions_across_width_m']
        self.assertAlmostEqual(got[0], 0.25, places=12)
        self.assertAlmostEqual(got[1], 0.623, places=12)
        self.assertIn('strip edge', bpl.QUESTION_BY_ID['band_positions'].help)
        self.assertIn('first coolant nozzle', bpl.QUESTION_BY_ID['band_positions'].help)

    def test_help_texts_have_no_engine_talk(self):
        bad = re.compile(r'template|barrel coordinate|schema|\bv2\b|\bnull\b|case key|'
                         r'header start|[a-z]+_[a-z]+', re.IGNORECASE)
        for q in bpl.QUESTIONS:
            for text in (q.wording, q.help) + tuple(lab for _, lab in q.choices):
                self.assertIsNone(bad.search(text), f'{q.id}: {text}')


class AnswersCaseTest(unittest.TestCase):
    def test_dont_know_gives_null(self):
        p = preset('example_battery_foil')
        values = {q.id: None for q in bpl.QUESTIONS}
        c = bpl.case_from_answers({'values': values}, p)
        for k, v in c['observation'].items():
            self.assertIn(v, (None, []), k)
        self.assertIsNone(c['width_model']['nozzle_levels'])
        # mill, pass and material values stay at the starting point's
        self.assertEqual(c['pass'], p['case']['pass'])
        self.assertEqual(c['stand'], p['case']['stand'])
        self.assertTrue(all(o == 'preset' for o in bpl.value_origins(c).values()))

    def test_round_trip_case_answers_case(self):
        for p in all_presets():
            a = bpl.answers_from_case(p['case'])
            c = bpl.case_from_answers(a, p)
            for k in c:
                if k not in ('notes', 'provenance', 'name', 'synthetic'):
                    self.assertEqual(c[k], p['case'][k], f'{p["id"]}: {k}')
            a2 = bpl.answers_from_case(c)
            self.assertEqual(a2['values'], a['values'], p['id'])

    def test_round_trip_answers_case_answers(self):
        p = preset('foil_mill')
        values = {'orientation': 'longitudinal', 'band_positions': [300.0, 650.5],
                  'positions_repeat': True, 'continuity': 'both', 'appearance': 'loose_or_buckle',
                  'exit_gauge': 18.0, 'entry_gauge': 30.0, 'exit_speed': 600.0,
                  'strip_width': 1200.0, 'friction': 0.035, 'wr_diameter': 260.0,
                  'mill_modulus': 5500.0, 'strip_heat_share': 22.0, 'oil_inlet_temperature': 42.0,
                  'spray_angle': 40.0, 'intermittent_duration': 30.0, 'band_spacing': 12.0,
                  'nozzle_levels': [1.0] * 11 + [0.5] + [1.0] * 16,
                  'pitch_observations': None, 'route': [
                      {'label': 'F1', 'entry_thickness_m': 50.0, 'exit_thickness_m': 30.0,
                       'mean_flow_stress_pa': 170.0, 'friction_coefficient': 0.03,
                       'entry_tension_pa': 35.0, 'exit_tension_pa': 40.0,
                       'exit_speed_m_s': 780.0}],
                  'agc_gain': 0.8}
        origins = {'friction': 'measured', 'wr_diameter': 'measured', 'mill_modulus': 'estimated'}
        a = {'values': values, 'origins': origins, 'own_mill': True, 'name': 'my coil 4711'}
        c = bpl.case_from_answers(a, p)
        self.assertEqual(c['pass']['exit_thickness_m'], 1.8e-05)
        self.assertEqual(c['pass']['exit_speed_m_s'], 10.0)
        self.assertEqual(c['pass']['work_roll_radius_m'], 0.13)
        self.assertEqual(c['tribology']['strip_heat_fraction'], 0.22)
        self.assertEqual(c['width_model']['nozzle_levels'][11], 0.5)
        self.assertEqual(c['schedule'][0]['exit_speed_m_s'], 13.0)
        self.assertFalse(c['synthetic'])
        self.assertEqual(c['name'], 'my coil 4711')
        back = bpl.answers_from_case(c)
        for k, v in values.items():
            self.assertEqual(back['values'].get(k), v, k)
        self.assertEqual(back['origins']['friction'], 'measured')
        self.assertEqual(back['origins']['mill_modulus'], 'estimated')
        self.assertEqual(back['origins']['exit_gauge'], 'estimated')     # typed, no mark
        self.assertEqual(back['origins']['strip_width'], 'preset')       # typed = typical
        self.assertEqual(back['origins']['flow_stress'], 'preset')
        self.assertTrue(back['own_mill'])

    def test_synthetic_and_provenance_are_truthful(self):
        p = preset('example_lengthwise_bands')
        a = bpl.answers_from_case(p['case'])
        a['values']['friction'] = 0.04
        a['origins']['friction'] = 'measured'
        c = bpl.case_from_answers(a, p)
        self.assertTrue(c['synthetic'])
        self.assertIn('synthetic', c['provenance'])
        self.assertIn('1 measured', c['provenance'])
        self.assertIn('generated by the model', c['provenance'])
        self.assertEqual(bpl.value_origins(c)['pass.friction_coefficient'], 'measured')
        a['own_mill'] = True
        c2 = bpl.case_from_answers(a, p)
        self.assertFalse(c2['synthetic'])
        self.assertIn('own mill', c2['provenance'])
        # an origin 'preset' keeps the starting point's value whatever was typed
        a['origins']['friction'] = 'preset'
        c3 = bpl.case_from_answers(a, p)
        self.assertEqual(c3['pass']['friction_coefficient'],
                         p['case']['pass']['friction_coefficient'])

    def test_every_preset_builds_a_valid_case(self):
        ps = all_presets()
        self.assertEqual({p['id'] for p in ps},
                         {'foil_mill', 'sheet_mill'} | {e[0] for e in bpl.WORKED_EXAMPLES})
        for p in ps:
            c = bpl.case_from_answers({'values': {}}, p)
            bd.validate_case(c)
            self.assertEqual(c['case_schema'], bd.CASE_SCHEMA_V2)
            self.assertTrue(p['description'])
            if p['kind'] == 'example':
                self.assertTrue(p['generated_by_model'])
                self.assertIn('generated by the model', p['description'])
        self.assertEqual(len(bpl.presets()), 2)       # without the scenario files

    def test_created_sections_and_plain_errors(self):
        p = preset('foil_mill')
        c = bpl.case_from_answers({'values': {'incoming_hardness_variation': 2.0,
                                              'incoming_once_per_turn': True}}, p)
        self.assertEqual(c['incoming_variation'], {'flow_stress_variation_fraction': 0.02,
                                                   'coil_synchronous': True})
        with self.assertRaises(bpl.AnswerError) as cm:
            bpl.case_from_answers({'values': {'incoming_hardness_variation': 2.0}}, p)
        self.assertEqual(cm.exception.question, 'incoming_once_per_turn')
        with self.assertRaises(bpl.AnswerError) as cm:
            bpl.case_from_answers({'values': {'exit_gauge': 'thin'}}, p)
        self.assertEqual(bpl.plain_error(cm.exception)['question'], 'exit_gauge')
        with self.assertRaises(bpl.AnswerError) as cm:
            bpl.case_from_answers({'values': {'barrel_length': 1700.0}},
                                  preset('example_bearing_order'))
        self.assertIn('Start from the typical foil mill', str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            bpl.case_from_answers({'values': {'agc_gain': 5.0}}, p)
        err = bpl.plain_error(cm.exception)
        self.assertEqual(err['question'], 'agc_gain')
        self.assertIn('Gauge-control compensation gain', err['text'])
        with self.assertRaises(ValueError) as cm:
            bpl.case_from_answers({'values': {'exit_gauge': 60.0}}, p)   # entry is 50 um
        self.assertEqual(bpl.plain_error(cm.exception)['question'], 'exit_gauge')
        with self.assertRaises(ValueError):
            bpl.case_from_answers({'values': {'no_such_question': 1}}, p)

    def test_product_defaults_are_literature_values(self):
        d = bpl.product_defaults('household_foil', exit_thickness_m=10e-6,
                                 entry_thickness_m=20e-6)
        self.assertEqual(d['label'], 'typical values from the literature, to confirm')
        self.assertEqual(d['values']['exit_gauge'], 10.0)
        self.assertEqual(d['values']['product'], 'household_foil')
        self.assertEqual(d['mill_kind'], 'foil')
        c = bpl.case_from_answers({'values': d['values']}, preset('foil_mill'))
        self.assertEqual(c['material']['product'], 'household_foil')

    def test_light_starter_case_equals_the_survey_starter_case(self):
        from physicroll import band_survey as bs
        for pid, ov in (('battery_collector_foil', {'exit_thickness_m': 18e-6,
                                                    'entry_thickness_m': 30e-6}),
                        ('household_foil', {}), ('litho_sheet', {})):
            light, row = bs.product_starter_case(pid, **ov)
            result, mills = bs.survey_with_mills(
                [pid], overrides=bs.validate_overrides({pid: ov}) if ov else None)
            full = bs.starter_case(result['rows'][0], mills[result['rows'][0]['mill']])
            self.assertEqual(light, full, pid)
            self.assertEqual(row, result['rows'][0], pid)

    def test_quick_profile(self):
        c = bpl.case_from_answers({'values': {}}, preset('example_battery_foil'))
        q, changed = bpl.apply_profile(c, 'quick')
        self.assertEqual(q['model_options']['thermal_sensitivity'], 'off')
        self.assertEqual(q['width_model']['numerics'], bpl.QUICK_NUMERICS)
        self.assertEqual(q['model_options']['cells'], 128)
        self.assertEqual(len(changed), 3)
        bd.validate_case(q)
        d, changed = bpl.apply_profile(c, 'detailed')
        self.assertEqual(d, c)
        self.assertEqual(changed, [])
        self.assertEqual(c['model_options']['thermal_sensitivity'], 'full')    # untouched
        with self.assertRaises(ValueError):
            bpl.apply_profile(c, 'fast')


class SummaryTest(unittest.TestCase):
    def test_every_hypothesis_has_one_plain_entry(self):
        self.assertEqual(set(bpl.CAUSES), set(bd.HYPOTHESIS_IDS))
        for hid, (name, desc, picto) in bpl.CAUSES.items():
            self.assertTrue(name and desc.endswith('.') and picto, hid)
        self.assertEqual(len({c[2] for c in bpl.CAUSES.values()}), 20)

    def test_summaries_build_and_keep_engine_numbers(self):
        for name, r in all_results().items():
            with self.subTest(result=name):
                s = bpl.plain_summary(r)
                text = json.dumps(s, allow_nan=False).lower()
                for w in bpl.FORBIDDEN:
                    self.assertNotIn(w, text, f'{name}: "{w}"')
                self.assertEqual(s['status'], bd.STATUS)
                by_id = {h['id']: h for h in r['hypotheses']}
                self.assertEqual(len(s['causes']), 20)
                for c in s['causes']:
                    h = by_id[c['id']]
                    self.assertEqual(c['score'], h['score'])
                    self.assertEqual(c['standing'], h['standing'])
                    self.assertEqual(c['rank'], h['rank'])
                    self.assertEqual(c['how_to_check'], bpl.words(h['confirming_test']))
                    n_sup = sum(e['verdict'] == 'SUPPORTS' for e in h['evidence'])
                    self.assertEqual(len(c['fits_because']), n_sup)
                    for item in c['fits_because'] + c['speaks_against']:
                        self.assertIn(item['criterion'], bpl.CRITERIA)
                # every number of the views is a number of the result
                engine = set(numbers_in(r))
                sv = s['strip_view']
                if sv.get('geometry_basis'):        # v1 case: strip edges from the inputs
                    self.assertEqual(sv['strip_start_m'], bpl.strip_edge_m(r['inputs']))
                    engine |= {sv['strip_start_m'], sv['strip_end_m']}
                for view in ('strip_view', 'along_view', 'gauge_view', 'temperature_view'):
                    for x in numbers_in(s[view]):
                        if isinstance(x, int) and x < 100:      # indices, counts
                            continue
                        self.assertIn(x, engine, f'{name} {view}: {x}')
                for c in s['causes']:
                    self.assertIn(c['score'], engine)
                self.assertEqual(s['trust']['level'], 'LOW')     # preset (synthetic) mills
                self.assertTrue(s['trust']['rule'].startswith('Rule, not a statistic'))
                undescribed = [f['flag'] for f in s['flags_plain'] if not f['described']]
                self.assertEqual(undescribed, [], name)
                self.assertEqual(len(s['flags_plain']), len(r['flags']))

    def test_reader_facing_text_has_no_engine_tokens(self):
        snake = re.compile(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b')
        scream = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b')
        enums = {v for q in bpl.QUESTIONS for v, _ in q.choices if isinstance(v, str)}
        enums |= {'true', 'false'}
        keys = ('text', 'label', 'why', 'what', 'how_to_check', 'name', 'description',
                'prompts', 'direction_text', 'caveat')

        def walk(obj, path, out):
            if isinstance(obj, dict):
                if obj.get('described') is False:      # an unknown flag keeps its raw name
                    return
                for k, v in obj.items():
                    if k in keys or k.endswith('_words'):
                        for t in (v if isinstance(v, list) else [v]):
                            if isinstance(t, str):
                                out.append((f'{path}.{k}', t))
                    else:
                        walk(v, f'{path}.{k}', out)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, f'{path}[{i}]', out)
        for name, r in all_results().items():
            found = []
            walk(bpl.plain_summary(r), name, found)
            self.assertGreater(len(found), 200)
            for where, t in found:
                self.assertIsNone(snake.search(t), f'{where}: {t}')
                self.assertIsNone(scream.search(t), f'{where}: {t}')
                self.assertNotIn(t.strip(), enums, where)
                self.assertNotIn(t.strip().lower(), ('true', 'false'), where)

    def test_evidence_sentences_three_shapes(self):
        # 1. positions in metres -> millimetres, split into what was seen and what was computed
        e = {'criterion': 'band positions vs model stripes / blocked or low-level nozzles',
             'observed': 'observed 0.667 m on model 0.6675 m, 0.668 m (model steady stripes and '
                         'blocked / low-level nozzles)',
             'expected': 'within 0.013 m (one quarter of the nozzle pitch)',
             'verdict': 'SUPPORTS', 'weight': 'strong', 'basis': 'observation'}
        out = bpl.evidence_sentences(e, ['band_positions'])
        self.assertEqual(out['verdict_words'], 'Matches')
        self.assertEqual(out['seen_words'], 'You saw: Bands at 667 mm.')
        self.assertTrue(out['model_words'].startswith('The model computed: Positions at 668 mm'))
        self.assertIn('13 mm', out['expects_words'])
        self.assertNotRegex(json.dumps(out), r'\d m\b')
        # 2. the source is named by the basis
        for basis, start in (('model', 'The model computed: '),
                             ('input', 'From your mill values: ')):
            e2 = {'criterion': 'pass reduction', 'observed': '0.300', 'expected': '>= 0.40',
                  'verdict': 'CONTRADICTS', 'weight': 'moderate', 'basis': basis}
            o2 = bpl.evidence_sentences(e2)
            self.assertIsNone(o2['seen_words'])
            self.assertTrue(o2['model_words'].startswith(start), o2)
            self.assertEqual(o2['verdict_words'], 'Does not match')
        # 3. a compound item: what was seen and what the model computed, as two sentences,
        #    and the expectation as a sentence
        e3 = {'criterion': 'visible only after tension release vs steady model band',
              'observed': 'false; model MANIFEST_BUCKLE / MANIFEST_AFTER_TENSION_RELEASE',
              'expected': 'true: LATENT in mill and MANIFEST after release; false: MANIFEST in '
                          'mill', 'verdict': 'SUPPORTS', 'weight': 'moderate',
              'basis': 'observation'}
        o3 = bpl.evidence_sentences(e3, ['only_after_release'])
        self.assertEqual(o3['seen_words'], 'You saw: The bands are seen in the mill.')
        self.assertEqual(o3['model_words'], 'The model computed: Buckled in the mill and '
                                            'visible after tension release.')
        self.assertTrue(o3['expects_words'].startswith('If the bands show only after the coil '
                                                       'is unwound'))
        for o in (out, o3):
            for v in o.values():
                if v:
                    self.assertNotRegex(v, r'[A-Z]{2,}_[A-Z]|\b(true|false)\b|;\s*model')

    def test_views_follow_the_result(self):
        s = bpl.plain_summary(artifact('lengthwise-bands-demo'))
        r = artifact('lengthwise-bands-demo')
        sv = s['strip_view']
        ts = r['width']['thermal_steady']
        self.assertEqual(sv['strip_start_m'], ts['strip_start_m'])
        self.assertEqual(sv['thermal_profile']['local_deviation_m'], ts['local_deviation_m'])
        self.assertEqual([n['level'] for n in sv['nozzles']], ts['nozzle_levels'])
        self.assertEqual(sv['nozzles'][12]['state'], 'weak')
        self.assertEqual(sv['observed_positions_m'],
                         r['width']['positions']['observed_positions_m'])
        self.assertEqual(sv['tolerance_m'], r['width']['positions']['tolerance_m'])
        kinds = {p['kind'] for p in sv['predicted']}
        self.assertIn('steady_stripes', kinds)
        gv = s['gauge_view']
        self.assertEqual(len(gv['passes']), len(r['width']['gauge_trend']['rows']))
        th = [p['exit_thickness_m'] for p in gv['passes']]
        self.assertEqual(th, sorted(th, reverse=True))
        self.assertIn('thinner is worse', gv['direction_text'])
        tv = s['temperature_view']
        self.assertTrue(tv['available'])
        self.assertIn('not the coil temperature', tv['caveat'])
        av = bpl.plain_summary(artifact('thin-gauge-chatter-demo'))['along_view']
        sm = artifact('thin-gauge-chatter-demo')['strip_map']
        self.assertEqual(av['predicted_pitch_m'], sm['predicted_pitch_m'])
        self.assertEqual(av['hypothesis_id'], 'third_octave_self_excited_chatter')
        self.assertEqual(len(av['observed']), 2)

    def test_not_looked_at_and_next_checks_point_to_questions(self):
        s = bpl.plain_summary(artifact('lengthwise-bands-demo'))
        lead = s['causes'][0]
        self.assertEqual(lead['id'], 'nozzle_thermal_stripe')
        self.assertTrue(lead['not_looked_at'])
        for item in lead['not_looked_at']:
            for q in item['questions']:
                self.assertIn(q, bpl.QUESTION_BY_ID)
        faces = [x for x in lead['not_looked_at'] if x['criterion'] == 'faces']
        self.assertEqual(faces[0]['questions'], ['faces'])
        mapped = [c for c in s['next_checks'] if c['mapped']]
        self.assertTrue(mapped)
        self.assertEqual(len(s['next_checks']),
                         len(artifact('lengthwise-bands-demo')['recommended_next_measurements']))

    def test_headline_one_leader_tie_and_nothing_leads(self):
        s = bpl.plain_summary(artifact('battery-foil-demo'))
        self.assertEqual(s['headline']['kind'], 'one_leader')
        self.assertIn('Blocked or weak coolant nozzle', s['headline']['text'])
        self.assertIn('shortlist from a screening model, not a finding', s['headline']['text'])
        tie = bpl.plain_summary(dry_run_like(DRY_RUN_12UM_FLAGS, DRY_RUN_12UM_TOP))
        self.assertEqual(tie['headline']['kind'], 'tie')
        self.assertIn('tie for the lead', tie['headline']['text'])
        self.assertIn('Cooling-zone switching', tie['headline']['text'])
        self.assertIn('Tension troughs', tie['headline']['text'])
        r = artifact('battery-foil-demo')
        for h in r['hypotheses']:
            if h['standing'] == 'CONSISTENT_LEADING':
                h['standing'] = 'CONSISTENT'
        r['leading_hypotheses'] = []
        none = bpl.plain_summary(r)
        self.assertEqual(none['headline']['kind'], 'nothing_leads')
        self.assertIn('Nothing stands out yet', none['headline']['text'])
        self.assertIn('still unknown', none['headline']['text'])
        for x in (s, tie, none):
            t = x['headline']['text'].lower()
            for w in ('the cause is', 'confirmed', '%', 'probab', 'diagnos'):
                self.assertNotIn(w, t)

    def test_unknown_flag_falls_back_visibly(self):
        r = artifact('bearing-order-demo')
        r['flags'] = r['flags'] + ['SOME_NEW_ENGINE_FLAG']
        s = bpl.plain_summary(r)
        f = [x for x in s['flags_plain'] if x['flag'] == 'SOME_NEW_ENGINE_FLAG'][0]
        self.assertFalse(f['described'])
        self.assertIn('SOME_NEW_ENGINE_FLAG', f['text'])
        self.assertIn('no plain description yet', f['text'])

    def test_trust_rule(self):
        r = artifact('lengthwise-bands-demo')
        r['flags'] = [f for f in r['flags'] if f != 'SYNTHETIC_INPUTS']
        r['synthetic'] = r['inputs']['synthetic'] = False
        own = {q.key: 'measured' for q in bpl.QUESTIONS
               if q.origin_tracked and bpl._get(r['inputs'], q.key) is not None}
        ob = r['inputs']['observation']
        ob['changes_with_coolant_zone_switching'] = True      # all nine 'ask first' answered
        ob['disappears_after_backup_roll_change'] = False
        s = bpl.plain_summary(r, value_origins_=own, own_mill=True)
        self.assertEqual(s['trust']['level'], 'FAIR', s['trust']['reasons'])
        self.assertEqual(s['trust']['reasons'], [])
        # one key mill value left at the typical value: never above LOW
        key = 'pass.friction_coefficient'
        s2 = bpl.plain_summary(r, value_origins_=dict(own, **{key: 'preset'}), own_mill=True)
        self.assertEqual(s2['trust']['level'], 'LOW')
        self.assertTrue(any('typical value' in x['text'] for x in s2['trust']['reasons']))
        # not marked as the person's own mill values
        self.assertEqual(bpl.plain_summary(r, value_origins_=own, own_mill=False)
                         ['trust']['level'], 'LOW')
        # an experimental-model flag caps at MODERATE
        r['flags'].append('EXPERIMENTAL_MATTRESS_FOIL_MODEL')
        s3 = bpl.plain_summary(r, value_origins_=own, own_mill=True)
        self.assertEqual(s3['trust']['level'], 'MODERATE')
        r['flags'].append('STRIP_MAP_FAILED')
        self.assertEqual(bpl.plain_summary(r, value_origins_=own, own_mill=True)
                         ['trust']['level'], 'LOW')
        self.assertNotIn('HIGH', bpl.TRUST_LEVELS)

    def test_compare_summaries_words(self):
        old = bpl.plain_summary(artifact('battery-foil-demo'))
        r = artifact('battery-foil-demo')
        r['hypotheses'][0]['standing'] = 'CONSISTENT'
        r['hypotheses'][0]['score'] -= 6
        new = bpl.plain_summary(r)
        diff = bpl.compare_summaries(old, new)
        self.assertTrue(diff['changes'])
        self.assertIn('fits best -> fits', diff['text'])

    def test_product_survey_is_not_a_screening_result(self):
        survey = load_artifact('product-survey')
        with self.assertRaises(ValueError):
            bpl.plain_summary(survey)


if __name__ == '__main__':
    unittest.main()
