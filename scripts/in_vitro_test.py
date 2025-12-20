"""In-vitro parser test using the ble_monitor PR #804 test vector.

This is intentionally a small, dependency-free script that can be run locally:
  python scripts/in_vitro_test.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PARSER_PATH = (
    _REPO_ROOT / "custom_components" / "laica_smart_scale" / "laica_parser.py"
)

spec = importlib.util.spec_from_file_location(
    "laica_smart_scale_laica_parser", _PARSER_PATH
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load parser module from {_PARSER_PATH}")

_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = _module
spec.loader.exec_module(_module)

parse_laica_manufacturer_data = _module.parse_laica_manufacturer_data


def _extract_laica_payload_from_hci_event(hci_event: bytes) -> bytes:
    """Extract the manufacturer payload bytes from the ble_monitor-style HCI event.

    The PR #804 test vector contains the manufacturer AD structure:
      0f ff ac a0 <12 bytes payload>
    """

    marker = bytes.fromhex("0fffaca0")
    idx = hci_event.find(marker)
    if idx == -1:
        raise ValueError(
            "Manufacturer AD structure (0f ff ac a0) not found in test vector"
        )

    payload_start = idx + len(marker)
    payload_len = 12
    payload = hci_event[payload_start : payload_start + payload_len]
    if len(payload) != payload_len:
        raise ValueError(
            "Test vector truncated; could not read full manufacturer payload"
        )

    return payload


def main() -> None:
    data_string = (
        "043e2b02010300a02bbe5e91a01f0201040303b0ff0fffaca0a02bbe5e91a0"
        "a02c92140dbf0709414141303032d9"
    )
    hci_event = bytes.fromhex(data_string)
    payload = _extract_laica_payload_from_hci_event(hci_event)

    report = parse_laica_manufacturer_data(payload)

    print("payload_hex:", payload.hex())
    print("candidate_type_offsets:", report.candidate_type_offsets)
    print("parsed:", report.parsed)
    print("attempts:", report.attempts)

    assert report.parsed is not None, "Expected successful parse"
    assert report.parsed.kind == "weight"
    assert report.parsed.weight_kg == 13.0


if __name__ == "__main__":
    main()
