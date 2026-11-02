import unittest
from decimal import Decimal

from app.subscriptions.service import normalize_monthly


class MonthlySpendNormalizationTests(unittest.TestCase):
    def test_supported_intervals_use_decimal_arithmetic(self):
        self.assertEqual(normalize_monthly(Decimal("120.00"), "monthly"), Decimal("120.000000"))
        self.assertEqual(normalize_monthly(Decimal("1200.00"), "annual"), Decimal("100.000000"))
        self.assertEqual(normalize_monthly(Decimal("300.00"), "quarterly"), Decimal("100.000000"))
        self.assertEqual(normalize_monthly(Decimal("52.00"), "weekly"), Decimal("225.333333"))

    def test_unknown_interval_or_amount_is_unavailable(self):
        self.assertIsNone(normalize_monthly(None, "monthly"))
        self.assertIsNone(normalize_monthly(Decimal("10"), "unknown"))


if __name__ == "__main__":
    unittest.main()
