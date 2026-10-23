"""Contract and quarantine regressions for research evidence."""
import copy
import json
from pathlib import Path
import unittest

from garden_registry.evidence import validate

ROOT = Path(__file__).resolve().parents[1]


class EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = json.loads((ROOT / 'data/evidence/hattie-carthan.json').read_text())
        self.registry = {'snapshot_version': 'test-only', 'records': [{'id': 'nyc-greenthumb:B400-GT001'}]}

    def test_historical_claim_and_ambiguous_farm_stay_separate(self) -> None:
        output = validate(self.bundle, self.registry)
        self.assertEqual(len(output['accepted']), 1)
        self.assertEqual(output['accepted'][0]['observed_at'], '2019-03-28')
        self.assertEqual(output['accepted'][0]['unit'], 'beds_added')
        self.assertEqual(len(output['unresolved']), 1)
        self.assertEqual(len(output['unknowns']), 8)

    def test_rejects_unsupported_facts(self) -> None:
        mutations = [lambda r: r.update(citations=[]),
                     lambda r: r['citations'][0].update(source_id='missing'),
                     lambda r: r.update(observed_at='2019-02-30'),
                     lambda r: r['site_match'].update(garden_id='missing'),
                     lambda r: r.update(layout={'invented': True})]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                bundle = copy.deepcopy(self.bundle)
                mutate(bundle['records'][0])
                with self.assertRaises(ValueError):
                    validate(bundle, self.registry)

    def test_unknown_is_not_absence(self) -> None:
        self.bundle['records'][2]['value'] = False
        with self.assertRaises(ValueError):
            validate(self.bundle, self.registry)

    def test_unresolved_cannot_assign_site(self) -> None:
        self.bundle['records'][1]['site_match']['garden_id'] = 'nyc-greenthumb:B400-GT001'
        with self.assertRaises(ValueError):
            validate(self.bundle, self.registry)

    def test_unknown_rights_never_import_assets(self) -> None:
        self.bundle['sources'][0]['rights']['asset_use'] = 'download'
        with self.assertRaises(ValueError):
            validate(self.bundle, self.registry)

    def test_deterministic_and_versioned(self) -> None:
        first = validate(self.bundle, self.registry)
        self.bundle['records'].reverse()
        self.bundle['sources'].reverse()
        self.assertEqual(first, validate(self.bundle, self.registry))
        self.bundle['records'][0]['limitations'].append('Follow-up needed')
        self.assertNotEqual(first['version'], validate(self.bundle, self.registry)['version'])
