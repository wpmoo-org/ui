"""Keep the reviewed PR114 artifact-hash exceptions strictly fingerprint-scoped."""

import unittest

from tests.helpers import ROOT


class SecretScanExceptionTests(unittest.TestCase):
    def test_only_verified_historical_artifact_fingerprints_are_ignored(self):
        entries = [
            line.strip()
            for line in (ROOT / '.gitleaksignore').read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        ]
        expected = {
            f'{commit}:tests/fixtures/boundary-baseline.json:generic-api-key:{line}'
            for commit in (
                'fa6f8e17afb021dfddea95feff8cd300589b2f9d',
                'a5df5eb4d62a397c0bad4653a1712616912d579c',
                '4ea34685c9966308739c1b711bd641d6dd31f6df',
                'dea7b98c19acbce89aa94eb0d4d5593bcf6c6f0c',
            )
            for line in (18, 730, 750, 839, 877)
        }
        self.assertEqual(len(entries), len(expected))
        self.assertEqual(set(entries), expected)
