# Project Rules: UrbanHello Rémi API Client

## 1. Project Context
Standalone async Python client library for the UrbanHello Rémi baby monitor's cloud API (Parse Server-based backend). Published independently to PyPI and intended to be consumed by [urbanhello_remi_hass](../urbanhello_remi_hass/), the Home Assistant integration for this device — not vendored into it.

## 2. Standards
@../.gemini/rules/shared_python_lib.md

## 3. Project-Specific Notes
- **Package name**: `urbanhello-remi-api` (import as `urbanhello_remi_api`)
- **Architecture**: `client.py` (`ParseClient`, low-level HTTP/auth) → `api.py` (`RemiAPI`, high-level façade) → `models.py` (typed dataclasses: `RemiDevice`, `Alarm`, `Face`)
- **License**: GPL-3.0-or-later (differs from `urbanhello_remi_hass`, which is MIT — do not assume shared licensing when moving code between the two)
