"""W1 envelope and one real checked-pass serialization example."""

import hashlib
import json
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # The core and standard-library tests do not require jsonschema.
    Draft202012Validator = None

from physicroll.checked_schedule import CheckedPass, run_checked_schedule
from physicroll.materials import MaterialState, PowerHardeningLaw
from physicroll.model import Scenario
from physicroll.operating import ObservedSignal, PassOperatingPlan, SignalRange
from physicroll.run_contract import CONVENTIONS, ResultBundle, RunSpec

ROOT = Path(__file__).resolve().parents[1]


def sample_spec():
    return {
        'schema_version': '1',
        'workflow_kind': 'checked_pass',
        'model_choices': {'solver': 'spatial_slab', 'material': 'power_hardening',
                          'bite': 'unassisted', 'thermal': 'none'},
        'unit_conventions': dict(CONVENTIONS),
        'identities': {'code_version': 'test-revision', 'model_version': 'v03',
                       'material_id': None, 'state_id': None, 'recipe_id': None},
        'source_hashes': {'solver': 'a' * 64}, 'card_hashes': {},
        'numerical_settings': {'cells': 128, 'verify_refinement': True},
        'requested_inputs': {'exit_thickness_m': .0015, 'estimated_force_n': None},
        'resolved_inputs': {'exit_thickness_m': .0015, 'history': ('initial', 'pass1')},
        'recipe_targets': {}, 'observations': {},
    }


def sample_result(spec):
    return {
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': {'exit_thickness_m': .0015},
        'outputs': {'torque_per_work_roll_nm': -12.5, 'exit_temperature_k': None},
        'checks': {'declared_bounds': {'required_limit_ids': [], 'evaluations': []}},
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': 'IN_DOMAIN', 'numerical_verification': 'PASSED',
            'declared_bounds_status': 'INDETERMINATE',
            'declared_bounds_coverage': 'NONE',
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED',
            'predictions_computed': True, 'qualification_evidence_refs': [],
        },
    }


