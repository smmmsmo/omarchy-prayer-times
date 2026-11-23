import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("prayer_fetch", ROOT / "fetch.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
DAY = dt.date(2026, 11, 24)


def response(day=DAY, zone="Asia/Dhaka", method=1, polar=False):
    tz = ZoneInfo(zone)
    hours = {"Fajr": (5, 0), "Sunrise": (6, 19), "Dhuhr": (11, 45), "Asr": (15, 35),
             "Sunset": (17, 11), "Maghrib": (17, 11), "Isha": (18, 30)}
    if polar:
        hours.update({key: (0, 46) for key in ("Fajr", "Sunrise", "Sunset", "Maghrib", "Isha")})
    return {"code": 200, "data": {
        "date": {"gregorian": {"date": day.strftime("%d-%m-%Y")}},
        "meta": {"timezone": zone, "method": {"id": method}},
        "timings": {k: dt.datetime.combine(day, dt.time(*v), tzinfo=tz).isoformat() for k, v in hours.items()},
    }}


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prayer-tests-")
        self.addCleanup(self.temp.cleanup)
        self.cache = patch.object(b, "CACHE", Path(self.temp.name))
        self.cache.start()
        self.addCleanup(self.cache.stop)
        self.cfg = b.config({"locationMode": "manual", "city": "Dhaka", "country": "Bangladesh"})
        self.days = [b.parse_day(response(DAY + dt.timedelta(days=i)), DAY + dt.timedelta(days=i)) for i in (0, 1)]
        self.now = dt.datetime(2026, 11, 24, 0, 30, tzinfo=ZoneInfo("Asia/Dhaka"))

    def report(self):
        return b.make_report(self.cfg, self.days, "Dhaka", self.now)

    def test_neutral_defaults(self):
        cfg = b.config({})
        self.assertEqual(cfg["method"], "auto")
        self.assertEqual(cfg["school"], 0)
        self.assertNotIn("city", cfg)
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertFalse(manifest["barWidget"]["defaults"]["autoRefresh"])

    def test_all_provider_methods_and_schools(self):
        for method in b.METHODS:
            for school in (0, 1):
                cfg = b.config({"method": method, "school": school})
                self.assertEqual(cfg["method"], method)
                self.assertEqual(cfg["school"], school)
        self.assertIn(0, b.METHODS)
        self.assertIn(7, b.METHODS)

    def test_strict_settings(self):
        for raw in (None, [], {"method": True}, {"method": 1.2}, {"method": 99},
                    {"school": 3}, {"highLatitude": 4}, {"offsets": {"Isha": -31}},
                    {"offsets": {"unknown": 2}}, {"offsets": []}, {"ishaEnd": "other"}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                b.config(raw)

    def test_manual_location_required(self):
        for values in ({"locationMode": "manual"}, {"locationMode": "manual", "city": "Paris"},
                       {"locationMode": "manual", "city": "", "country": "France"}):
            with self.assertRaises(ValueError):
                b.config(values)

    def test_zero_and_negative_coordinates(self):
        for lat, lon in ((0, 0), (-33.8688, 151.2093), (51.5074, -0.1278), (90, -180)):
            cfg = b.config({"locationMode": "coordinates", "latitude": lat, "longitude": lon})
            self.assertEqual(cfg["latitude"], lat)
            self.assertEqual(cfg["longitude"], lon)
        for value in ("", None, True, float("inf"), float("nan"), 91):
            with self.assertRaises(ValueError):
                b.coordinate(value, 90)

    def test_strip_control_and_bidi_spoofing(self):
        self.assertEqual(b.clean(" Dhaka\u202e\n "), "Dhaka")
        self.assertEqual(b.clean("ঢাকা"), "ঢাকা")
        with self.assertRaises(ValueError):
            b.clean("x" * 101)

    def test_prayer_and_fasting_boundaries(self):
        r = self.report()
        self.assertEqual(r["rows"][0]["end"], r["sunrise"])
        self.assertEqual(r["rows"][1]["end"], r["rows"][2]["start"])
        self.assertEqual(r["rows"][2]["end"], r["sunset"])
        self.assertEqual(r["rows"][3]["end"], r["rows"][4]["start"])
        self.assertEqual(r["sehri"], r["rows"][0]["start"])
        self.assertNotEqual(r["sehri"], r["sunrise"])
        self.assertEqual(r["iftar"], r["rows"][3]["start"])

    def test_half_night_and_fajr_conventions(self):
        r = self.report()
        self.assertEqual(r["rows"][4]["end"], (r["sunset"] + r["tomorrowSehri"]) // 2)
        self.cfg["ishaEnd"] = "fajr"
        r = self.report()
        self.assertEqual(r["rows"][4]["end"], r["tomorrowSehri"])
        self.assertEqual(r["clock"][str(r["rows"][4]["end"])]["day"], 1)

    def test_local_offsets(self):
        before = self.report()
        self.cfg["offsets"].update(Fajr=-3, Maghrib=2, Isha=5)
        after = self.report()
        self.assertEqual(after["sehri"], before["sehri"] - 180)
        self.assertEqual(after["iftar"], before["iftar"] + 120)
        self.assertEqual(after["rows"][3]["end"], before["rows"][3]["end"] + 300)

    def test_conflicting_isha_limit_does_not_hide_other_prayers(self):
        self.days[0]["times"]["Isha"] = self.days[1]["times"]["Fajr"] - 600
        r = self.report()
        self.assertIsNone(r["rows"][4]["end"])
        self.assertIn("window", r["warnings"])
        self.assertIsNotNone(r["sehri"])

    def test_global_timezones_and_fractional_offsets(self):
        for zone in ("Europe/London", "America/New_York", "Australia/Sydney", "Asia/Kathmandu",
                     "Pacific/Auckland", "Pacific/Kiritimati", "Pacific/Honolulu", "America/St_Johns",
                     "Africa/Johannesburg", "Asia/Tehran", "Australia/Eucla", "America/Sao_Paulo"):
            with self.subTest(zone=zone):
                days = [b.parse_day(response(DAY + dt.timedelta(days=i), zone), DAY + dt.timedelta(days=i))
                        for i in (0, 1)]
                local = self.now.replace(tzinfo=ZoneInfo(zone))
                r = b.make_report(self.cfg, days, "Test", local)
                self.assertEqual(r["clock"][str(r["sehri"])]["h"], 5)
                self.assertEqual(r["date"], DAY.isoformat())

    def test_both_dst_directions(self):
        for date, length in ((dt.date(2026, 3, 8), 82800), (dt.date(2026, 11, 1), 90000)):
            days = [b.parse_day(response(date + dt.timedelta(days=i), "America/New_York"),
                                date + dt.timedelta(days=i)) for i in (0, 1)]
            now = dt.datetime.combine(date, dt.time(12), tzinfo=ZoneInfo("America/New_York"))
            r = b.make_report(self.cfg, days, "New York", now)
            self.assertEqual(r["validUntil"] - r["validFrom"], length)

    def test_explicit_next_day_isha(self):
        raw = response()
        raw["data"]["timings"]["Isha"] = "2026-11-25T00:15:00+06:00"
        day = b.parse_day(raw, DAY)
        self.assertEqual(dt.datetime.fromtimestamp(day["times"]["Isha"], ZoneInfo("Asia/Dhaka")).day, 25)

    def test_reykjavik_provider_labels_midnight_sunset_with_wrong_day(self):
        date = dt.date(2026, 6, 21)
        raw = response(date, "Atlantic/Reykjavik", 3)
        raw["data"]["timings"].update({
            "Fajr": "2026-06-21T01:30:00+00:00", "Sunrise": "2026-06-21T02:55:00+00:00",
            "Dhuhr": "2026-06-21T13:30:00+00:00", "Asr": "2026-06-21T18:22:00+00:00",
            "Sunset": "2026-06-21T00:04:00+00:00", "Maghrib": "2026-06-21T00:04:00+00:00",
            "Isha": "2026-06-21T01:30:00+00:00",
        })
        result = b.parse_day(raw, date)
        self.assertFalse(result["polar"])
        for key in ("Sunset", "Maghrib", "Isha"):
            self.assertEqual(dt.datetime.fromtimestamp(result["times"][key], dt.timezone.utc).day, 22)

    def test_offset_cannot_publish_iftar_before_actual_sunset(self):
        self.cfg["offsets"]["Maghrib"] = -2
        r = self.report()
        self.assertIsNone(r["iftar"])
        self.assertIsNone(r["tomorrowIftar"])
        self.assertIn("window", r["warnings"])

    def test_reject_ambiguous_or_spoofed_datetime(self):
        for value in ("05:00", "2026-11-24T05:00:00", "2026-11-24T05:00:00+00:00",
                      "2026-11-29T05:00:00+06:00", '<img src="https://example.invalid/tracker">'):
            raw = response()
            raw["data"]["timings"]["Fajr"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                b.parse_day(raw, DAY)

    def test_reject_wrong_date_and_out_of_order_data(self):
        with self.assertRaises(ValueError):
            b.parse_day(response(), DAY + dt.timedelta(days=1))
        raw = response()
        raw["data"]["timings"]["Asr"] = "2026-11-24T01:00:00+06:00"
        with self.assertRaises(ValueError):
            b.parse_day(raw, DAY)

    def test_polar_placeholders_are_not_fasting_times(self):
        self.days = [b.parse_day(response(DAY + dt.timedelta(days=i), polar=True),
                                 DAY + dt.timedelta(days=i)) for i in (0, 1)]
        r = self.report()
        self.assertIsNone(r["sunrise"])
        self.assertIsNone(r["sehri"])
        self.assertIsNone(r["iftar"])
        self.assertIsNotNone(r["rows"][1]["start"])
        self.assertIn("solar", r["warnings"])

    def test_missing_fajr_preserves_real_solar_times(self):
        raw = response()
        raw["data"]["timings"]["Fajr"] = None
        self.days[0] = b.parse_day(raw, DAY)
        r = self.report()
        self.assertIsNone(r["sehri"])
        self.assertIsNotNone(r["sunrise"])
        self.assertIsNotNone(r["sunset"])

    def test_automatic_method_omitted_and_query_encoded(self):
        cfg = b.config({"locationMode": "manual", "city": "A&B;$(touch x)", "country": "US",
                        "state": "New York", "highLatitude": 2, "shafaq": "abyad"})
        url = b.day_url(cfg, {}, DAY)
        self.assertIn("city=A%26B%3B%24%28touch+x%29", url)
        self.assertIn("state=New+York", url)
        self.assertIn("latitudeAdjustmentMethod=2", url)
        self.assertIn("iso8601=true", url)
        self.assertNotIn("&method=", url)

    def test_corrupt_cache_recovers(self):
        (b.CACHE / "broken.json").write_text("{bad")
        self.assertIsNone(b.read_cache("broken"))
        with patch.object(b, "fetch_json", return_value=response()) as fetch:
            self.assertEqual(b.get_day(self.cfg, {}, DAY)["date"], DAY.isoformat())
            b.get_day(self.cfg, {}, DAY)
            self.assertEqual(fetch.call_count, 1)

    def test_unwritable_cache_does_not_fail_fetch(self):
        with patch.object(b, "write_cache", return_value=False), \
             patch.object(b, "fetch_json", return_value=response()):
            self.assertEqual(b.get_day(self.cfg, {}, DAY)["date"], DAY.isoformat())

    def test_bounded_private_cache(self):
        self.assertTrue(b.write_cache("test", {"ok": True}))
        self.assertEqual((b.CACHE / "test.json").stat().st_mode & 0o777, 0o600)
        (b.CACHE / "large.json").write_bytes(b" " * (b.MAX_BYTES + 1))
        self.assertIsNone(b.read_cache("large"))

    def test_ip_response_validation(self):
        with patch.object(b, "fetch_json", return_value={"latitude": "NaN", "longitude": 0}):
            with self.assertRaises(ValueError):
                b.location()
        with patch.object(b, "fetch_json", return_value={"latitude": 0, "longitude": 0, "name": "Null Island"}) as fetch:
            self.assertEqual(b.location()["name"], "Null Island")
            self.assertEqual(b.location()["latitude"], 0)
            self.assertEqual(fetch.call_count, 1)

    def test_offline_never_requests_network(self):
        with patch.object(b, "fetch_json") as fetch:
            self.assertFalse(b.run(self.cfg, offline=True)["ok"])
            fetch.assert_not_called()

    def test_offline_midnight_rollover(self):
        for i in (0, 1, 2):
            date = DAY + dt.timedelta(days=i)
            with patch.object(b, "fetch_json", return_value=response(date)):
                b.get_day(self.cfg, {}, date)
        b.write_cache(b.state_key(self.cfg), {"schema": b.SCHEMA, "place": {}, "name": "Dhaka",
                      "timezone": "Asia/Dhaka", "fetchedAt": 1})
        next_morning = self.now + dt.timedelta(days=1)
        r = b.cached_report(self.cfg, next_morning)
        self.assertEqual(r["date"], "2026-11-25")
        self.assertTrue(r["offline"])

    def test_no_cross_configuration_cache_fallback(self):
        b.write_cache(b.state_key(self.cfg), {"schema": b.SCHEMA, "place": {}, "name": "Dhaka",
                      "timezone": "Asia/Dhaka", "fetchedAt": 1})
        other = dict(self.cfg, city="London")
        with self.assertRaises(ValueError):
            b.cached_report(other, self.now)

    def test_request_host_allowlist(self):
        for url in ("http://api.aladhan.com/v1", "https://evil.invalid/", "file:///etc/passwd"):
            with self.assertRaises(ValueError):
                b.fetch_json(url)

    def test_cli_bad_settings_is_structured_json(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "fetch.py"), "--config", "[]"],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["error"], "settings")
        self.assertEqual(result.stderr, "")

    def test_contract_fixture(self):
        output = os.environ.get("PRAYER_TEST_REPORT")
        if output:
            Path(output).write_text(json.dumps(self.report()))


if __name__ == "__main__":
    unittest.main()
