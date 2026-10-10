# V1 reproducible run bundle

Create a new run directory from any packaged or caller-authored RunSpec:

```bash
python -m physicroll.bundle_cli create --run-spec scenarios/v1_schedule_search.runspec.json --out /tmp/physicroll-search-run
python -m physicroll.bundle_cli verify /tmp/physicroll-search-run
python -m physicroll.bundle_cli replay /tmp/physicroll-search-run
```

Creation computes the workflow once and publishes the directory only after
all files are complete. An existing destination is rejected. The directory
contains `input.json` (requested and resolved inputs), `result.json`,
`checks.json`, `candidates.jsonl`, `summary.csv` and `manifest.json`.
`report.html` may be included when the W5 report generator is available.
Candidate records retain search rejections or declared sensitivity cases;
an empty file means that the workflow has no candidates. The summary repeats
the distinct status axes without converting missing limits into feasibility.

The manifest records each file's SHA-256, RunSpec and ResultBundle digests,
workflow kind, and hashes of every installed PhysicRollModel Python module
and packaged resource. It also records the originating Python implementation,
full version, operating system and architecture. `verify` requires the same
Python implementation and major.minor line; patch versions, OS and architecture
may differ, but `replay` must still reproduce the exact scientific digest.
`verify` rejects missing, extra, modified or linked
files and a different installed package. It checks that derived checks,
candidate records and CSV summary still match the saved result. `replay`
first verifies, then reruns the workflow with that installed package and
requires the same canonical scientific result digest. For finite search,
this reruns candidate enumeration and the independent selected-route replay.

A bundle is portable **data**, not a standalone executable. Reproduction on
another machine requires matching installed package bytes and the declared Python
runtime line. Originating runtime metadata is outside the scientific
digest. SHA-256 detects accidental changes; it does not authenticate an
attacker who can replace the data and manifest together. Cross-platform
numerical digest parity must be checked on the supported Linux and Windows
runtimes; the current package CI performs installed bundle verification and
replay on both platforms. This software reproducibility is separate from
scientific validation and site qualification.
