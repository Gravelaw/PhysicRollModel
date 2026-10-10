"""Build, install, and run the offline package check outside the source tree."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import venv


ROOT = Path(__file__).resolve().parents[1]


def main():
    with TemporaryDirectory(prefix='physicroll-wheel-') as temporary:
        target = Path(temporary)
        source = target / 'source'
        source.mkdir()
        for name in ('pyproject.toml', 'LICENSE'):
            shutil.copyfile(ROOT / name, source / name)
        shutil.copytree(ROOT / 'physicroll', source / 'physicroll',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        wheelhouse = target / 'wheels'
        wheelhouse.mkdir()
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps',
                        '--wheel-dir', str(wheelhouse), str(source)],
                       cwd=target, check=True)
        wheels = list(wheelhouse.glob('physicroll-*.whl'))
        if len(wheels) != 1:
            raise RuntimeError('expected exactly one PhysicRollModel wheel')
        environment = target / 'venv'
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        clean_env = os.environ.copy()
        clean_env.pop('PYTHONPATH', None)
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-index', '--no-deps',
                        str(wheels[0])], cwd=target, env=clean_env, check=True)
        outside = target / 'outside-checkout'
        outside.mkdir()
        subprocess.run([str(python), '-I', '-m', 'physicroll.package_check'],
                       cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.editor import _template, guided_values, build_guided_checked; "
            "from physicroll.workflows import run_workflow; "
            "base=_template('checked_pass'); "
            "saved=build_guided_checked(base, guided_values(base)); "
            "assert run_workflow(saved).to_dict()['assessments']['execution']=='COMPLETED'",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t1 import T1Episode, T1Trajectory; "
            "case=T1Episode(times_s=(0.,1.),prescribed_strip_speed_m_s=(.1,.1),"
            "free_span_length_m=1.,thickness_m=.001,width_m=1.,density_kg_m3=1000.,"
            "left_core_radius_m=.1,right_core_radius_m=.1,left_initial_length_m=2.,"
            "right_initial_length_m=1.); "
            "result=T1Trajectory(case).result(); "
            "assert result['status']=='COMPLETED' and result['strip_speed_role']=='prescribed_input'",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a1 import T2A1Case, run_torque_driven; "
            "case=T2A1Case(duration_s=2.,step_s=.01,left_radius_m=.1,"
            "right_radius_m=.1,left_inertia_kg_m2=1.,right_inertia_kg_m2=1.,"
            "span_stiffness_n_m=100.,initial_extension_m=.01); "
            "result=run_torque_driven(case); "
            "assert result['episode_outcome']=='TERMINATED_TENSION_LOSS' "
            "and result['shaft_speed_role']=='predicted_from_applied_torque'",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a2 import T2A2Case, run_coupled_bar; "
            "result=run_coupled_bar(T2A2Case(16,.003125)); "
            "assert result['episode_outcome']=='COMPLETED_REQUESTED_DURATION' "
            "and result['bar_material_role']=='fixed_material_no_flux' "
            "and result['maximum_energy_defect_j']<1e-18",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a3 import T2A3Case, run_prescribed_reel_flux; "
            "result=run_prescribed_reel_flux(T2A3Case()); "
            "assert result['mode']=='constant_prescribed_transport_reaction' "
            "and result['maximum_reel_angular_impulse_defect_nm_s']['left']<1e-10 "
            "and result['maximum_reel_energy_defect_j']['right']<1e-10",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a4 import T2A4Case, run_torque_driven_reels; "
            "result=run_torque_driven_reels(T2A4Case(.04)); "
            "assert result['mode']=='torque_driven_inextensible_moving_web' "
            "and result['shaft_speed_role']=='predicted_from_applied_torque' "
            "and abs(result['completed_transfer_m']-.2)<1e-12",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a5 import T2A5Case, run_moving_elastic_span; "
            "result=run_moving_elastic_span(T2A5Case(64)); "
            "assert result['mode']=='distributed_moving_elastic_span_with_characteristic_inputs' "
            "and result['maximum_mass_balance_defect_kg']<1e-10 "
            "and result['maximum_reconstructed_stage_courant']<=result['cfl_limit']",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a6 import T2A6Case, run_append_only_reaction_reel; "
            "result=run_append_only_reaction_reel(T2A6Case(.0005)); "
            "assert result['mode']=='append_only_elastic_port_reaction_reel' "
            "and result['shaft_torque_role']=='reaction_not_applied_input' "
            "and result['maximum_storage_vs_flux_defect_j']<1e-11",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a7 import T2A7Case, run_torque_driven_elastic_coupling; "
            "result=run_torque_driven_elastic_coupling(T2A7Case(64)); "
            "assert result['mode']=='torque_driven_append_only_elastic_span_reel_coupling' "
            "and result['right_incoming_characteristic_role']=='predicted_from_reel_speed' "
            "and result['maximum_combined_inventory_defect_kg']<1e-12",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a8 import T2A8Case, run_reaction_release_first_tension_zero; "
            "result=run_reaction_release_first_tension_zero(T2A8Case(64)); "
            "assert result['episode_outcome']=='STOPPED_AT_FIRST_TENSION_ZERO' "
            "and result['event']['feasible_minimum_tension_n']<1e-9 "
            "and result['maximum_combined_inventory_defect_kg']<1e-11",
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from physicroll.transient_t2a9 import T2A9Case, run_matched_reaction_reversal; "
            "result=run_matched_reaction_reversal(T2A9Case(64)); "
            "assert result['episode_outcome']=='RETURNED_TO_OLD_LAYER_WITHOUT_CONSUMING_IT' "
            "and len(result['events'])==2 "
            "and result['maximum_new_strain_ownership_defect_j']<1e-14",
        ], cwd=outside, env=clean_env, check=True)
        for name in ('v1_checked_pass.runspec.json',
                     'v1_operating_replay.runspec.json',
                     'v1_schedule_search.runspec.json',
                     'v1_prescribed_transport_t1.runspec.json',
                     'v1_shao_benchmark.runspec.json',
                     'v1_shao_sensitivity.runspec.json'):
            spec = outside / name
            result = outside / f'{name}.result.json'
            subprocess.run([
                str(python), '-I', '-c',
                "from pathlib import Path; import sys; "
                "from physicroll.resources import resource_file; "
                "Path(sys.argv[1]).write_bytes(resource_file('examples', "
                "sys.argv[2]).read_bytes())",
                str(spec), name,
            ], cwd=outside, env=clean_env, check=True)
            subprocess.run([str(python), '-I', '-m', 'physicroll', '--run-spec',
                            str(spec), '--output', str(result)],
                           cwd=outside, env=clean_env, check=True)
            subprocess.run([
                str(python), '-I', '-c',
                "from pathlib import Path; import sys; "
                "from physicroll.run_contract import RunSpec, ResultBundle; "
                "from physicroll.workflows import run_workflow; "
                "spec=RunSpec.from_json(Path(sys.argv[1]).read_bytes()); "
                "cli=ResultBundle.from_json(Path(sys.argv[2]).read_bytes()); "
                "cli.verify_run_spec(spec); "
                "assert cli.sha256 == run_workflow(spec).sha256",
                str(spec), str(result),
            ], cwd=outside, env=clean_env, check=True)
            if name in ('v1_checked_pass.runspec.json',
                        'v1_schedule_search.runspec.json',
                        'v1_prescribed_transport_t1.runspec.json'):
                bundle = outside / f'{name}.run'
                subprocess.run([str(python), '-I', '-m', 'physicroll.bundle_cli',
                                'create', '--run-spec', str(spec), '--out', str(bundle)],
                               cwd=outside, env=clean_env, check=True)
                for action in ('verify', 'replay'):
                    subprocess.run([str(python), '-I', '-m', 'physicroll.bundle_cli',
                                    action, str(bundle)],
                                   cwd=outside, env=clean_env, check=True)
                if name == 'v1_prescribed_transport_t1.runspec.json':
                    subprocess.run([
                        str(python), '-I', '-c',
                        "from pathlib import Path; import sys; "
                        "from physicroll.run_contract import RunSpec; "
                        "from physicroll.transient_workflow import episode_from_spec; "
                        "from physicroll.transient_t1 import T1Trajectory, continue_t1, "
                        "save_t1_checkpoint, load_t1_checkpoint; "
                        "spec=RunSpec.from_json(Path(sys.argv[1]).read_bytes()); "
                        "case=episode_from_spec(spec); direct=T1Trajectory(case); "
                        "cursor=direct.stop_time_s/2; "
                        "save_t1_checkpoint(sys.argv[2], direct.checkpoint_at(cursor,spec.sha256)); "
                        "suffix=continue_t1(case,load_t1_checkpoint(sys.argv[2]),spec.sha256).result(); "
                        "assert suffix['final_state']==direct.state_at(direct.stop_time_s); "
                        "assert suffix['remaining_events']==list(direct.events)["
                        "load_t1_checkpoint(sys.argv[2])['next_event_index']:]",
                        str(spec), str(outside / 't1-checkpoint.json'),
                    ], cwd=outside, env=clean_env, check=True)


if __name__ == '__main__':
    main()
