import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from billy_track import dashboard


class IncompleteSlipTests(unittest.TestCase):
    def test_warning_survives_cache_and_render_without_mutating_input(self):
        bet = {'odds': 536, 'stake': 5, 'legs': [{}, {}]}
        weeks = [{'label': '2026-10-28', 'bets': [bet]}]
        with tempfile.TemporaryDirectory() as directory:
            source = dict(bet, expected_leg_count=3, transcription_complete=False,
                          note='Missing third leg; visible leg lost.')
            (Path(directory) / '2026-10-28.json').write_text(json.dumps({'bets': [source]}))
            with patch.object(dashboard, 'WEEKS_DIR', Path(directory)):
                html = dashboard.render_html(weeks, {})
            self.assertIn('Missing third leg; visible leg lost.', html)
            self.assertIn('"expected_leg_count": 3', html)
        self.assertNotIn('note', bet)


if __name__ == '__main__':
    unittest.main()