class RunContractTests(unittest.TestCase):
    def test_run_round_trip_canonical_hash_and_snapshot(self):
        source = sample_spec()
        source['resolved_inputs']['scenario'] = Scenario.from_dict({
            'name': 'synthetic contract test', 'synthetic': True,
            'entry_thickness_m': .002, 'exit_thickness_m': .0015,
            'width_m': 1., 'entry_speed_m_s': 2., 'work_roll_radius_m': .25,
            'density_kg_m3': 2700., 'mean_flow_stress_pa': 120e6,
            'friction_coefficient': .08, 'entry_tension_pa': 10e6,
            'exit_tension_pa': 15e6, 'drive_efficiency': .9,
        })
        spec = RunSpec(source)
        source['requested_inputs']['exit_thickness_m'] = 99
        self.assertEqual(spec.to_dict()['requested_inputs']['exit_thickness_m'], .0015)
        self.assertEqual(spec.to_dict()['resolved_inputs']['history'], ['initial', 'pass1'])
        self.assertEqual(spec.to_dict()['resolved_inputs']['scenario']['exit_thickness_m'], .0015)
        self.assertIsNone(spec.to_dict()['requested_inputs']['estimated_force_n'])
        self.assertEqual(RunSpec.from_json(spec.to_json()).sha256, spec.sha256)
        self.assertEqual(spec.sha256, hashlib.sha256(spec.to_json().rstrip('\n').encode()).hexdigest())

    def test_runtime_metadata_does_not_change_scientific_digest(self):
        spec = RunSpec(sample_spec())
        payload = sample_result(spec)
        first = ResultBundle(payload, runtime_metadata={'timestamp': 'earlier'})
        second = ResultBundle(payload, runtime_metadata={'timestamp': 'later'})
        self.assertEqual(first.sha256, second.sha256)
        self.assertNotEqual(first.to_json(), second.to_json())
        reopened = ResultBundle.from_json(first.to_json())
        reopened.verify_run_spec(spec)
        self.assertEqual(reopened.to_dict()['runtime_metadata']['timestamp'], 'earlier')
        self.assertEqual(reopened.to_dict()['outputs']['torque_per_work_roll_nm'], -12.5)
        self.assertIsNone(reopened.to_dict()['outputs']['exit_temperature_k'])

    def test_versions_identities_conventions_and_unknown_fields_reject(self):
        for change in (
            lambda x: x.update(schema_version='2'),
            lambda x: x.update(workflow_kind='arbitrary'),
            lambda x: x.update(workflow_kind=[]),
            lambda x: x.update(workflow_kind={}),
            lambda x: x.update(workflow_kind=None),
            lambda x: x['identities'].update(material_id='AA5052'),
            lambda x: x['unit_conventions'].update(layer_count=True),
            lambda x: x['source_hashes'].update(solver='short'),
            lambda x: x.update(unexpected='value'),
        ):
            with self.subTest(change=change):
                data = sample_spec()
                change(data)
                with self.assertRaises(ValueError):
                    RunSpec(data)

    def test_nonfinite_unsupported_cycles_and_duplicate_keys_reject(self):
        for value in (float('nan'), float('inf'), -float('inf'), Path('file')):
            data = sample_spec()
            data['requested_inputs']['bad'] = value
            with self.assertRaises(ValueError):
                RunSpec(data)
        data = sample_spec()
        data['requested_inputs']['cycle'] = data['requested_inputs']
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            RunSpec(data)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            RunSpec.from_json('{"schema_version":"1","schema_version":"1"}')
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            RunSpec.from_json(RunSpec(sample_spec()).to_json().replace('0.0015', 'NaN'))
        data = sample_spec()
        data['requested_inputs']['bad'] = chr(0xD800)
        with self.assertRaisesRegex(ValueError, 'Unicode'):
            RunSpec(data)
        with self.assertRaisesRegex(ValueError, 'Unicode'):
            RunSpec.from_json(json.dumps(data, ensure_ascii=True))

    def test_status_axes_remain_independent_and_missing_bounds_not_within(self):
        spec = RunSpec(sample_spec())
        result = sample_result(spec)
        self.assertEqual(ResultBundle(result).to_dict()['assessments']['declared_bounds_status'],
                         'INDETERMINATE')
        for coverage in ('NONE', 'PARTIAL'):
            bad = sample_result(spec)
            bad['assessments']['declared_bounds_coverage'] = coverage
            bad['assessments']['declared_bounds_status'] = 'WITHIN'
            with self.assertRaisesRegex(ValueError, 'declared bounds'):
                ResultBundle(bad)
        bad = sample_result(spec)
        bad['checks'] = {}
        bad['assessments']['declared_bounds_coverage'] = 'COMPLETE'
        bad['assessments']['declared_bounds_status'] = 'WITHIN'
        with self.assertRaisesRegex(ValueError, 'evidence is required'):
            ResultBundle(bad)
        bad['checks'] = {'declared_bounds': {'required_limit_ids': [], 'evaluations': []}}
        with self.assertRaisesRegex(ValueError, 'coverage does not match'):
            ResultBundle(bad)
        complete = sample_result(spec)
        complete['checks']['declared_bounds'] = {
            'required_limit_ids': ['force_max', 'torque_max'],
            'evaluations': [{'limit_id': 'force_max', 'status': 'WITHIN'},
                            {'limit_id': 'torque_max', 'status': 'WITHIN'}]}
        complete['assessments']['declared_bounds_coverage'] = 'COMPLETE'
        complete['assessments']['declared_bounds_status'] = 'WITHIN'
        ResultBundle(complete)
        complete['checks']['declared_bounds']['evaluations'].pop()
        complete['assessments']['declared_bounds_coverage'] = 'PARTIAL'
        complete['assessments']['declared_bounds_status'] = 'INDETERMINATE'
        ResultBundle(complete)
        complete['checks']['declared_bounds']['evaluations'][0]['status'] = 'VIOLATED'
        complete['assessments']['declared_bounds_status'] = 'VIOLATED'
        ResultBundle(complete)
        result['assessments']['scientific_qualification'] = 'QUALIFIED'
        with self.assertRaisesRegex(ValueError, 'requires evidence'):
            ResultBundle(result)

    def test_result_rejects_tamper_and_contradictory_states(self):
        spec = RunSpec(sample_spec())
        other = RunSpec({**sample_spec(), 'workflow_kind': 'benchmark'})
        bundle = ResultBundle(sample_result(spec))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            bundle.verify_run_spec(other)
        data = sample_result(spec)
        data['assessments']['execution'] = 'FAILED'
        with self.assertRaisesRegex(ValueError, 'predictions require'):
            ResultBundle(data)
        data = sample_result(spec)
        data['assessments']['input_validity'] = 'INVALID'
        with self.assertRaisesRegex(ValueError, 'invalid inputs'):
            ResultBundle(data)
        data = sample_result(spec)
        data['assessments']['unexpected'] = 'FEASIBLE'
        with self.assertRaisesRegex(ValueError, 'unknown'):
            ResultBundle(data)
        data = sample_result(spec)
        data['schema_version'] = '2'
        with self.assertRaisesRegex(ValueError, 'unsupported ResultBundle'):
            ResultBundle(data)

    @unittest.skipIf(Draft202012Validator is None, 'optional JSON Schema validator unavailable')
    def test_json_schemas_match_key_runtime_status_rejections(self):
        run_schema = json.loads((ROOT/'schema/run-spec-v1.schema.json').read_text())
        result_schema = json.loads((ROOT/'schema/result-bundle-v1.schema.json').read_text())
        Draft202012Validator.check_schema(run_schema)
        Draft202012Validator.check_schema(result_schema)
        spec = RunSpec(sample_spec())
        Draft202012Validator(run_schema).validate(spec.to_dict())
        valid = ResultBundle(sample_result(spec)).to_dict()
        Draft202012Validator(result_schema).validate(valid)
        for mutation in ('missing_evidence', 'within_without_coverage',
                         'within_with_violation', 'none_with_evaluation',
                         'partial_without_evaluation', 'violated_without_violation'):
            data = sample_result(spec)
            if mutation == 'missing_evidence':
                data['assessments']['declared_bounds_status'] = 'WITHIN'
                data['assessments']['declared_bounds_coverage'] = 'COMPLETE'
            elif mutation == 'within_without_coverage':
                data['assessments']['declared_bounds_status'] = 'WITHIN'
            elif mutation == 'within_with_violation':
                data['checks']['declared_bounds'] = {
                    'required_limit_ids': ['force'],
                    'evaluations': [{'limit_id': 'force', 'status': 'VIOLATED'}]}
                data['assessments']['declared_bounds_status'] = 'WITHIN'
                data['assessments']['declared_bounds_coverage'] = 'COMPLETE'
            elif mutation == 'none_with_evaluation':
                data['checks']['declared_bounds'] = {
                    'required_limit_ids': ['force'],
                    'evaluations': [{'limit_id': 'force', 'status': 'WITHIN'}]}
            elif mutation == 'partial_without_evaluation':
                data['assessments']['declared_bounds_coverage'] = 'PARTIAL'
            else:
                data['checks']['declared_bounds'] = {
                    'required_limit_ids': ['force'],
                    'evaluations': [{'limit_id': 'force', 'status': 'WITHIN'}]}
                data['assessments']['declared_bounds_status'] = 'VIOLATED'
                data['assessments']['declared_bounds_coverage'] = 'COMPLETE'
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    ResultBundle(data)
                self.assertFalse(Draft202012Validator(result_schema).is_valid(data))

    def test_dataclass_and_checked_example_preserve_input_vs_prediction(self):
        spec = RunSpec.from_json((ROOT/'scenarios/v1_checked_pass.runspec.json').read_text())
        inputs = spec.to_dict()['resolved_inputs']
        pass_data = inputs['checked_pass']
        scenario = Scenario.from_dict(pass_data['scenario'])
        state = MaterialState(**{**inputs['initial_state'],
                                 'history': tuple(inputs['initial_state']['history'])})
        law = PowerHardeningLaw(**inputs['law'])
        plan_data = pass_data['operating_plan']
        plan = PassOperatingPlan(**{**plan_data,
                                    'ranges': tuple(SignalRange(**item) for item in plan_data['ranges']),
                                    'observations': tuple(ObservedSignal(**item)
                                                          for item in plan_data['observations'])})
        self.assertEqual(plan.pass_name, scenario.name)
        for key in ('elasticity', 'heat_boundary', 'passive_contact',
                    'fluid_observation', 'roll_body_id'):
            self.assertIsNone(pass_data[key], f'example optional {key} changed')
        checked = CheckedPass(scenario, plan, pass_data['solver'], pass_data['cells'],
                              pass_data['bite_mode'], tuple(pass_data['assumed_strain_range']),
                              tuple(pass_data['assumed_temperature_range_k']),
                              pass_data['elasticity'], pass_data['heat_boundary'],
                              pass_data['passive_contact'], pass_data['fluid_observation'],
                              pass_data['roll_body_id'])
        self.assertEqual(spec.to_dict()['requested_inputs']['scenario'], pass_data['scenario'])
        self.assertEqual(inputs['interpass_handoffs'], [])
        result = run_checked_schedule((checked,), state, law,
                                      gauge_basis=inputs['gauge_basis'],
                                      layer_count=inputs['layer_count'])
        for name, digest in {**spec.to_dict()['source_hashes'],
                             **spec.to_dict()['card_hashes']}.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest)
        bundle_data = sample_result(spec)
        bundle_data['effective_inputs'] = {'scenario': result['passes'][0]['effective_scenario']}
        bundle_data['outputs'] = {'checked_schedule': result}
        self.assertTrue(result['passes'][0]['mechanics']['numerical_converged'])
        self.assertEqual(result['declared_bounds_status'], 'INDETERMINATE')
        self.assertEqual(result['passes'][0]['operating']['equipment_checks'], [])
        bundle_data['checks'] = {
            'declared_bounds': {'required_limit_ids': [], 'evaluations': []},
            'gauge_audit': result['gauge_audit'],
            'declared_bound_violations': result['declared_bound_violations']}
        bundle_data['assessments']['declared_bounds_status'] = result['declared_bounds_status']
        bundle = ResultBundle(bundle_data)
        reopened = ResultBundle.from_json(bundle.to_json())
        reopened.verify_run_spec(RunSpec.from_json(spec.to_json()))
        item = reopened.to_dict()['outputs']['checked_schedule']['passes'][0]
        self.assertEqual(item['requested_scenario']['exit_thickness_m'],
                         item['effective_scenario']['exit_thickness_m'])
        self.assertNotEqual(item['requested_scenario']['mean_flow_stress_pa'],
                            item['effective_scenario']['mean_flow_stress_pa'])
        self.assertEqual(reopened.to_dict()['assessments']['declared_bounds_coverage'], 'NONE')
        self.assertIsNone(item['thermal'])


if __name__ == '__main__':
    unittest.main()
