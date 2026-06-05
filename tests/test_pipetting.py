"""Unit tests for high-level pipetting helpers."""

import unittest

from picus2 import multi_dispense_total


class MultiDispenseTotalTest(unittest.TestCase):
    """Tests for the multi-dispense aspiration-volume formula."""

    def test_matches_reference_example(self):
        """3 x 100 uL with 30 uL excess totals 360 uL (basics doc)."""
        self.assertEqual(multi_dispense_total(100, 3, 30), 360)

    def test_scales_with_count(self):
        """The total scales with aliquot count plus two excesses."""
        self.assertEqual(multi_dispense_total(50, 5, 20), 20 + 250 + 20)


if __name__ == "__main__":
    unittest.main()
