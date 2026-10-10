"""Named examples and audited fixtures carried by the wheel.

The allowlist is intentional: callers cannot turn a resource name into an
arbitrary filesystem path. Traversables also work when resources are zipped.
"""

import json
from importlib.resources import files


RESOURCE_NAMES = {
    'examples': frozenset({
        'baseline.json', 'baseline.equipment.json', 'flowing_energy_demo.json',
        'higher_reduction.json', 'higher_speed.json', 'passive_contact_demo.json',
        'unloaded_transport.json', 'v03_foundations.json',
        'v1_checked_pass.runspec.json',
        'v1_operating_replay.runspec.json',
        'v1_schedule_search.runspec.json',
        'v1_prescribed_transport_t1.runspec.json',
        'v1_torque_driven_span_reel_t2.runspec.json',
        'v1_shao_benchmark.runspec.json', 'v1_shao_sensitivity.runspec.json',
    }),
    'schemas': frozenset({
        'scenario.schema.json', 'run-spec-v1.schema.json',
        'result-bundle-v1.schema.json',
    }),
    'shao_fixture': frozenset({
        'assumptions.json', 'inputs.csv', 'measured_validation.csv',
        'reference_model_outputs.csv', 'sources.json',
    }),
    'shao_research': frozenset({
        'shao2015_raw.json', 'shao2015_conditional_adapter.json',
        'shao2015_prior_sensitivity.json',
    }),
}


def resource_file(category, name):
    """Return a package Traversable for reading a declared resource."""
    if category not in RESOURCE_NAMES or name not in RESOURCE_NAMES[category]:
        raise ValueError('unknown packaged resource')
    return files('physicroll').joinpath('_resources').joinpath(category).joinpath(name)


def resource_directory(category):
    """Return a package Traversable for a declared resource collection."""
    if category not in RESOURCE_NAMES:
        raise ValueError('unknown packaged resource category')
    return files('physicroll').joinpath('_resources').joinpath(category)


def read_example(name):
    """Load a packaged example, without resolving a path from the caller's cwd."""
    return json.loads(resource_file('examples', name).read_text(encoding='utf-8'))
