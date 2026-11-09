"""The wheel copy must remain byte-for-byte tied to reviewed source inputs."""

from pathlib import Path
import unittest

from physicroll.resources import RESOURCE_NAMES, read_example, resource_file


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORIES = {
    'examples': ROOT / 'scenarios',
    'schemas': ROOT / 'schema',
    'shao_fixture': ROOT / 'scenarios/literature/shao2015_aa5052',
    'shao_research': ROOT / 'docs/research/data',
}


class PackageResourceTests(unittest.TestCase):
    def test_every_declared_copy_matches_source_bytes(self):
        for category, names in RESOURCE_NAMES.items():
            for name in names:
                with self.subTest(category=category, name=name):
                    source = SOURCE_DIRECTORIES[category] / name
                    self.assertEqual(resource_file(category, name).read_bytes(),
                                     source.read_bytes())

    def test_example_names_are_explicit(self):
        self.assertTrue(read_example('baseline.json')['synthetic'])
        for name in ('../baseline.json', '/tmp/baseline.json', 'missing.json'):
            with self.assertRaisesRegex(ValueError, 'unknown packaged resource'):
                read_example(name)


if __name__ == '__main__':
    unittest.main()
