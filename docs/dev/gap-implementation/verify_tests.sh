#!/bin/bash
# Run the band test modules in five parallel groups plus the smoke script; print one line each.
# Usage (from the repository root): verify_tests.sh [extra test modules...]
S=/tmp/claude-0/-home-user-PhysicRollModel/2f99237c-57ca-5a74-a3d6-b1fb23e86cf7/scratchpad/vt
mkdir -p "$S"
python -m unittest tests.test_band_v2_sections tests.test_band_v2_process_sections tests.test_benchmarks tests.test_bite_tribology \
  tests.test_band_signatures tests.test_chatter tests.test_foil_bite tests.test_strip_shape \
  tests.test_roll_thermal tests.test_flatness_control > "$S/a.txt" 2>&1 &
python -m unittest tests.test_band_foil tests.test_band_plain tests.test_band_plain_partial \
  tests.test_band_thermal_check tests.test_band_process_temperatures \
  tests.test_band_robustness_v2_sweep tests.test_band_diagnosis_reports > "$S/b.txt" 2>&1 &
python -m unittest tests.test_band_lengthwise tests.test_band_diagnosis \
  tests.test_package_resources tests.test_band_products tests.test_band_extended_domain \
  tests.test_band_robustness tests.test_band_local tests.test_band_flatness_loop \
  tests.test_band_flatness_demos tests.test_band_flatness_demos_lengthwise > "$S/c.txt" 2>&1 &
python -m unittest tests.test_band_survey tests.test_band_app tests.test_band_app_drawing \
  tests.test_band_app_reopen tests.test_band_lengthwise_events tests.test_band_foil_demo \
  tests.test_band_plain_phase1 tests.test_band_local_sources tests.test_band_grinding "$@" > "$S/d.txt" 2>&1 &
python -m unittest tests.test_band_absent_inputs tests.test_band_sensors \
  tests.test_band_sensors_gauge tests.test_band_strip_temperature \
  tests.test_band_friction_stripes tests.test_band_roll_profile tests.test_halfspace_bite \
  tests.test_halfspace_bite_cases tests.test_halfspace_bite_branch \
  tests.test_halfspace_bite_sensitivity tests.test_halfspace_bite_modes \
  tests.test_band_halfspace tests.test_band_halfspace_default \
  tests.test_asperity_contact tests.test_band_friction_identification \
  tests.test_band_rate_temperature tests.test_band_heat_partition tests.test_roll_skin \
  tests.test_band_spray_calibration > "$S/e.txt" 2>&1 &
wait
for f in a b c d e; do echo "group $f: $(tail -n 3 "$S/$f.txt" | tr '\n' ' ')"; grep -h "^FAIL:\|^ERROR:" "$S/$f.txt"; done
python scripts/smoke.py > "$S/smoke.txt" 2>&1; echo "smoke exit $?"
