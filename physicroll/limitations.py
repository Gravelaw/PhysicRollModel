"""Generated blocks of the register of limitations (``docs/limitations.md``).

``python -m physicroll.limitations --write docs/limitations.md`` rewrites ONLY the blocks
between the marker lines (the recorded discrepancies of part 5 and the flag index of part 8);
the hand-written register around them is left as it is. ``--check PATH`` exits 1 when a block
differs. Standard library only; nothing here changes an engine result.

The mapping of every flag of ``band_plain.FLAGS`` to the register rows it belongs to lives in
``FLAG_REGISTER`` below (or ``INFORMATIONAL`` for a flag that only says a section was applied).
``ANALYST_CHOICE_PATTERN`` is the search the register's part 4 was built from;
``tests/test_limitations_register.py`` repeats it.
"""
import argparse
import os
import re
import sys

INFORMATIONAL = 'informational'
BLOCKS = ('discrepancies', 'flag-index')
_BEGIN = '<!-- BEGIN GENERATED BLOCK: {} (python -m physicroll.limitations --write docs/limitations.md; do not edit by hand) -->'
_END = '<!-- END GENERATED BLOCK: {} -->'

# A module-level constant whose assignment line carries one of the register's tags. It does not
# catch: a tag on a comment line above the constant (FEED_MARK_SPACING_CEILING_M,
# NARROW_STRIPE_REFERENCE_WIDTH_M), constants without a tag that section 14 of the guide calls
# analyst choices (DEFAULT_REPORTING_THRESHOLD_I_UNITS, EDGE_OR_CENTRE_FRACTION, ...), choices
# written inside strings or rule tables, or tags in lower-case names. Those are added by hand.
ANALYST_CHOICE_PATTERN = re.compile(
    r"^([A-Z][A-Z0-9_]*)\s*(?::[^=]*)?=(?!=).*"
    r"(\[D[\],;]|analyst choice|the tool's own|the project's own)", re.IGNORECASE)

# Verdicts of the benchmark harness that part 5 does not list: agreement, and a project value
# with no published value to compare with (counted only).
NOT_LISTED_VERDICTS = ('WITHIN_AGREEMENT_BAND', 'NO_REFERENCE_VALUE')
VERDICT_WORDS = {
    'RECORDED_DISCREPANCY': 'does not match the published value',
    'INDICATIVE_ASSUMED_INPUTS': 'indicative: some inputs were assumed',
    'REFERENCE_READ_BY_EYE': 'published value read by eye from a figure',
    'REFERENCE_ONLY_INPUTS_NOT_RECORDED': 'published value only; inputs not recorded',
    'CONSISTENT_REGIME': 'same regime as the published formula',
    'REFERENCE_NOT_GRID_INDEPENDENT': 'published value not grid independent',
}

