from datetime import datetime, timedelta, timezone
import unittest
from unittest import mock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from career_discovery import matching


def missing_zone(key):
    raise ZoneInfoNotFoundError(key)


try:
    ZoneInfo("Europe/Berlin")
    HAS_DATABASE = True
except ZoneInfoNotFoundError:
    HAS_DATABASE = False


class BerlinDateTests(unittest.TestCase):
    """Windows has no system time-zone database; the fallback must give the same Berlin date."""

    def instants(self):
        for year in (2025, 2026, 2027, 2030):
            # Hours around both EU switches (last Sunday of March and October, 01:00 UTC) and the midnights near them.
            for month, day in ((3, 25), (10, 25)):
                start = datetime(year, month, day, tzinfo=timezone.utc)
                yield from (start + timedelta(minutes=30 * step) for step in range(8 * 48))
            yield from (datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(hours=7 * step) for step in range(1252))

    @unittest.skipUnless(HAS_DATABASE, "no time-zone database on this system (Windows); fixed dates below still run")
    def test_fallback_matches_the_time_zone_database(self):
        zone = ZoneInfo("Europe/Berlin")
        expected = [moment.astimezone(zone).date() for moment in self.instants()]
        with mock.patch.object(matching, "ZoneInfo", side_effect=missing_zone):
            actual = [matching.berlin_date(moment) for moment in self.instants()]
        self.assertEqual(actual, expected)

    def test_fallback_on_known_switch_dates(self):
        # 2026: summer time from 29 March, back to winter time on 25 October, both at 01:00 UTC.
        cases = {(2026, 3, 29, 0, 59): "2026-03-29", (2026, 3, 29, 22, 30): "2026-03-30",
                 (2026, 3, 28, 22, 30): "2026-03-28", (2026, 10, 24, 22, 30): "2026-10-25",
                 (2026, 10, 25, 22, 30): "2026-10-25", (2026, 10, 25, 23, 30): "2026-10-26",
                 (2026, 12, 31, 23, 0): "2027-01-01", (2026, 7, 1, 21, 59): "2026-07-01",
                 (2026, 7, 1, 22, 0): "2026-07-02"}
        with mock.patch.object(matching, "ZoneInfo", side_effect=missing_zone):
            for parts, expected in cases.items():
                moment = datetime(*parts, tzinfo=timezone.utc)
                self.assertEqual(matching.berlin_date(moment).isoformat(), expected, parts)

    def test_uses_the_database_when_present(self):
        moment = datetime(2026, 11, 16, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(matching.berlin_date(moment).isoformat(), "2026-11-17")

    def test_other_offsets_are_converted_first(self):
        moment = datetime(2026, 7, 1, 20, 30, tzinfo=timezone(timedelta(hours=-5)))
        with mock.patch.object(matching, "ZoneInfo", side_effect=missing_zone):
            self.assertEqual(matching.berlin_date(moment).isoformat(), "2026-07-02")


if __name__ == "__main__":
    unittest.main()
