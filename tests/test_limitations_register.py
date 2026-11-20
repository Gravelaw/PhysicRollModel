"""The register of limitations (docs/limitations.md) stays in step with the code (SPEC21)."""
import os
import re
import unittest

from physicroll import benchmarks, limitations as lim
from physicroll.band_plain import FLAGS, FORBIDDEN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'docs', 'limitations.md')
GAPS = os.path.join(ROOT, 'docs', 'simulation-coverage-gaps.md')


def _read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read().replace('\r\n', '\n')


def _part(text, number):
    start = text.index(f'\n## {number}. ')
    end = text.find('\n## ', start + 1)
    return text[start:] if end < 0 else text[start:end]


class LimitationsRegisterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(DOC)
        cls.result = benchmarks.run_all()   # about 30 s; once for the module

    def test_generated_blocks_equal_generator_output(self):
        blocks = lim.render_blocks(self.result)
        for name in lim.BLOCKS:
            self.assertEqual(lim.block_text(self.text, name), blocks[name],
                             f'block {name}: run python -m physicroll.limitations --write '
                             'docs/limitations.md')

    def test_register_ids_unique(self):
        ids = lim.register_ids(self.text)
        self.assertGreater(len(ids), 100)
        dup = sorted({i for i in ids if ids.count(i) > 1})
        self.assertEqual(dup, [])

    def test_every_flag_mapped_to_an_existing_row_or_informational(self):
        ids = set(lim.register_ids(self.text))
        self.assertEqual(sorted(set(FLAGS) - set(lim.FLAG_REGISTER)), [])
        self.assertEqual(sorted(set(lim.FLAG_REGISTER) - set(FLAGS)), [])
        index = lim.block_text(self.text, 'flag-index')
        for flag, rows in lim.FLAG_REGISTER.items():
            self.assertIn(f'| `{flag}` |', index)
            if rows == lim.INFORMATIONAL:
                continue
            self.assertTrue(rows)
            for r in rows:
                self.assertIn(r, ids, f'{flag} maps to {r}, which is not in the register')

    def test_every_benchmark_row_outside_the_band_is_in_part_5(self):
        part5 = lim.block_text(self.text, 'discrepancies')
        rows = benchmarks.table_rows(self.result)
        outside = [r for r in rows if r['verdict'] not in lim.NOT_LISTED_VERDICTS]
        self.assertGreater(len(outside), 0)
        for r in outside:
            self.assertIn(f'| {r["id"]} | `{r["quantity"]}` |', part5)
        for e in self.result['not_encoded']:
            self.assertIn(f'- {e["id"]}:', part5)

    def test_every_analyst_choice_constant_is_in_part_4(self):
        # The search: a module-level UPPER_CASE assignment whose line carries "[D]", "[D,",
        # "analyst choice", "the tool's own" or "the project's own" (lim.ANALYST_CHOICE_PATTERN).
        # It does not catch a tag on a comment line above the constant, an untagged threshold
        # that the guide calls an analyst choice, a choice inside a string or a rule table, or
        # lower-case names; part 4 lists those by hand below the searched ones.
        part4 = _part(self.text, 4)
        hits = lim.find_analyst_choices()
        self.assertGreater(len(hits), 40)
        missing = [f'{f}:{n} {name}' for f, n, name in hits if f'`{name}`' not in part4]
        self.assertEqual(missing, [])

    def test_part_6_matches_the_gap_study(self):
        gaps = _read(GAPS)
        reg = re.findall(r'^\| \*\*([A-Z0-9-]+)\*\* \|', _part(gaps, 5), re.MULTILINE)
        self.assertEqual(len(reg), 58)
        built = set()
        for line in _part(gaps, 11).split('\n'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 5 and cells[0] not in ('gap', '---'):
                for g in re.split(r',\s*', cells[0]):
                    if cells[4] != '-':
                        built.add(g)
                    else:
                        built.discard(g)
        part6 = _part(self.text, 6)
        sub1, sub2 = part6.split('### 6.2')
        listed1 = set(re.findall(r'^\| ([A-Z0-9-]+) \|', sub1, re.MULTILINE)) - {'gap'}
        listed2 = set(re.findall(r'^\| ([A-Z0-9-]+) \|', sub2, re.MULTILINE)) - {'gap'}
        self.assertEqual(sorted(listed1), sorted(set(reg) - built), 'not built')
        self.assertEqual(sorted(listed2), sorted(set(reg) & built), 'built in part')

    def test_prose_has_no_forbidden_word(self):
        prose = re.sub(r'`[^`]*`', '', self.text)          # code spans (engine tokens)
        prose = re.sub(r'\]\([^)]*\)', ']', prose)         # link targets (file names)
        prose = re.sub(r'<!--.*?-->', '', prose)           # marker lines
        low = prose.lower()
        found = [w for w in FORBIDDEN if w in low]
        self.assertEqual(found, [])

    def test_check_mode_reports_up_to_date(self):
        new = lim.rewrite(self.text, lim.render_blocks(self.result))
        self.assertEqual(new, self.text)


if __name__ == '__main__':
    unittest.main()