# flag -> register ids (or INFORMATIONAL). One table; the test checks it against FLAGS and
# against the ids in the document.
FLAG_REGISTER = {
    'SYNTHETIC_INPUTS': ('L-DATA-01',),
    'USER_SUPPLIED_INPUTS_NOT_VERIFIED': ('L-DATA-03',),
    'EXPERIMENTAL_MATTRESS_FOIL_MODEL': ('L-BITE-02',),
    'BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL': ('L-BITE-02',),
    'DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL': ('L-BITE-02',),
    'MATTRESS_REGIME_FOIL': ('L-BITE-02',),
    'BITE_MODEL_AUTO': INFORMATIONAL,
    'BITE_MODEL_HALF_SPACE': ('L-BITE-05',),
    'BITE_MODEL_AUTO_HALF_SPACE': ('L-BITE-05',),
    'BITE_FROM_REDUCED_HALF_SPACE_MODEL': ('L-BITE-05',),
    'DERIVED_BY_HALF_SPACE_FOIL_MODEL': ('L-BITE-05',),
    'REDUCED_HALF_SPACE_FOIL_MODEL': ('L-BITE-05',),
    'HALF_SPACE_REGIME_FOIL': INFORMATIONAL,
    'HALF_SPACE_REGIME_CONVENTIONAL': INFORMATIONAL,
    'STRIP_THICKNESS_SPRING_NOT_IN_PUBLISHED_MODEL': ('L-BITE-07',),
    'SHEAR_CAP_ACTIVE': ('L-BITE-11',),
    'PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD': ('L-BITE-10',),
    'LIGHT_REDUCTION_ELASTIC_STRIP_ZONES_NOT_MODELLED': ('L-BITE-09',),
    'ZONE_STRUCTURE_AT_REGIME_BOUNDARY': ('L-BITE-08',),
    'NO_SLIP_ZONE_CREEP_ABOVE_ONE_PERCENT': ('L-BITE-09',),
    'FLOW_STRESS_RATE_TEMPERATURE_FACTOR_APPLIED': ('L-MAT-01',),
    'STRAIN_RATE_FROM_UNDEFORMED_ARC': ('L-MAT-01',),
    'BITE_TEMPERATURE_NOT_AVAILABLE_REFERENCE_USED': ('L-MAT-01',),
    'RATE_SENSITIVITY_EXTRAPOLATED_BEYOND_MEASURED_RATES': ('L-MAT-01',),
    'RATE_TEMPERATURE_FACTOR_REJECTED': ('L-MAT-02',),
    'NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING': ('L-MAT-05',),
    'STRIP_HEAT_FRACTION_COMPUTED_FROM_INTERFACE_MODEL': ('L-HEAT-04',),
    'ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL': ('L-HEAT-04',),
    'HEAT_SHARE_OUTSIDE_0_1_TEMPERATURE_DIFFERENCE_DOMINATES': ('L-HEAT-04',),
    'STRIP_NOT_THERMALLY_THIN_LUMPED_MODEL_INDICATIVE': ('L-HEAT-04',),
    'ZONE_STEP_TEST_EMULATED': ('L-LOOP-07', 'L-HEAT-09'),
    'FLATNESS_LOOP_SIMULATED': ('L-LOOP-01',),
    'FLATNESS_LOOP_NOT_SETTLED': ('L-LOOP-05',),
    'FLATNESS_LOOP_TRIMMING_LIMIT_CYCLE': ('L-LOOP-05',),
    'CONTROL_INCREASES_RESIDUAL': ('L-LOOP-05',),
    'CONTROL_ZONE_AT_LIMIT': ('L-LOOP-05',),
    'CONTROL_MADE_BAND': ('L-LOOP-05',),
    'LOW_ORDER_FLATNESS_LEFT_TO_BENDING_NOT_MODELLED': ('L-LOOP-02',),
    'FLATNESS_LOOP_ON_COARSE_GRID': ('L-LOOP-06',),
    'GRINDER_CHATTER_NOT_EXCLUDED_NO_GRINDER_DATA': ('L-GRIND-02',),
    'ROLL_PROFILE_BANDS_DEPEND_ON_DETREND_ORDER': ('L-GRIND-04',),
    'ROLL_PROFILE_GRID_TOO_COARSE': ('L-GRIND-03',),
    'LOCAL_STATE_COMPUTED': ('L-SHAPE-13',),
    'LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE': ('L-SHAPE-13',),
    'LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE': ('L-FRIC-01', 'L-SHAPE-13'),
    'OIL_SUPPLY_BELOW_SMOOTH_FILM': ('L-FRIC-09',),
    'ZERO_OIL_SUPPLY_UNDER_BLOCKED_NOZZLE_NO_SPREADING_MODEL': ('L-FRIC-09',),
    'LOCAL_FRICTION_CHANGE_ABOVE_20_PERCENT_LINEAR_SOURCE_INDICATIVE': ('L-SHAPE-14',),
    'LOCAL_SOURCES_COMPUTED': ('L-SHAPE-14',),
    'LOCAL_NET_SIGN_DEPENDS_ON_INLET_WEIGHT': ('L-SHAPE-14',),
    'LOCAL_SOURCES_REVERSE_A_BAND': ('L-SHAPE-14',),
    'LOCAL_SOURCES_SUMMED_ON_LINEAR_PROFILE_SATURATION_NOT_APPLIED': ('L-SHAPE-14',),
    'LOCAL_NET_INCOMPLETE_TERM_MISSING': ('L-SHAPE-14',),
    'ROLL_SURFACE_CYCLE_COMPUTED': ('L-HEAT-07',),
    'CIRCUMFERENTIAL_MEAN_COEFFICIENT_BIASED': ('L-HEAT-07',),
    'ROLL_ENTRY_TEMPERATURE_FROM_SURFACE_CYCLE': INFORMATIONAL,
    'FRICTION_IDENTIFIED_FROM_ENTERED_RECORDS': ('L-FRIC-04',),
    'FORWARD_SLIP_INSENSITIVE_TO_FRICTION_IN_THIS_REGIME': ('L-FRIC-04',),
    'MEASURED_SLIP_NOT_REPRODUCED_BY_CONSTANT_FRICTION_BITE': ('L-FRIC-03',),
    'IDENTIFIED_FRICTION_DIFFERS_FROM_CASE_FRICTION': ('L-FRIC-04',),
    'COLD_START_BY_FRICTION_CONTINUATION': ('L-BITE-11',),
    'ONE_SIDED_TENSION_DIFFERENCE_AT_ZERO_TENSION': ('L-BITE-17',),
    'REGIME_CHANGE_WITHIN_FINITE_DIFFERENCE_STENCIL': ('L-BITE-17',),
    'SENSITIVITY_STEP_NOT_CONVERGED': ('L-BITE-17',),
    'CONTACT_RADIUS_RATIO_CLAMPED_TO_ONE': ('L-BITE-02',),
    'BITE_MODEL_MATTRESS': ('L-BITE-02',),
    'CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE': ('L-BITE-14',),
    'CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED': ('L-BITE-15',),
    'DOUBLED_FINAL_PASS_NOT_MODELLED': ('L-BITE-16',),
    'EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN': ('L-BITE-12',),
    'REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN': ('L-BITE-12',),
    'EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR': ('L-BITE-13',),
    'THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN': ('L-BITE-01',),
    'CIRCULAR_FLATTENING_ASSUMED_NOT_VALIDATED': ('L-BITE-01',),
    'HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE': ('L-BITE-01',),
    'CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS': ('L-BITE-02',),
    'FOUNDATION_MODULUS_FROM_MEMORY_FORMULA': ('L-BITE-02',),
    'FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL': ('L-BITE-03',),
    'FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS': ('L-BITE-04',),
    'FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS': ('L-BITE-04',),
    'MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN': ('L-MAT-07',),
    'LUDERS_STRAIN_NOT_SUPPLIED_ZERO_USED_IN_WINDOWS': ('L-MAT-09',),
    'FLOW_STRESS_FROM_HARDENING_LAW': ('L-MAT-04',),
    'MODEL_STEADY_THERMAL_STRIPES_PRESENT': INFORMATIONAL,
    'OPERATING_POINT_LINEARLY_UNSTABLE': ('L-DYN-01',),
    'CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT': ('L-DYN-03',),
    'OPERATING_SPEED_OUTSIDE_SCANNED_RANGE': ('L-DYN-06',),
    'AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF': ('L-DYN-05',),
    'SHAPEMETER_OPERATOR_APPLIED': ('L-MEAS-01',),
    'MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD': ('L-MEAS-01',),
    'SHAPEMETER_DOES_NOT_COVER_STRIP': ('L-MEAS-01',),
    'SHAPEMETER_NEIGHBOUR_SPREADING_APPLIED': ('L-MEAS-02',),
    'ROLL_GROUND_PROFILE_SUPPLIED': ('L-GRIND-03',),
    'ROLL_GROUND_PROFILE_BAND_ABOVE_THRESHOLD': ('L-GRIND-03',),
    'FRICTION_STRIPE_SCREEN_APPLIED': ('L-SHAPE-12',),
    'FRICTION_STRIPE_LINEAR_FEEDBACK_NOT_SATURATED': ('L-SHAPE-12',),
    'STRIP_TEMPERATURE_TERM_SUPPLIED_PROFILE': ('L-SHAPE-10',),
    'STRIP_EXPANSION_COEFFICIENT_FROM_MEMORY_DEFAULT': ('L-SHAPE-10',),
    'STRIP_TEMPERATURE_SCAN_DOES_NOT_COVER_STRIP': ('L-SHAPE-11',),
    'STRIP_TEMPERATURE_TERM_WITHOUT_MECHANICAL_PROFILE': ('L-SHAPE-11',),
    'STRIP_TEMPERATURE_CHANGES_A_BAND_STATE': ('L-SHAPE-10',),
    'SHAPEMETER_TEMPERATURE_COMPENSATED': ('L-MEAS-03',),
    'GAUGE_TRANSFER_APPLIED': ('L-MEAS-04',),
    'GAUGE_KEEPS_LESS_THAN_HALF_OF_OBSERVED_MARK': ('L-MEAS-04',),
    'GAUGE_NOT_DETECTED_BUT_MARK_NOT_RESOLVABLE': ('L-MEAS-05',),
    'LENGTHWISE_MODEL_BAND_NOT_UNDER_GAUGE': ('L-MEAS-04',),
    'MEASUREMENT_SECTION_FAILED': ('L-DATA-10',),
    'SPRAY_COEFFICIENT_BASIS_NOT_ESTABLISHED': ('L-HEAT-03',),
    'STRIP_EXIT_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT': ('L-HEAT-11',),
    'OIL_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT': ('L-HEAT-11',),
    'OIL_SUPPLY_TEMPERATURE_ABOVE_SITE_CAP': ('L-HEAT-11',),
    'HEAT_PARTITION_INPUTS_INCONSISTENT': ('L-HEAT-05',),
    'MODELLED_EXIT_TEMPERATURE_ABOVE_BATTERY_COIL_LIMIT': ('L-COIL-07',),
    'DUPLICATE_BAND_POSITIONS_MERGED': ('L-DATA-11',),
    'FORCE_SENSITIVITY_DERIVED_NOT_FROM_SUPPLIED_BITE': ('L-BITE-18',),
    'CASE_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE': ('L-DATA-05',),
    'FINAL_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE': ('L-DATA-05',),
    'CASE_STRENGTH_BELOW_STANDARD_MINIMUM_FOR_GAUGE': ('L-DATA-05',),
    'RIGID_BOUND_NOT_DEFINED_BUMP_REACHES_GAUGE': ('L-SHAPE-02',),
    'COMPLIANCE_ONLY_LEVEL_NOT_DEFINED_CHANGE_REACHES_GAUGE': ('L-SHAPE-02',),
    'HYPOTHESIS_EVALUATION_FAILED': ('L-DATA-10',),
    'NEXT_MEASUREMENTS_FAILED': ('L-DATA-10',),
    'STRIP_MAP_FAILED': ('L-DATA-10',),
    'SIGNATURES_SECTION_FAILED': ('L-DATA-10',),
    'SCREENS_SECTION_FAILED': ('L-DATA-10',),
    'THERMAL_CHECK_FAILED': ('L-DATA-10',),
    'MATERIAL_SELECTION_FAILED': ('L-DATA-10',),
    'THERMAL_SENSITIVITY_PER_PASS_FAILED': ('L-DATA-10',),
    'THERMAL_SENSITIVITY_FAILED': ('L-DATA-10',),
    'BITE_DERIVATION_FAILED_CHATTER_NOT_ASSESSABLE': ('L-BITE-13', 'L-DATA-10'),
    'WIDTH_SECTION_PARTIAL_FAILURE': ('L-DATA-10',),
    'WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE': ('L-BITE-13',),
    'WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT': ('L-BITE-13',),
    'SUPPLIED_BITE_SENSITIVITIES_NOT_VERIFIED': ('L-DATA-03',),
    'BITE_RESPONSE_SUPPLIED': INFORMATIONAL,
    'SHAPE_INPUTS_SUPPLIED': INFORMATIONAL,
    'STEADY_STATE_NOT_CONVERGED': ('L-HEAT-01',),
    'PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED': ('L-FRIC-01',),
    'FRICTION_FROM_PLACEHOLDER_CLOSURE': ('L-FRIC-01',),
    'BUCKLING_FE_REPORTED_BESIDE_SINE_MODE': ('L-SHAPE-16',),
    'BUCKLING_FE_IN_MILL_STATE_DIFFERS_FROM_SINE_MODE': ('L-SHAPE-16',),
    'BUCKLING_FE_RELEASED_STATE_DIFFERS_FROM_SINE_MODE': ('L-SHAPE-16',),
}

