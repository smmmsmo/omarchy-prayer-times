# Omarchy submission notes

## Suggested title

Optional Prayer Times plugin for Omarchy

## Suggested description

Prayer Times adds an optional bar widget for the five daily Islamic prayer windows, a next-prayer countdown, suhoor and iftar, and sunrise and sunset. It follows the shell theme, formats dates as `DD MMM YYYY`, and supports automatic IP, manual city and exact-coordinate locations. Calculation methods, Asr, high-latitude handling, Isha end and local offsets are configurable. Network access is opt-in for new users. The widget does not replace or change the default bar layout.

The plugin uses the existing bar-widget manifest and UI kit; no changes to Omarchy core are needed to install it. The marketplace ID is `mo.prayer`; early copies using `mo.namaz` can migrate using the README instructions. To discuss first-party inclusion, start in [Omarchy Suggestions](https://github.com/omacom/omarchy/discussions/categories/suggestions). If maintainers ask for a first-party PR, adapt the plugin to the current `quattro` branch and follow its `AGENTS.md` and shell-development guide. In particular, confirm the desired namespace, network/backend policy, visual assets, test placement, and translation review before opening the PR.

## Reviewer checklist

- Run `./test/all` and `omarchy plugin validate .` on Omarchy.
- Follow the [Quattro manual checks](docs/development.md#manual-checks-on-quattro), including first-run network behavior, display and settings, timezone edge cases, and locale rendering.
- Check the [screenshots](README.md#screenshots), calculated-time disclaimers, and API disclosure. Confirm no default bar entry will be installed upstream.

Publishing the standalone plugin on GitHub does not submit it to Omarchy upstream.
