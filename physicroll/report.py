"""Deterministic, offline presentation of a checked saved run.

Every displayed numerical value comes from the RunSpec or ResultBundle. This
module does not run a solver, infer missing values, or assign qualification.
"""

from html import escape

from .run_contract import ResultBundle, RunSpec, canonical_json


ASSESSMENT_ORDER = (
    'execution', 'input_validity', 'model_applicability',
    'numerical_verification', 'declared_bounds_status',
    'declared_bounds_coverage', 'scientific_qualification',
    'operating_readiness', 'predictions_computed',
    'qualification_evidence_refs',
)


def _label(value):
    return escape(str(value), quote=True)


def _field(value, depth=0):
    if type(value) is dict:
        if not value:
            return '<span class="empty">empty object</span>'
        rows = ''.join(
            f'<tr><th scope="row">{_label(key)}</th><td>{_field(item, depth + 1)}</td></tr>'
            for key, item in value.items()
        )
        table = f'<table><tbody>{rows}</tbody></table>'
        if depth > 0:
            return f'<details><summary>{len(value)} fields</summary>{table}</details>'
        return table
    if type(value) is list:
        if not value:
            return '<span class="empty">empty list</span>'
        rows = ''.join(
            f'<tr><th scope="row">{index + 1}</th><td>{_field(item, depth + 1)}</td></tr>'
            for index, item in enumerate(value)
        )
        return f'<details><summary>{len(value)} items</summary><table><tbody>{rows}</tbody></table></details>'
    if value is None:
        return '<strong class="missing">not available (null)</strong>'
    if type(value) is str:
        return _label(value)
    return _label(canonical_json(value))


def _section(title, value):
    return f'<section><h2>{_label(title)}</h2>{_field(value)}</section>'


def render_report(spec: RunSpec, result: ResultBundle) -> str:
    """Render all saved fields without adding inferred predictions or units."""
    if not isinstance(spec, RunSpec) or not isinstance(result, ResultBundle):
        raise ValueError('report requires RunSpec and ResultBundle')
    result.verify_run_spec(spec)
    request = spec.to_dict()
    saved = result.to_dict(include_runtime_metadata=False)
    assessment = saved['assessments']
    ordered_assessment = {key: assessment[key] for key in ASSESSMENT_ORDER}
    sections = (
        ('Assessment axes', ordered_assessment),
        ('Model choices', request['model_choices']),
        ('Identities', request['identities']),
        ('Unit and sign conventions', request['unit_conventions']),
        ('Requested inputs', request['requested_inputs']),
        ('Resolved inputs', request['resolved_inputs']),
        ('Effective inputs and histories', saved['effective_inputs']),
        ('Recipe targets', request['recipe_targets']),
        ('Observations', request['observations']),
        ('Outputs and timelines', saved['outputs']),
        ('Checks, limits and residuals', saved['checks']),
        ('Numerical settings', request['numerical_settings']),
        ('Source hashes', request['source_hashes']),
        ('Card hashes', request['card_hashes']),
    )
    content = ''.join(_section(title, value) for title, value in sections)
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>PhysicRollModel saved run</title>'
        '<style>body{font:16px/1.5 system-ui,sans-serif;max-width:84rem;margin:2rem auto;'
        'padding:0 1rem;color:#172033;background:#fff}h1,h2{line-height:1.2}'
        'section{border-top:1px solid #ccd3df;padding:1rem 0}table{border-collapse:collapse;'
        'width:100%;table-layout:fixed}th,td{border:1px solid #ccd3df;padding:.4rem;'
        'text-align:left;vertical-align:top;overflow-wrap:anywhere}th{width:30%;background:#f4f6fa}'
        'details{margin:.15rem 0}summary{cursor:pointer;color:#17428c}'
        '.missing{color:#842025}.empty{color:#5a6476}.identity{overflow-wrap:anywhere}'
        '@media print{details{display:block}summary{display:none}}</style></head><body>'
        '<h1>PhysicRollModel saved run</h1>'
        '<p>This report displays saved inputs and results. Missing values remain missing; '
        'software checks do not establish scientific qualification or operating readiness.</p>'
        f'<p>Workflow: <strong>{_label(request["workflow_kind"])}</strong><br>'
        f'RunSpec SHA-256: <span class="identity">{spec.sha256}</span><br>'
        f'ResultBundle SHA-256: <span class="identity">{result.sha256}</span></p>'
        f'{content}</body></html>\n'
    )
