# Development guide

For the file map and invariants, start with [AGENTS.md](../AGENTS.md). The [README](../README.md) is the user-facing reference; [SUBMISSION.md](../SUBMISSION.md) covers marketplace review.

## How a timetable reaches the bar

1. **The shell hosts the widget.** Omarchy loads `BarWidget.qml` from `manifest.json` and supplies the widget's settings. `PrayerSettings.qml` edits a draft; only **Apply settings** persists it in the bar layout entry.
2. **The widget chooses the fetch mode.** `BarWidget.qml` starts `python3 -B fetch.py`, passing settings on stdin. With automatic fetching off it uses `--offline` for background checks. **Refresh** uses `--force`. A result for superseded settings is ignored.
3. **The helper resolves and validates schedules.** `fetch.py` fetches or reuses provider schedules, resolves the location's timezone, builds prayer windows and fasting boundaries, and emits a schema-2 report. Today's and tomorrow's schedules supply the next-prayer countdown and fasting preview. The extra prefetched day helps preserve tomorrow's preview after offline midnight rollover.
4. **The UI renders the validated report.** `Model.js` checks the report shape, selects the first future event from the sorted schedule, and formats the supplied local clock values. `BarWidget.qml` checks the report's validity window and `PrayerTimetable.qml` displays windows, cache status, and unavailable events.

## Automated checks

From the repository root:

```sh
./test/all
```

The runner executes the Python tests, then passes a Python-generated report to the Node.js tests to check the backend/frontend contract. Provider responses are mocked. CI tests Python 3.11–3.13 with Node.js 22. If an Omarchy install is available, the runner also checks `manifest.json` with `omarchy plugin validate`.

## Manual checks on Quattro

Use a disposable session or test profile with the current checkout, not a personal install. In that session, `omarchy shell mo.prayer status` reports whether the widget is open, ready, or loading, plus its displayed date and error code. It does not report the configured location.

| Area | Verify |
| --- | --- |
| First run and refresh | Start with an empty cache. No requests should occur until **Refresh** or **Automatic fetching** is enabled. Middle-click should behave like **Refresh**. Restart with automatic fetching off and a matching cache; the cached label should appear. |
| Settings | Try IP, manual city, and coordinates. **Apply settings** persists, **Cancel** discards edits, and the 12/24-hour clock changes without fetching. Use sample locations, not private coordinates, for any online check. |
| Layout and input | Open from a horizontal and a vertical bar. Check the icon, horizontal countdown, right-click settings, keyboard access, and Escape. The popup should scroll on a short display without hiding controls permanently. |
| Time and missing events | Use a location whose date differs from the desktop's. Check a single-digit day (`05 Jan 2027` in English), a DST transition, and a high-latitude schedule with missing events. Unavailable times must render as `—`, not guessed fasting times. |
| Locales and theme | Switch between English, Bengali, and Arabic without restarting. Check digits, text fit, and Arabic mirroring. Confirm the popup and bar icon use the active theme. |

## Refreshing the screenshots

The gallery uses real captures of the Quattro bar and popup with sample data, not mockups. Keep the primary screenshot at [`preview.png`](../preview.png) and other views in [`docs/screenshots/`](screenshots/).

1. Load the current checkout in a disposable desktop or private compositor. Use an isolated cache and a public example city; keep automatic fetching off. For a fully offline capture, the `test_offline_midnight_rollover` test in [`tests/test_backend.py`](../tests/test_backend.py) shows how the helper seeds and reuses cached sample days.
2. Capture the full timetable including the bar countdown, then open **Settings** and capture the **Location** and **Calculation** tabs. On an Omarchy desktop, `omarchy capture screenshot region save` can save just the selected region.
3. Crop to the relevant UI and strip image metadata before committing. Check that text is readable, that the screenshots share a theme and location, and that no notifications, personal desktop content, or private settings are visible.
4. Update the [README gallery](../README.md#screenshots) and its alt text if a view or filename changes. Label sample timings as examples, not a live timetable.
