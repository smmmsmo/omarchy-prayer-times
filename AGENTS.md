# Working on Prayer Times

This is `mo.prayer`, an optional bar widget for Omarchy 4.5's Quattro shell. It is not a standalone app or part of Omarchy core. The runtime is QML/JavaScript plus Python 3.11+ and system `tzdata`; Node.js is only for tests.

## Where to start

| If you are changing… | Start here |
| --- | --- |
| Plugin metadata, entry point, or defaults | `manifest.json`, then `BarWidget.qml` |
| Bar icon, countdown, panel lifecycle, or refresh orchestration | `BarWidget.qml`, `PrayerIcon.qml` |
| Timetable or settings layout | `PrayerTimetable.qml`, `PrayerSettings.qml`, `SectionCard.qml`, `PlainLabel.qml` |
| Time formatting, settings projection, or report validation | `Model.js`, `tests/test_model.cjs` |
| Provider requests, cache, timezone handling, or prayer windows | `fetch.py`, `tests/test_backend.py` |
| UI text | `i18n/en.json`, `i18n/bn.json`, `i18n/ar.json` |
| Screenshots, user docs, or marketplace handoff | `preview.png`, `docs/screenshots/`, `README.md`, `SUBMISSION.md` |

## Contracts to preserve

- `BarWidget.qml` passes a settings JSON line to `fetch.py` on stdin. The helper emits one schema-2 JSON report; `Model.js` validates it before the UI uses it. Update both sides and the contract test if the report changes.
- Keep defaults aligned across the manifest, `Model.requestSettings()` and `fetch.config()` for the settings each layer owns. `hour24` is display-only. `mo.prayer` is the installed ID; `mo.namaz` is the legacy ID, and `omarchy/namaz/v2` remains the cache path.
- Keep automatic fetching off by default. Startup and background checks must stay cache-only unless opted in. Keep HTTPS requests bounded and restricted to the documented hosts; never put private settings on argv or add personal locations, cache files, or a real `shell.json` to fixtures or screenshots.
- Use the selected location's civil date and timezone, not the computer's. Missing boundaries stay `null` and display as `—`; never invent a time or present a calculation as a religious ruling.
- Use the shell's `qs.Commons` and `qs.Ui` for styling and controls. Render untrusted text with `PlainLabel.qml` or an explicitly plain-text sink. For a shared control that cannot enforce plain text, neutralize markup first and add regression coverage. Keep translatable strings whole and preserve `%1`-style placeholders.

## Before handing off

1. Run `./test/all`. It needs Python, `tzdata`, and Node.js; it does not contact the live APIs. It also runs `omarchy plugin validate` if available.
2. For UI changes, follow the [manual checks and screenshot guide](docs/development.md). State which checks you could not run. The offline suite does not exercise QML rendering.
3. For settings or network behavior changes, update the [user docs](README.md) alongside the tests. Do not edit the user's installed Omarchy config or publish changes unless asked.
