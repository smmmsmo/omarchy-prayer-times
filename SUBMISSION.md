# Omarchy submission notes

## Suggested title

Optional Prayer Times plugin for Omarchy

## Suggested description

Prayer Times adds an optional bar widget for the five daily Islamic prayer windows, a next-prayer countdown, suhoor and iftar, and sunrise and sunset. It follows the shell theme, formats dates as `DD MMM YYYY`, and supports automatic IP, manual city and exact-coordinate locations. Calculation methods, Asr, high-latitude handling, Isha end and local offsets are configurable. Network access is opt-in for new users. The widget does not replace or change the default bar layout.

The plugin uses the existing bar-widget manifest and UI kit; no changes to Omarchy core are needed to install it. `mo.namaz` is stable for existing installs. To discuss first-party inclusion, start in [Omarchy Suggestions](https://github.com/omacom/omarchy/discussions/categories/suggestions). If maintainers ask for a first-party PR, adapt the plugin to the current `quattro` branch and follow its `AGENTS.md` and shell-development guide. In particular, confirm the desired namespace, network/backend policy, visual assets, test placement, and translation review before opening the PR.

## Reviewer checklist

- Run `./test/all` and `omarchy plugin validate .`.
- Test that a new install makes no network requests until Refresh or automatic fetching is enabled.
- Open the card on a horizontal and vertical bar; confirm the mosque icon is legible at both sizes and uses theme foreground.
- Switch between IP, city and coordinates. Confirm Apply persists and Cancel leaves settings unchanged.
- Verify a remote location whose civil date differs from the computer's. Verify a date with a single-digit day renders `05 Jan 2027`.
- Try a DST boundary and a high-latitude summer timetable; confirm missing events do not produce a fasting time.
- Switch to Arabic and verify label/layout mirroring; switch to Bengali and confirm digits and translated labels.
- Review calculated time disclaimers and API disclosure; confirm no default bar entry will be installed upstream.

Publishing the standalone plugin on GitHub does not submit it to Omarchy upstream.
