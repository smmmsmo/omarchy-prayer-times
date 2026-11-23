"""AlAdhan adapter for Omarchy Prayer Times (Python 3.11+, standard library)."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import tempfile
import time
import unicodedata
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA = 2
MAX_BYTES = 131072
METHODS = {0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}
PRAYERS = ("Fajr", "Dhuhr", "Asr", "Maghrib", "Isha")
KEYS = ("Fajr", "Sunrise", "Dhuhr", "Asr", "Sunset", "Maghrib", "Isha")
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "omarchy/namaz/v2"
EXPECTED = (ValueError, KeyError, TypeError, OverflowError, ZoneInfoNotFoundError)


class DataError(ValueError):
    """A stable, translatable error code; never remote text."""


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        before, after = urlsplit(req.full_url), urlsplit(newurl)
        if after.scheme != "https" or after.netloc != before.netloc:
            raise DataError("network")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_json(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in ("geo.omarchy.org", "api.aladhan.com"):
        raise DataError("network")
    with build_opener(SafeRedirect()).open(url, timeout=8) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise DataError("response")
    return json.loads(raw)


def clean(value, limit=100):
    if not isinstance(value, str) or len(value) > limit:
        raise DataError("settings")
    # Do not let controls or bidi overrides spoof a location label.
    return "".join(c for c in value.strip() if not unicodedata.category(c).startswith("C"))


def integer(value, allowed):
    if isinstance(value, bool) or not re.fullmatch(r"-?\d+", str(value)):
        raise DataError("settings")
    value = int(value)
    if value not in allowed:
        raise DataError("settings")
    return value


def coordinate(value, limit):
    if value is None or isinstance(value, bool) or value == "":
        raise DataError("coordinates")
    number = float(value)
    if not math.isfinite(number) or abs(number) > limit:
        raise DataError("coordinates")
    return number


def config(raw):
    if not isinstance(raw, dict):
        raise DataError("settings")
    mode = raw.get("locationMode", "auto")
    method = raw.get("method", "auto")
    method = "auto" if method == "auto" else integer(method, METHODS)
    school = integer(raw.get("school", 0), {0, 1})
    end = raw.get("ishaEnd", "midnight")
    high = integer(raw.get("highLatitude", 3), {0, 1, 2, 3})
    shafaq = raw.get("shafaq", "general")
    if mode not in ("auto", "manual", "coordinates") or end not in ("midnight", "fajr"):
        raise DataError("settings")
    if shafaq not in ("general", "ahmer", "abyad"):
        raise DataError("settings")
    result = dict(locationMode=mode, method=method, school=school, ishaEnd=end,
                  highLatitude=high, shafaq=shafaq)
    if mode == "manual":
        result.update(city=clean(raw.get("city", "")), country=clean(raw.get("country", "")),
                      state=clean(raw.get("state", "")))
        if not result["city"] or not result["country"]:
            raise DataError("location")
    elif mode == "coordinates":
        result.update(latitude=coordinate(raw.get("latitude"), 90),
                      longitude=coordinate(raw.get("longitude"), 180),
                      locationName=clean(raw.get("locationName", "")))
    offsets = raw.get("offsets", {})
    if not isinstance(offsets, dict) or any(k not in PRAYERS for k in offsets):
        raise DataError("settings")
    result["offsets"] = {k: integer(offsets.get(k, 0), range(-30, 31)) for k in PRAYERS}
    return result


def read_cache(name):
    try:
        with (CACHE / (name + ".json")).open("rb") as source:
            raw = source.read(MAX_BYTES + 1)
        return json.loads(raw) if len(raw) <= MAX_BYTES else None
    except (OSError, ValueError):
        return None


def write_cache(name, data):
    """A full disk or unwritable cache must not hide successfully fetched times."""
    path = None
    try:
        CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, path = tempfile.mkstemp(dir=CACHE, prefix=".prayer-")
        with os.fdopen(fd, "w") as out:
            json.dump(data, out, ensure_ascii=False, allow_nan=False)
        os.replace(path, CACHE / (name + ".json"))
        return True
    except OSError:
        return False
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def prune_cache():
    try:
        paths = sorted((p for p in CACHE.glob("*.json")
                        if re.fullmatch(r"(?:state-)?[a-f0-9]{24}\.json|location\.json", p.name)),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for path in paths[192:]:
            path.unlink(missing_ok=True)
    except OSError:
        pass


def coordinates(raw):
    return {"latitude": coordinate(raw["latitude"], 90),
            "longitude": coordinate(raw["longitude"], 180),
            "name": clean(raw.get("name", ""))}


def location(force=False):
    saved = read_cache("location")
    try:
        if not force and 0 <= time.time() - saved["fetched"] < 3600:
            return coordinates(saved["location"])
    except EXPECTED:
        pass
    result = coordinates(fetch_json("https://geo.omarchy.org/"))
    write_cache("location", {"fetched": time.time(), "location": result})
    return result


def parse_day(raw, expected):
    if not isinstance(raw, dict) or raw.get("code") != 200:
        raise DataError("response")
    data = raw["data"]
    if data["date"]["gregorian"]["date"] != expected.strftime("%d-%m-%Y"):
        raise DataError("response")
    zone = clean(data["meta"]["timezone"], 80)
    tz = ZoneInfo(zone)
    method = integer(data["meta"]["method"]["id"], METHODS)
    times = {}
    for key in KEYS:
        value = data["timings"].get(key)
        if value in (None, "", "-", "-----"):
            times[key] = None
            continue
        if not isinstance(value, str) or len(value) > 40:
            raise DataError("response")
        moment = dt.datetime.fromisoformat(value)
        if moment.tzinfo is None or abs((moment.date() - expected).days) > 1:
            raise DataError("response")
        if moment.utcoffset() != moment.astimezone(tz).utcoffset():
            raise DataError("response")
        times[key] = int(moment.timestamp())
    # A repeated sunrise/sunset is a polar-day/night placeholder, not a
    # usable solar event. An early civil-clock sunset can also be real: in
    # Reykjavík the service sometimes labels after-midnight times with the
    # same date as the preceding Asr, even in ISO mode.
    rise, setting = times["Sunrise"], times["Sunset"]
    if (rise is not None and setting is not None and setting < rise
            and dt.datetime.fromtimestamp(setting, tz).hour < 6):
        for key, previous in (("Sunset", "Asr"), ("Maghrib", "Sunset"), ("Isha", "Maghrib")):
            value, before = times[key], times[previous]
            if value is None or before is None or value >= before:
                continue
            local = dt.datetime.fromtimestamp(value, tz)
            corrected = int((local + dt.timedelta(days=1)).timestamp())
            if local.date() != expected or local.hour >= 6 or not 0 <= corrected - before <= 12 * 3600:
                raise DataError("response")
            times[key] = corrected
        setting = times["Sunset"]
    polar = rise is None or setting is None or rise >= setting
    if (rise is None and setting is None) or (rise is not None and setting is not None and rise >= setting):
        for key in ("Fajr", "Sunrise", "Sunset", "Maghrib", "Isha"):
            times[key] = None
    if not polar:
        # Keep the provider's explicit dates, including previous-day Fajr or
        # next-day Isha. Never guess a calendar day from HH:mm.
        for left, right in zip(KEYS, KEYS[1:]):
            if times[left] is not None and times[right] is not None:
                if times[left] > times[right] or (left != "Sunset" and times[left] == times[right]):
                    raise DataError("response")
    if all(value is None for value in times.values()):
        raise DataError("solar")
    missing = any(times[k] is None for k in ("Fajr", "Sunrise", "Sunset", "Maghrib", "Isha"))
    return {"date": expected.isoformat(), "timezone": zone, "times": times, "method": method, "polar": polar or missing}


def day_url(cfg, place, date):
    query = {"school": cfg["school"], "iso8601": "true",
             "latitudeAdjustmentMethod": cfg["highLatitude"], "shafaq": cfg["shafaq"]}
    if cfg["method"] != "auto":
        query["method"] = cfg["method"]
    if cfg["locationMode"] == "manual":
        endpoint = "timingsByCity"
        query.update(city=cfg["city"], country=cfg["country"])
        if cfg["state"]:
            query["state"] = cfg["state"]
    else:
        endpoint = "timings"
        query.update(latitude=place["latitude"], longitude=place["longitude"])
    return f"https://api.aladhan.com/v1/{endpoint}/{date:%d-%m-%Y}?" + urlencode(query)


def get_day(cfg, place, date, force=False, offline=False):
    url = day_url(cfg, place, date)
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    raw = read_cache(key)
    if raw is not None and not force:
        try:
            return parse_day(raw, date)
        except EXPECTED:
            pass
    if offline:
        raise DataError("offline")
    raw = fetch_json(url)
    result = parse_day(raw, date)
    if cfg["method"] != "auto" and result["method"] != cfg["method"]:
        raise DataError("response")
    write_cache(key, raw)
    return result


def make_report(cfg, days, place_name, now=None):
    today, following = days[0], days[1]
    tz = ZoneInfo(today["timezone"])
    now = now or dt.datetime.now(tz)
    base = dt.date.fromisoformat(today["date"])
    if base != now.astimezone(tz).date() or following["date"] != (base + dt.timedelta(days=1)).isoformat():
        raise DataError("offline")
    if following["timezone"] != today["timezone"]:
        raise DataError("response")

    def adjusted(day):
        result = dict(day["times"])
        for key in PRAYERS:
            if result[key] is not None:
                result[key] += cfg["offsets"][key] * 60
        return result

    t, tomorrow = adjusted(today), adjusted(following)
    end = tomorrow["Fajr"]
    if cfg["ishaEnd"] == "midnight":
        end = (t["Sunset"] + end) // 2 if t["Sunset"] is not None and end is not None else None
    rows = []
    warnings = []
    for key, limit in (("Fajr", t["Sunrise"]), ("Dhuhr", t["Asr"]), ("Asr", t["Sunset"]),
                       ("Maghrib", t["Isha"]), ("Isha", end)):
        if t[key] is None or limit is None or limit <= t[key]:
            limit = None
            if not today["polar"]:
                warnings.append("window")
        rows.append({"name": key, "start": t[key], "end": limit})
    if today["polar"] or following["polar"]:
        warnings.append("solar")
    events = sorted([{"name": key, "start": day[key]} for day in (t, tomorrow) for key in PRAYERS
                     if day[key] is not None], key=lambda event: event["start"])
    iftar = t["Maghrib"]
    tomorrow_iftar = tomorrow["Maghrib"]
    if iftar is not None and t["Sunset"] is not None and iftar < t["Sunset"]:
        iftar = None
        warnings.append("window")
    if tomorrow_iftar is not None and tomorrow["Sunset"] is not None and tomorrow_iftar < tomorrow["Sunset"]:
        tomorrow_iftar = None
        warnings.append("window")
    report = {
        "schema": SCHEMA, "ok": True, "date": base.isoformat(), "timezone": today["timezone"],
        "location": place_name, "rows": rows, "events": events,
        "sunrise": t["Sunrise"], "sunset": t["Sunset"], "sehri": t["Fajr"], "iftar": iftar,
        "tomorrowSehri": tomorrow["Fajr"], "tomorrowIftar": tomorrow_iftar,
        "method": today["method"], "school": cfg["school"], "ishaEnd": cfg["ishaEnd"],
        "highLatitude": cfg["highLatitude"], "warnings": sorted(set(warnings)), "offline": False,
        "validFrom": int(dt.datetime.combine(base, dt.time(), tzinfo=tz).timestamp()),
        "validUntil": int(dt.datetime.combine(base + dt.timedelta(days=1), dt.time(), tzinfo=tz).timestamp()),
        "clock": {},
    }
    epochs = [v for day in (t, tomorrow) for v in day.values() if v is not None]
    epochs += [row["end"] for row in rows if row["end"] is not None]
    for epoch in epochs:
        local = dt.datetime.fromtimestamp(epoch, tz)
        report["clock"][str(epoch)] = {"h": local.hour, "m": local.minute, "day": (local.date() - base).days}
    return report


def state_key(cfg):
    return "state-" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:24]


def cached_report(cfg, now=None):
    state = read_cache(state_key(cfg))
    if not isinstance(state, dict) or state.get("schema") != SCHEMA:
        raise DataError("offline")
    tz = ZoneInfo(state["timezone"])
    date = (now or dt.datetime.now(tz)).astimezone(tz).date()
    place = coordinates(state["place"]) if cfg["locationMode"] != "manual" else {}
    days = [get_day(cfg, place, date + dt.timedelta(days=i), offline=True) for i in (0, 1)]
    result = make_report(cfg, days, clean(state["name"], 304), now)
    result.update(offline=True, fetchedAt=state["fetchedAt"])
    return result


def run(cfg, force=False, offline=False):
    failure = "offline"
    if not offline:
        try:
            if cfg["locationMode"] == "auto":
                place = location(force)
            elif cfg["locationMode"] == "coordinates":
                place = {"latitude": cfg["latitude"], "longitude": cfg["longitude"], "name": cfg["locationName"]}
            else:
                place = {}
            name = (", ".join(filter(None, (cfg["city"], cfg["state"], cfg["country"])))
                    if cfg["locationMode"] == "manual" else place["name"]
                    or f'{place["latitude"]:.4f}, {place["longitude"]:.4f}')
            # One probe learns the destination timezone. No computer timezone or
            # DST assumptions enter the selected-place date calculation.
            probe = get_day(cfg, place, dt.datetime.now(dt.timezone.utc).date(), force)
            date = dt.datetime.now(ZoneInfo(probe["timezone"])).date()
            days = [probe if probe["date"] == (date + dt.timedelta(days=i)).isoformat()
                    else get_day(cfg, place, date + dt.timedelta(days=i), force) for i in (0, 1)]
            result = make_report(cfg, days, name)
            state = {"schema": SCHEMA, "place": place, "name": name,
                     "timezone": result["timezone"], "fetchedAt": int(time.time())}
            result["fetchedAt"] = state["fetchedAt"]
            result["cacheWritable"] = write_cache(state_key(cfg), state)
            # Prefetch the second following day so a cached session can roll
            # over midnight offline with tomorrow's fasting boundaries intact.
            try:
                get_day(cfg, place, date + dt.timedelta(days=2))
            except (OSError, URLError, *EXPECTED):
                pass
            prune_cache()
            return result
        except DataError as error:
            failure = str(error)
        except (OSError, URLError, *EXPECTED):
            failure = "network"
    try:
        result = cached_report(cfg)
        result["error"] = failure
        return result
    except (OSError, *EXPECTED):
        return {"schema": SCHEMA, "ok": False, "error": failure}


def timed_out(signum, frame):
    raise TimeoutError("Prayer fetch deadline exceeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="JSON settings, not a path")
    parser.add_argument("--force", action="store_true", help="Bypass network caches")
    parser.add_argument("--offline", action="store_true", help="Never access the network")
    args = parser.parse_args()
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(40)  # Bound slow reads AND contention between monitor instances.
    lock = None
    try:
        cfg = config(json.loads(args.config))
        try:
            CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
            lock = (CACHE / ".fetch.lock").open("a")
            fcntl.flock(lock, fcntl.LOCK_EX)
        except OSError:
            pass
        result = run(cfg, args.force, args.offline)
    except TimeoutError:
        try:
            result = cached_report(cfg)
        except (UnboundLocalError, *EXPECTED):
            result = {"schema": SCHEMA, "ok": False, "error": "network"}
    except EXPECTED:
        result = {"schema": SCHEMA, "ok": False, "error": "settings"}
    finally:
        if lock:
            lock.close()
        signal.alarm(0)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
