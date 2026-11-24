# Prayer Times for Omarchy

An optional Quickshell bar widget for daily Islamic prayers and fasting. The bar shows the time until the next prayer; the popup brings together today's five prayer windows, today's and tomorrow's fasting boundaries, sunrise, and sunset. The date uses **DD MMM YYYY** in the selected location's timezone.

## Install

Requires Omarchy 4.5 with the Quattro bar, Python 3.11+, and system timezone data (`tzdata`). No pip packages, API key, elevated permissions, or changes to stock Omarchy files are required.

Review the source before enabling this plugin. Omarchy plugins run with your user permissions, not in a sandbox. Install using Omarchy's normal confirmation and placement prompts:

```sh
omarchy plugin add https://github.com/smmmsmo/omarchy-prayer-times.git --enable
```

Click the mosque icon, open **Settings**, and choose an approximate IP location, a city and country (plus an optional state/region), or exact decimal coordinates. Choose **Apply settings**, then **Refresh** to fetch the timetable. For less location sharing, use a city instead of exact coordinates or IP lookup. **Automatic fetching** is off for new installations. Right-click the widget for Settings; middle-click to refresh. Move it with `omarchy bar move mo.prayer`.

**Upgrading from `mo.namaz` (1.1.2 or earlier):** Omarchy treats the new ID as a separate plugin. Note your current widget settings, remove the old copy with `omarchy plugin remove mo.namaz`, and then run the install command above. Reapply any settings you want to keep. Don't use `omarchy plugin update mo.namaz` to switch IDs.

## Update or remove

```sh
omarchy plugin update mo.prayer  # Update a Git-managed install
omarchy plugin disable mo.prayer # Hide it without uninstalling
omarchy plugin remove mo.prayer  # Disable and uninstall via Omarchy's confirmation prompt
```

After removal, Omarchy leaves separately stored timetable data alone. To erase this plugin's cache too, inspect and confirm removal of the dedicated cache directory:

```sh
rm -ri -- "${XDG_CACHE_HOME:-$HOME/.cache}/omarchy/namaz"
```

These commands do not remove unrelated bar widgets or Omarchy settings.

## Calculation options

- AlAdhan's location-based recommendation or one of 23 named methods, including Karachi, ISNA, MWL, Umm al-Qura, Moonsighting Committee, Tehran and Jaʿfari.
- Standard or Hanafi Asr, four high-latitude options, and Moonsighting Committee twilight selection.
- Per-prayer offsets from −30 to +30 minutes. Use only to match a trusted local timetable.
- Isha end at the midpoint from sunset to next Fajr, or at next Fajr as an outer limit.
- 12-hour and 24-hour time, live locale formatting, and English, Bengali, and Arabic UI catalogs. Other languages fall back to English.

Dates, DST, and rollover use the chosen location rather than the computer's timezone. The timetable distinguishes Fajr (suhoor cutoff) from sunrise, and Maghrib (iftar) from astronomical sunset. These are calculated boundaries, **not mosque congregation times or religious rulings**. The end column does not reflect every school's jurisprudence; verify with a local mosque or prayer authority, especially during Ramadan. Polar-day/night gaps are shown as `—`, not substituted with guessed fasting times.

## Privacy and reliability

No analytics, telemetry, accounts, background service, or API key. The plugin does not request GPS access. Only two fixed HTTPS services are used: `geo.omarchy.org` in IP mode, which sees the request's IP and returns an approximate location, and `api.aladhan.com` for timings. Each request exposes its source IP to the destination; AlAdhan also receives the selected city/region/country or coordinates and calculation settings, but not the optional location label or local offsets. IP mode rounds the returned coordinates before sending them to AlAdhan. City and coordinate modes skip the IP lookup entirely.

With automatic fetching enabled, an internal check runs every 15 minutes; cached daily schedules are reused and IP location is reused for up to an hour. Settings, startup, and the location's midnight can also trigger checks. **Refresh** bypasses today's and tomorrow's timetable cache. With automatic fetching off, background checks are cache-only.

Location and calculation preferences are saved only when you choose **Apply settings**, in the widget's entry in Omarchy's local `shell.json`. The helper receives settings via standard input rather than command-line arguments. Don't commit or share your personal `shell.json` without reviewing it first.

The local cache under `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy/namaz/v2` keeps validated times, timezone, method, and (in IP mode only) the approximate location needed to reuse those times. New entries omit raw provider metadata and do not duplicate a manually entered location. Cache files are written privately and atomically. Entries older than seven days are ignored and pruned during online refresh; you can delete the cache at any time using the removal steps. A future day is prefetched so the timetable can roll over offline. Cached times are labeled and only shown for the matching location, settings, and date.

## Development

```sh
./test/all
```

Tests need Python, timezone data, and Node.js, and run without network access. Omarchy's manifest validator also runs when installed. The CI workflow exercises supported Python versions. See [submission notes](SUBMISSION.md) for the marketplace handoff and manual UI checks.
