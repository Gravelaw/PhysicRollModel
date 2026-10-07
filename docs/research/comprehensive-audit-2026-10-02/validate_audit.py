"""Validate authored audit data, links, source IDs and reproducible counts."""
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'caec37ef86a8b78e1eb88292ea6368bfb64bcbdc'
FIRST_PUBLICATION = 'ade4d1d0c4d5f8e6ca943ea1af9860446ead01d9'


def main():
    ledger = json.loads((HERE / 'source-ledger.json').read_text())
    counts = json.loads((HERE / 'source-counts.json').read_text())
    ids = {x['source_id'] for x in ledger}
    original_ledger = json.loads(subprocess.check_output(
        ['git', 'show', FIRST_PUBLICATION + ':docs/research/comprehensive-audit-2026-10-02/source-ledger.json'],
        cwd=ROOT, text=True))
    prior_by_id = {x['source_id']: x for x in original_ledger}
    current_by_id = {x['source_id']: x for x in ledger}
    assert set(prior_by_id) <= ids, 'Previously published persistent IDs were removed'
    for sid, prior in prior_by_id.items():
        current = current_by_id[sid]
        assert set(prior['urls']) <= set(current['urls']), (sid, 'Original identity URLs lost')
        assert prior['source_type'] == current['source_type'], (sid, 'Source identity reclassified')
        assert not prior['doi'] or prior['doi'] == current['doi'], (sid, 'DOI identity changed')
    assert len(ids) == len(ledger) == counts['verified_distinct_source_records']
    assert sum(counts['current_access_status'].values()) == len(ledger)
    assert Counter(x['access_status'] for x in ledger) == counts['current_access_status']
    assert Counter(x['source_type'] for x in ledger) == counts['by_source_type']
    assert all(x['reviews'] for x in ledger if x['source_type'] != 'secondary_orientation')
    assert not counts['unresolved_external_urls']
    csv_rows = list(csv.DictReader((HERE / 'source-ledger.csv').open()))
    assert [x['source_id'] for x in csv_rows] == [x['source_id'] for x in ledger]
    for row in ledger:
        assert row['doi'] or row['urls'], row['source_id']
        for url in row['urls']:
            assert urlparse(url).scheme in ('http', 'https') and urlparse(url).netloc
    json_files = sorted(HERE.glob('*.json'))
    for path in json_files:
        json.loads(path.read_text())
    trace = list(csv.DictReader((HERE / 'traceability.csv').open()))
    assert len({x['trace_id'] for x in trace}) == len(trace)
    for row in trace:
        assert all(str(v).strip() for v in row.values()), row['trace_id']
        for sid in row['source_ids'].split(';'):
            assert sid in ids or sid.strip().startswith('Repository'), (row['trace_id'], sid)
    missing_links = []
    checked_links = 0
    for path in HERE.glob('*.md'):
        content = path.read_text()
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
            if link.startswith(('https://', 'http://', '#', 'mailto:')):
                continue
            link = link.split('#')[0].split('?')[0]
            if link:
                checked_links += 1
                if not (path.parent / link).exists():
                    missing_links.append({'file': path.name, 'target': link})
    assert not missing_links, missing_links
    changed = subprocess.check_output(['git', 'diff', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    assert all(x.startswith('docs/research/') for x in changed), changed
    originals = ['docs/research/Aluminium_cold_rolling_research_for_PhysicRollModel.docx', 'docs/research/Aluminium_cold_rolling_research_for_PhysicRollModel.pdf', 'docs/research/report-update-2026-10-02.docx', 'docs/research/report-update-2026-10-02.pdf']
    preserved = {}
    for name in originals:
        raw = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
        assert raw == (ROOT / name).read_bytes(), name
        preserved[name] = hashlib.sha256(raw).hexdigest()
    result = {'status': 'passed', 'baseline_commit': BASE, 'source_records': len(ledger), 'technical_sources': sum(x['source_type'] != 'secondary_orientation' for x in ledger), 'baseline_distinct_sources': sum(bool(x['source_locations']) for x in ledger), 'audit_added_sources': sum(not bool(x['source_locations']) for x in ledger), 'traceability_rows': len(trace), 'json_files_parsed': len(json_files), 'local_markdown_links_checked': checked_links, 'missing_local_links': missing_links, 'baseline_files_scanned': counts['baseline_files_scanned'], 'external_locators_reconciled': counts['baseline_unique_external_urls'], 'unresolved_external_locators': counts['unresolved_external_urls'], 'source_review_coverage': 'Every technical source has individual fresh review/access annotation; orientation excluded from technical reliance', 'external_link_validation_scope': 'URL syntax/identity reconciliation and reviewer-documented source retrieval; not a claim all websites are reachable or full text accessible', 'historical_reports_preserved_sha256': preserved, 'physics_product_changes': False, 'remaining_limitations': ['U001 exact historical book identities unresolved', 'Source-specific inaccessible/partial texts and dataset files not fully audited', 'Optional OpenUSD runtime verification unavailable without pxr', 'No empirical plant-validation or deployment gate passed']}
    result['previous_publication_commit'] = FIRST_PUBLICATION
    result['previously_published_source_ids_preserved'] = len(prior_by_id)
    result['new_source_ids_since_first_publication'] = sorted(ids - set(prior_by_id))
    (HERE / 'validation-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