REGISTER_ID = re.compile(r'^\| (L-[A-Z]+-\d{2}) \|', re.MULTILINE)


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _num(x):
    if x is None:
        return '-'
    return f'{x:.4g}'


def _cell(text):
    return str(text).replace('|', '\\|')


def find_analyst_choices(package_dir=None):
    """(module file, line number, constant name) for every hit of ``ANALYST_CHOICE_PATTERN``."""
    package_dir = package_dir or os.path.dirname(os.path.abspath(__file__))
    hits = []
    for name in sorted(os.listdir(package_dir)):
        if not name.endswith('.py'):
            continue
        with open(os.path.join(package_dir, name), encoding='utf-8') as fh:
            for n, line in enumerate(fh, 1):
                m = ANALYST_CHOICE_PATTERN.match(line)
                if m and m.group(1).isupper():
                    hits.append((name, n, m.group(1)))
    return hits


def discrepancy_rows(result=None):
    """Benchmark rows part 5 lists: every row whose verdict is not in ``NOT_LISTED_VERDICTS``."""
    from . import benchmarks
    rows = benchmarks.table_rows(result)
    return [r for r in rows if r['verdict'] not in NOT_LISTED_VERDICTS], rows


def render_discrepancies(result=None):
    from . import benchmarks
    result = benchmarks.run_all() if result is None else result
    listed, rows = discrepancy_rows(result)
    within = sum(1 for r in rows if r['verdict'] == 'WITHIN_AGREEMENT_BAND')
    no_ref = sum(1 for r in rows if r['verdict'] == 'NO_REFERENCE_VALUE')
    lo, hi = benchmarks.AGREEMENT_BAND
    L = [f'The benchmark harness records {len(rows)} project values in '
         f'{len(result["cases"])} cases. {within} carry the verdict "within the agreement band" '
         f'(project / reference {lo} to {hi}); {no_ref} record a project value for which no '
         f'published value exists. The other {len(listed)} are listed here, including rows '
         'whose ratio lies inside the band but whose verdict qualifies the comparison (numbers '
         'to four significant digits).', '',
         '| case | quantity | unit | project | reference | ratio | verdict | in plain words |',
         '|---|---|---|---|---|---|---|---|']
    for r in listed:
        L.append(f'| {r["id"]} | `{r["quantity"]}` | {_cell(r["unit"])} | {_num(r["project"])} | '
                 f'{_num(r["reference"])} | {_num(r["ratio"])} | `{r["verdict"]}` | '
                 f'{VERDICT_WORDS.get(r["verdict"], "-")} |')
    L += ['', 'Cases not encoded, with the reason:', '']
    for e in result['not_encoded']:
        L.append(f'- {e["id"]}: {e["reason"]}.')
    return '\n'.join(L)


