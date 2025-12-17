# Repository Guidelines

This repository contains a Home Assistant custom integration for a Laica Smart Scale, using passive BLE advertisements (no device pairing).

## Project Structure & Module Organization

- `custom_components/laica_smart_scale/`: the integration package
  - `manifest.json`: Home Assistant metadata (domain, dependencies, BLE matcher)
  - `__init__.py`: Bluetooth callback registration and entity update dispatching
  - `config_flow.py`: UI setup flow (Bluetooth discovery + manual address entry)
  - `sensor.py`: sensor entities (`weight`, `impedance`, `last_seen`)
  - `diagnostics.py`: diagnostics payload for support/debugging
  - `laica_parser.py`: HA-agnostic manufacturer payload parser (keep deterministic)
  - `translations/` and `strings.json`: UI strings
- `scripts/`: local helper scripts for parser verification (e.g. known test vectors)
- `reference/`: protocol notes / upstream diffs used during development

## Build, Test, and Development Commands

- `python scripts/in_vitro_test.py`: runs a dependency-free parser smoke test against a known BLE test vector.
- `python -m compileall custom_components/laica_smart_scale`: quick syntax check for the integration package.
- Manual Home Assistant test: copy `custom_components/laica_smart_scale` into your HA config at `config/custom_components/laica_smart_scale/`, restart Home Assistant, then add the integration via the UI.

## Coding Style & Naming Conventions

- Python: 4-space indentation, no tabs, keep type hints (`from __future__ import annotations` is used).
- Follow Home Assistant patterns: `async_*` entrypoints, `hass.data[DOMAIN]` for storage, dispatcher signals via `update_signal(...)`.
- Naming: `snake_case` for modules/functions, `UPPER_CASE` for constants, descriptive keys for stored measurements (see `DATA_LAST_*` in `const.py`).

## Testing Guidelines

- No full test framework is configured yet; prefer adding small, deterministic regression vectors under `scripts/` when evolving `laica_parser.py`.
- When reporting issues, include the diagnostics output and (redacted) manufacturer payload hex where possible.

## Commit & Pull Request Guidelines

- Git history is currently minimal; use short, imperative commit subjects (e.g., “Add impedance parsing”) and keep commits focused.
- PRs: include a clear description, steps to reproduce, example payload/log excerpts (redact MAC addresses), and screenshots for UI-facing changes.

## Security & Configuration Tips

- Treat BLE addresses and captured advertisements as sensitive; redact identifiers before sharing.
- Avoid committing artifacts (`__pycache__/`, logs, captures); `.gitignore` already excludes common ones.
