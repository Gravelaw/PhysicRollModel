"""Rebuild the authored audit ledger and reconcile baseline citation occurrences.

Run from the repository root. No network requests, source downloads or model changes.
Reviewer JSONs are original annotations; source content is not copied.
"""
import csv
import hashlib
import json
import re
import subprocess
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'caec37ef86a8b78e1eb88292ea6368bfb64bcbdc'
DATE = '2026-10-02'


def canonical(url):
    url = url.strip().rstrip("'.,;*")
    while url.endswith(')') and url.count(')') > url.count('('):
        url = url[:-1]
    return unquote(url).replace('http://', 'https://').rstrip('/').lower()


def dump(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def table(name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in r.items()})


def main():
    originals = json.loads((HERE / 'original-bibliography.json').read_text())
    extras = json.loads((HERE / 'additional-sources.json').read_text())
    records = originals + extras
    ids = {r['source_id']: r for r in records}
    assert len(ids) == len(records), 'Duplicate persistent source IDs'
    assert {r['source_id'] for r in originals} == {f'R{i:03}' for i in range(1, 106)}
    aliases = json.loads((HERE / 'url-aliases.json').read_text())
    urls = {}
    def bind(url, sid):
        assert sid in ids, f'Unknown source ID {sid}'
        key = canonical(url)
        assert key not in urls or urls[key] == sid, f'URL collision: {url}: {urls.get(key)} vs {sid}'
        urls[key] = sid
    for r in records:
        for u in r.get('urls', []):
            bind(u, r['source_id'])
    for u, sid in aliases.items():
        bind(u, sid)
    reviews = {}
    for p in sorted(HERE.glob('*-source-reviews.json')):
        data = json.loads(p.read_text())
        if isinstance(data, dict):
            data = data.get('sources', data.get('reviews', data.get('records', [])))
        for r in data:
            sid = r.get('legacy_id') or r.get('source_id')
            if isinstance(sid, int):
                sid = f'R{sid:03}'
            if sid and sid.isdigit():
                sid = f'R{int(sid):03}'
            if sid not in ids:
                candidates = [r.get('url'), r.get('primary_url'), r.get('doi_url')]
                if r.get('doi'):
                    candidates.append('https://doi.org/' + r['doi'].replace('https://doi.org/', ''))
                sid = next((urls.get(canonical(x)) for x in candidates if x and urls.get(canonical(x))), None)
            if sid not in ids:
                raise ValueError(f'Unmapped review in {p.name}: {r.get("title")} / {r.get("url")}')
            r = dict(r, review_file=p.name)
            r['reported_access_status'] = r.get('access_status')
            r['access_status'] = {'fulltext_available_relevant_sections_reviewed': 'partial_text_reviewed', 'unavailable_in_fresh_review': 'unavailable'}.get(r.get('access_status'), r.get('access_status'))
            reviews.setdefault(sid, []).append(r)
            for key in ('url', 'primary_url', 'doi_url'):
                if isinstance(r.get(key), str) and r[key].startswith('http'):
                    bind(r[key], sid)
            if r.get('doi'):
                bind('https://doi.org/' + r['doi'].replace('https://doi.org/', ''), sid)
    source_files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    occurrences = []
    files_scanned = []
    for name in source_files:
        suffix = Path(name).suffix
        if suffix not in ('.md', '.json', '.py', '.toml', '.txt', '.csv', '.yml', '.yaml', '.docx', '.pdf'):
            continue
        raw = subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT)
        files_scanned.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest()})
        if suffix == '.docx':
            import io
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                found = []
                for member in z.namelist():
                    if member.endswith('.rels'):
                        found += [e.attrib['Target'] for e in ET.fromstring(z.read(member)) if e.attrib.get('TargetMode') == 'External']
                text = ' '.join(ET.fromstring(z.read('word/document.xml')).itertext())
                found += re.findall(r'https?://[^\s<>"\]}`]+', text)
        elif suffix == '.pdf':
            import io
            from pypdf import PdfReader
            pdf = PdfReader(io.BytesIO(raw))
            found = []
            for page in pdf.pages:
                for annot in page.get('/Annots', []):
                    action = annot.get_object().get('/A', {})
                    if action.get('/URI'):
                        found.append(str(action['/URI']))
            # PDF rendered line breaks can split URLs; annotations and DOCX
            # relationships retain exact links. Text is used for bare DOI IDs.
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        else:
            text = raw.decode(errors='replace')
            found = re.findall(r'https?://[^\s<>"\]}`]+', text)
        # Include bare DOI citations (e.g. dataset IDs in bibliography notes),
        # not just hyperlinks. This prevents undercounting the source library.
        for doi in re.findall(r'10\.\d{4,9}/[A-Za-z0-9()_./:+-]+', text):
            found.append('https://doi.org/' + doi.rstrip('.,;'))
        for u in found:
            norm = canonical(u)
            sid = urls.get(norm)
            if not norm.startswith('http') or 'github.com/gravelaw/physicrollmodel' in norm:
                cls = 'internal_project_reference'
            elif 'example.invalid/' in norm:
                cls = 'schema_identifier_not_evidence'
            else:
                cls = 'external_source' if sid else 'unresolved_external_url'
            occurrences.append({'file': name, 'url': u, 'canonical_url': norm, 'source_id': sid, 'classification': cls})
    unique = {(r['file'], r['canonical_url']): r for r in occurrences}
    occurrences = sorted(unique.values(), key=lambda x: (x['file'], x['canonical_url']))
    rank = {'full_text_reviewed': 6, 'official_document_reviewed': 5, 'partial_text_reviewed': 4, 'abstract_only': 3, 'metadata_only': 2, 'unavailable': 1, 'not_retrieved_orientation_only': 0}
    trace = list(csv.DictReader((HERE / 'traceability.csv').open())) if (HERE / 'traceability.csv').exists() else []
    for r in records:
        sid = r['source_id']
        rr = reviews.get(sid, [])
        r['reviews'] = rr
        if rr:
            best = max(rr, key=lambda x: rank.get(x.get('access_status'), -1))
            r['topic'] = sorted(set(x['review_file'].replace('-source-reviews.json', '') for x in rr))
            if sid not in {x['source_id'] for x in originals}:
                r['title'] = best.get('title', r['title'])
            for k in ('access_date', 'access_status'):
                r[k] = best.get(k) or r.get(k) or 'Not specified in review; resolve before quantitative reuse.'
            # Preserve every review's complementary claim/locator; access rank is
            # only a compact best-depth count, never a truth/quality ranking.
            for k in ('version', 'pages_equations_tables', 'findings', 'weaknesses_conflicts', 'domain', 'evidence_level', 'relevance'):
                r[k] = [{'review_file': x['review_file'], 'value': x[k]} for x in rr if x.get(k)]
            r['access_summary'] = [{'review_file': x['review_file'], 'version': x.get('version'), 'status': x['access_status'], 'reported_status': x['reported_access_status']} for x in rr]
            if best.get('doi'):
                r['doi'] = best['doi']
        else:
            r.setdefault('topic', ['orientation' if r['source_type'] == 'secondary_orientation' else 'access_gap'])
            r.setdefault('access_status', 'metadata_only')
            r.setdefault('access_date', DATE)
            r.setdefault('version', 'Identity recorded; exact accessible revision unresolved')
            r.setdefault('pages_equations_tables', 'No freshly inspected primary body locator')
            r.setdefault('findings', 'Identity accounted for; no new quantitative claim adopted.')
            r.setdefault('weaknesses_conflicts', 'Further primary access needed before equation or parameter reuse.')
            r.setdefault('domain', 'See original title and historical note; no unqualified transfer')
            r.setdefault('evidence_level', 'metadata lead only')
            r.setdefault('relevance', 'Evidence-acquisition backlog; does not calibrate the model')
        r['source_locations'] = sorted(set(x['file'] for x in occurrences if x['source_id'] == sid))
        r['traceability_ids'] = [x['trace_id'] for x in trace if sid in x['source_ids'].split(';')]
        r['implementation_link_status'] = 'See linked requirement rows; source access is not implementation or validation' if r['traceability_ids'] else 'No direct implemented-equation attribution; reviewed for research/architecture/data acquisition or orientation'
        r['aliases'] = sorted(k for k, v in urls.items() if v == sid)
        r.setdefault('doi', next((unquote(u).split('doi.org/', 1)[1] for u in r.get('urls', []) if 'doi.org/' in u), None))
        r.setdefault('historical_review', 'Additional source; not a numbered entry in historical report')
        r.setdefault('redistribution', 'Citations and original analysis only; no third-party full text redistributed')
    required = {'source_id', 'title', 'urls', 'source_type', 'topic', 'doi', 'access_date', 'access_status', 'version', 'pages_equations_tables', 'findings', 'weaknesses_conflicts', 'domain', 'evidence_level', 'relevance'}
    doi_ids = {}
    for r in records:
        assert not (required - r.keys()), (r['source_id'], required - r.keys())
        assert r['access_status'] in rank, (r['source_id'], r['access_status'])
        assert r['urls'] and all(u.startswith('https://') or u.startswith('http://') for u in r['urls'])
        if r['doi']:
            doi = r['doi'].lower().replace('https://doi.org/', '')
            assert doi not in doi_ids or doi_ids[doi] == r['source_id'], f'Duplicate DOI {doi}'
            doi_ids[doi] = r['source_id']
    counts = {'baseline_commit': BASE, 'audit_date': DATE, 'verified_distinct_source_records': len(records), 'original_numbered_records': len(originals), 'additional_records': len(extras), 'by_source_type': dict(sorted(Counter(r['source_type'] for r in records).items())), 'current_access_status': dict(sorted(Counter(r['access_status'] for r in records).items())), 'records_with_fresh_reviewer_annotation': len(reviews), 'baseline_files_scanned': len(files_scanned), 'baseline_file_url_pairs': len(occurrences), 'baseline_unique_external_urls': len(set(x['canonical_url'] for x in occurrences if x['classification'] in ('external_source', 'unresolved_external_url'))), 'unresolved_external_urls': sorted(set(x['canonical_url'] for x in occurrences if x['classification'] == 'unresolved_external_url')), 'unresolved_historical_clusters': [{'id': 'U001', 'description': 'Historical book-lead list absent; handoff mentions 14, exact identities not recovered', 'verified_distinct_count': None}], 'counts_are_not_quality_scores': True}
    dump('source-ledger.json', records)
    table('source-ledger.csv', [{k: v for k, v in r.items() if k != 'reviews'} for r in records])
    dump('source-counts.json', counts)
    table('citation-occurrences.csv', occurrences)
    dump('baseline-files-scanned.json', files_scanned)
    lines = ['# Annotated source inventory', '', 'Generated from original bibliography, additional identities and independent review records. See `audit-scope.md` for counting rules. The compact status is the greatest documented current access depth for any representation; it is not a quality score and does not imply every version/supplement was read. All complementary reviewer findings and conflicts are retained below and in JSON/CSV.', '']
    def pretty(value):
        if isinstance(value, list):
            return '; '.join((f"[{x['review_file']}] " + pretty(x['value'])) if isinstance(x, dict) and 'value' in x else pretty(x) for x in value)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    for r in records:
        lines += [f"## {r['source_id']} — {r['title']}", '', f"Source: [{r['urls'][0]}]({r['urls'][0]}) · Type: {r['source_type']} · Current access: **{r['access_status']}** · Date: {r['access_date']}", '', f"Version/locator: {pretty(r['version'])}. {pretty(r['pages_equations_tables'])}", '', f"Domain/evidence: {pretty(r['domain'])}. {pretty(r['evidence_level'])}", '', f"Findings: {pretty(r['findings'])}", '', f"Limits/conflicts: {pretty(r['weaknesses_conflicts'])}", '', f"Project use: {pretty(r['relevance'])}. Trace rows: {', '.join(r['traceability_ids']) or 'none; future/context source'}.", '', f"Historical review record: {r['historical_review']}", '']
    (HERE / 'annotated-source-review.md').write_text('\n'.join(lines))
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
