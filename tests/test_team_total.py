import unittest
from unittest.mock import patch

from billy_track.grading import grade_leg


class TeamTotalTests(unittest.TestCase):
    def grade(self, **overrides):
        leg = dict(sport='cfb', event_date='2026-10-24', away='Pittsburgh',
                   home='Miami', market='team_total', selection='Pittsburgh',
                   line=13.5, comparison='gt')
        leg.update(overrides)
        game = dict(completed=True, id='example',
                    away={'score': 23, 'by_period': {1: 0, 2: 7}},
                    home={'score': 52, 'by_period': {1: 14, 2: 14}})
        with patch('billy_track.grading.game_result', return_value=game):
            return grade_leg(leg)

    def test_away_team_uses_own_score_not_combined_total(self):
        self.assertEqual(self.grade(line=30.5), ('lost', 23, 52))
        self.assertEqual(self.grade(), ('won', 23, 52))

    def test_home_team_under(self):
        self.assertEqual(self.grade(selection='Miami', line=52.5, comparison='lt'),
                         ('won', 23, 52))

    def test_exact_line_pushes_for_over_and_under(self):
        for comparison in ('gt', 'lt'):
            self.assertEqual(self.grade(line=23, comparison=comparison)[0], 'push')

    def test_period_total_uses_selected_team_period_score(self):
        self.assertEqual(self.grade(period='1h', line=13.5), ('lost', 7, 28))

    def test_invalid_direction_rejected(self):
        with self.assertRaises(ValueError):
            self.grade(comparison='gte')


if __name__ == '__main__':
    unittest.main()