def render_flag_index():
    from .band_plain import FLAGS
    L = ['| flag | what it says | register row |', '|---|---|---|']
    for flag in sorted(FLAGS):
        sentence = FLAGS[flag][0] if isinstance(FLAGS[flag], tuple) else FLAGS[flag]
        ids = FLAG_REGISTER.get(flag)
        where = ('not mapped' if ids is None else
                 INFORMATIONAL if ids == INFORMATIONAL else ', '.join(ids))
        L.append(f'| `{flag}` | {_cell(sentence)} | {where} |')
    return '\n'.join(L)


def render_blocks(result=None):
    return {'discrepancies': render_discrepancies(result), 'flag-index': render_flag_index()}


def block_text(text, name):
    """The committed content of one block (between the marker lines), line endings normalised."""
    text = text.replace('\r\n', '\n')
    b, e = _BEGIN.format(name), _END.format(name)
    i, j = text.find(b), text.find(e)
    if i < 0 or j < i:
        raise ValueError(f'markers of block {name!r} not found')
    return text[i + len(b):j].strip('\n')


def rewrite(text, blocks):
    text = text.replace('\r\n', '\n')
    for name in BLOCKS:
        b, e = _BEGIN.format(name), _END.format(name)
        i, j = text.find(b), text.find(e)
        if i < 0 or j < i:
            raise ValueError(f'markers of block {name!r} not found')
        text = text[:i + len(b)] + '\n' + blocks[name] + '\n' + text[j:]
    return text


def register_ids(text):
    return REGISTER_ID.findall(text.replace('\r\n', '\n'))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='python -m physicroll.limitations',
        description='Rewrite the generated blocks of the register of limitations.')
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', metavar='PATH', help='rewrite the generated blocks of PATH')
    g.add_argument('--check', metavar='PATH', help='exit 1 if a generated block of PATH differs')
    args = parser.parse_args(argv)
    path = args.write or args.check
    with open(path, encoding='utf-8') as fh:
        old = fh.read()
    new = rewrite(old, render_blocks())
    if args.check:
        same = new == old.replace('\r\n', '\n')
        print('up to date' if same else f'{path}: generated blocks differ')
        return 0 if same else 1
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(new)
    print(f'wrote the generated blocks of {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
