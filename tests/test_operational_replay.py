"""O0 contract verification: source-informed semantics, no plant validation."""
from dataclasses import asdict, replace
import json
import unittest

from physicroll.operating import ObservedSignal, SignalRange
from physicroll.operational_replay import (
    AppliedReference, MeasuredSignal, OperationSample, OperatingRecipe, PassScope,
    PhaseTarget, SteadyWindowEvidence, assess_sample_models, assess_setup_recipe,
    replay_operating_samples)


class OperationalReplayTests(unittest.TestCase):
    def setUp(self):
        self.scope = PassScope('pass-1','Al-synthetic','unknown',.002,.0015)
        self.recipe = OperatingRecipe('recipe-A','r1',self.scope,(
            PhaseTarget('entry_speed_m_s','m/s',2.,'steady','synthetic recipe'),
            PhaseTarget('exit_thickness_m','m',.0015,'steady','synthetic recipe'),
            PhaseTarget('entry_tension_pa','Pa',1e7,'steady','synthetic recipe'),
            PhaseTarget('exit_tension_pa','Pa',1.5e7,'steady','synthetic recipe'),
            PhaseTarget('entry_speed_m_s','m/s',1.,'ramp_up','synthetic recipe'),
            PhaseTarget('entry_speed_m_s','m/s',.5,'deceleration','synthetic recipe')),
            'SYNTHETIC contract example; no actual mill recipe')
        actuals = tuple(MeasuredSignal(q,u,v,10.,'valid',location,12.,unc,'synthetic observation')
                        for q,u,v,location,unc in (
            ('entry_thickness_m','m',.002,'entry',1e-6),
            ('exit_thickness_m','m',.00151,'exit',1e-6),
            ('entry_speed_m_s','m/s',1.8,'entry',.01),
            ('entry_tension_pa','Pa',0.,'entry',100.),
            ('exit_tension_pa','Pa',1.4e7,'exit',100.)))
        self.window = SteadyWindowEvidence('spatial_slab',8.,10.,.1,
            'synthetic review of force/torque/power/slip stationarity and error budget',
            'synthetic parcel/location/timebase alignment assessment')
        self.sample = OperationSample('coil-1',self.scope,'recipe-A','r1','synthetic_clock',10.,
            'steady','observed','synthetic event annotation','entry-material-reference',
            'established','synthetic established bite and both span boundary records',
            actuals,(AppliedReference('entry_speed_m_s','m/s',1.9,9.,9.1,'synthetic trim'),),
            (self.window,))

    def replay(self, samples=None, recipes=None):
        return replay_operating_samples(recipes or (self.recipe,),samples or (self.sample,))

    def test_targets_applied_and_actual_remain_distinct_and_deterministic(self):
        before = asdict(self.sample)
        result = self.replay()
        row = result['samples'][0]
        target = next(t for t in row['recipe_targets'] if t['quantity']=='entry_speed_m_s')
        actual = next(t for t in row['sample']['measurements'] if t['quantity']=='entry_speed_m_s')
        self.assertEqual((target['value'],row['sample']['applied_references'][0]['value'],actual['value']),
                         (2.,1.9,1.8))
        self.assertEqual(row['model_readiness']['spatial_slab']['status'],'READY_FOR_SEPARATE_DOMAIN_CHECKS')
        self.assertEqual(row['model_readiness']['spatial_slab']['prediction_validity'],'NOT_EVALUATED')
        self.assertFalse(result['state_advanced']);self.assertFalse(result['predictions_computed'])
        self.assertEqual(before,asdict(self.sample))
        self.assertEqual(json.dumps(result,sort_keys=True,allow_nan=False),
                         json.dumps(self.replay(),sort_keys=True,allow_nan=False))

    def test_phase_or_speed_alone_never_enables_and_setup_is_separate(self):
        for phase in ('prepared','threading','ramp_up','deceleration','tailout','reversal','interrupted','complete','unknown'):
            s = replace(self.sample,phase=phase,phase_basis='unknown' if phase=='unknown' else 'observed')
            model = assess_sample_models(s)['spatial_slab']
            self.assertEqual(model['status'],'NOT_APPLICABLE')
            self.assertFalse(model['evaluation_allowed'])
        self.assertFalse(assess_sample_models(replace(self.sample,steady_evidence=()))['spatial_slab']['evaluation_allowed'])
        self.assertEqual(assess_setup_recipe(self.recipe)['status'],'READY_FOR_HYPOTHETICAL_DOMAIN_CHECKS')
        self.assertEqual(assess_setup_recipe(self.recipe,target_phase='ramp_up')['status'],'WAITING_FOR_INPUTS')

    def test_missing_stale_suspect_or_unaligned_actual_never_backfilled(self):
        target = self.sample.measurements[2]
        for replacement in (None,replace(target,quality='suspect'),
                            replace(target,quality='unavailable',value=None,observed_at_s=None),
                            replace(target,observed_at_s=9.),replace(target,material_coordinate_m=None),
                            replace(target,uncertainty_si=None)):
            values = tuple(x for x in self.sample.measurements if x.quantity != target.quantity)
            if replacement is not None: values += (replacement,)
            s = replace(self.sample,measurements=values)
            self.assertEqual(assess_sample_models(s)['spatial_slab']['status'],'WAITING_FOR_DATA')
        # Zero is an actual known boundary, not missing tension.
        self.assertTrue(assess_sample_models(self.sample)['spatial_slab']['evaluation_allowed'])
        for state,status in (('unknown','WAITING_FOR_DATA'),('absent','NOT_APPLICABLE')):
            self.assertEqual(assess_sample_models(replace(self.sample,boundary_state=state))['spatial_slab']['status'],status)

    def test_qualification_does_not_transfer_to_other_models(self):
        report = assess_sample_models(self.sample)
        for model,record in report.items():
            self.assertEqual(record['evaluation_allowed'],model=='spatial_slab',model)
        self.assertEqual(report['passive_energy']['status'],'SEPARATE_INPUT_CONTRACT_REQUIRED')
        self.assertEqual(report['parameter_adaptation']['status'],'NOT_IMPLEMENTED')

    def test_short_coil_ramp_deceleration_and_length_evidence(self):
        a = replace(self.sample,phase='ramp_up',steady_evidence=())
        b = replace(a,timestamp_s=11.,phase='deceleration',transition_provenance='recorded length-trigger event',
                    remaining_length_m=20.,remaining_length_uncertainty_m=2.,
                    remaining_length_provenance='synthetic estimator-v1; no project estimator')
        rows = self.replay((a,b))['samples']
        self.assertEqual([r['sample']['phase'] for r in rows],['ramp_up','deceleration'])
        self.assertTrue(all(not r['model_readiness']['spatial_slab']['evaluation_allowed'] for r in rows))
        self.assertEqual(rows[1]['sample']['remaining_length_m'],20.)
        with self.assertRaisesRegex(ValueError,'transition'):self.replay((a,replace(b,transition_provenance=None)))
        with self.assertRaisesRegex(ValueError,'remaining length'):
            self.replay((replace(b,remaining_length_uncertainty_m=None),))

    def test_context_recipe_revision_and_reentry(self):
        for scope in (replace(self.scope,pass_name='pass-2'),replace(self.scope,alloy='another'),
                      replace(self.scope,temper='another'),replace(self.scope,exit_thickness_m=.0014)):
            with self.assertRaisesRegex(ValueError,'applicability'):
                self.replay((replace(self.sample,scope=scope),))
        with self.assertRaisesRegex(ValueError,'applicability'):
            self.replay((replace(self.sample,recipe_revision='missing'),))
        newer = replace(self.recipe,revision='r2',targets=tuple(
            replace(t,value=3.) if t.quantity=='entry_speed_m_s' and t.phase=='steady' else t for t in self.recipe.targets))
        second = replace(self.sample,timestamp_s=11.,recipe_revision='r2',steady_evidence=())
        report = self.replay((self.sample,second),(self.recipe,newer))
        self.assertEqual(report['samples'][1]['model_readiness']['spatial_slab']['status'],'WAITING_FOR_DATA')
        with self.assertRaisesRegex(ValueError,'recipe-change'):
            self.replay((self.sample,replace(second,steady_evidence=(replace(self.window,end_s=11.),))),
                        (self.recipe,newer))
        interrupted = replace(self.sample,phase='interrupted',steady_evidence=())
        later = replace(self.sample,timestamp_s=12.,transition_provenance='re-established boundaries')
        with self.assertRaisesRegex(ValueError,'nonsteady'):
            self.replay((interrupted,later))
        fresh = replace(later,measurements=tuple(replace(x,observed_at_s=12.) for x in later.measurements),
                        steady_evidence=(replace(self.window,start_s=10.5,end_s=12.),))
        self.assertTrue(self.replay((interrupted,fresh))['samples'][1]['model_readiness']['spatial_slab']['evaluation_allowed'])

    def test_boundary_loss_and_data_gap_require_fresh_window(self):
        speed = self.sample.measurements[2]
        gaps = [replace(self.sample,boundary_state=state) for state in ('absent','unknown')]
        for bad in (None,replace(speed,quality='suspect'),
                    replace(speed,quality='unavailable',value=None,observed_at_s=None),
                    replace(speed,value=0.),replace(speed,material_coordinate_m=None),
                    replace(speed,uncertainty_si=None)):
            actuals = tuple(x for x in self.sample.measurements if x.quantity != speed.quantity)
            if bad is not None: actuals += (bad,)
            gaps.append(replace(self.sample,measurements=actuals))
        restored = replace(self.sample,timestamp_s=11.,
                           measurements=tuple(replace(x,observed_at_s=11.) for x in self.sample.measurements),
                           steady_evidence=(replace(self.window,end_s=11.),))
        for gap in gaps:
            with self.subTest(gap=gap):
                # Preserve the unavailable record even if it carries stale evidence.
                self.assertFalse(self.replay((gap,))['samples'][0]['model_readiness']['spatial_slab']['evaluation_allowed'])
                with self.assertRaisesRegex(ValueError,'evidence cannot cross'):
                    self.replay((gap,restored))
                with self.assertRaisesRegex(ValueError,'evidence cannot cross'):
                    self.replay((gap,replace(restored,steady_evidence=(replace(self.window,start_s=10.,end_s=11.),))))
                fresh = replace(restored,steady_evidence=(replace(self.window,start_s=10.5,end_s=11.),))
                rows = self.replay((gap,fresh))['samples']
                self.assertTrue(rows[-1]['model_readiness']['spatial_slab']['evaluation_allowed'])
                self.assertEqual(rows[0]['sample'],asdict(gap))
        # Established zero tension is not a data gap and must not break a window.
        self.assertTrue(self.replay((self.sample,restored))['samples'][-1]['model_readiness']['spatial_slab']['evaluation_allowed'])

    def test_complete_phase_trace_and_different_pass_recipe(self):
        phases = ('prepared','threading','ramp_up','steady','deceleration','tailout','complete')
        samples = []
        for i,phase in enumerate(phases):
            t = 10.+i
            actuals = tuple(replace(x,observed_at_s=t) for x in self.sample.measurements)
            evidence = (replace(self.window,start_s=t-.5,end_s=t),) if phase=='steady' else ()
            samples.append(replace(self.sample,timestamp_s=t,phase=phase,measurements=actuals,
                                   boundary_state='absent' if phase in ('prepared','threading','tailout','complete') else 'established',
                                   steady_evidence=evidence,transition_provenance='synthetic independently labelled event'))
        rows = self.replay(tuple(samples))['samples']
        self.assertEqual([r['model_readiness']['spatial_slab']['evaluation_allowed'] for r in rows],
                         [False,False,False,True,False,False,False])
        self.assertEqual(rows[0]['recipe_targets'],[])  # Never inherit steady targets.
        scope = PassScope('pass-2','different synthetic alloy','different temper',.0015,.001)
        recipe = replace(self.recipe,recipe_id='other',scope=scope,targets=tuple(
            replace(t,value=.001) if t.quantity=='exit_thickness_m' else t for t in self.recipe.targets))
        sample = replace(self.sample,scope=scope,recipe_id='other')
        self.assertEqual(self.replay((sample,),(recipe,))['recipes'][0]['scope'],asdict(scope))
        # A recipe change does not manufacture new actual values or material state.
        self.assertEqual(self.replay((sample,),(recipe,))['samples'][0]['sample']['measurements'],
                         asdict(self.sample)['measurements'])

    def test_invalid_contracts_and_future_information(self):
        for change in (dict(timestamp_s=float('nan')),dict(phase_basis='commanded'),
                       dict(measurements=list(self.sample.measurements)),dict(boundary_state=True),
                       dict(steady_evidence=(replace(self.window,start_s=10.),)),
                       dict(applied_references=(replace(self.sample.applied_references[0],acknowledged_at_s=11.),))):
            with self.subTest(change=change),self.assertRaises(ValueError):self.replay((replace(self.sample,**change),))
        for value in (-1.,True,float('inf')):
            bad = replace(self.sample.measurements[2],value=value)
            with self.assertRaises(ValueError):bad.validate()
        with self.assertRaisesRegex(ValueError,'future'):
            self.replay((replace(self.sample,measurements=(replace(self.sample.measurements[0],observed_at_s=11.),)),))
        with self.assertRaisesRegex(ValueError,'increase'):self.replay((self.sample,self.sample))
        with self.assertRaisesRegex(ValueError,'duplicate recipe'):
            self.replay(recipes=(self.recipe,self.recipe))
        with self.assertRaisesRegex(ValueError,'timebase'):
            self.replay((self.sample,replace(self.sample,timebase_id='other',timestamp_s=11.)))

    def test_new_phase_tags_preserve_old_range_and_observation_contracts(self):
        for phase in ('prepared','ramp_up','reversal','interrupted','complete','unknown'):
            SignalRange('entry_speed_m_s','m/s',0.,2.,phase,'synthetic').validate()
            ObservedSignal('entry_speed_m_s','m/s',1.,phase,'synthetic').validate()


if __name__ == '__main__':
    unittest.main()
