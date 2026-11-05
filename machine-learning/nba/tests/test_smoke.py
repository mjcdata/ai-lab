"""Verify that the installed project package is importable."""

import unittest


class PackageSmokeTest(unittest.TestCase):
    def test_package_import(self):
        import nba_player_similarity

        self.assertEqual(nba_player_similarity.__name__, "nba_player_similarity")


if __name__ == "__main__":
    unittest.main()
