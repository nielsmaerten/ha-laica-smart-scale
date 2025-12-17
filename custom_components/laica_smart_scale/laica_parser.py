"""Best-effort parser for Laica Smart Scale manufacturer advertisements.

This is intentionally HA-agnostic so we can iterate quickly based on captured
payloads and unit-test it separately later.

Known facts (from ble_monitor PR #804):
- Manufacturer/company id: 0xA0AC
- Packet types observed: 0x0D (weight) and 0x06 (impedance)
- "Decrypt": XOR each byte with 0xA0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PACKET_TYPE_WEIGHT = 0x0D
PACKET_TYPE_IMPEDANCE = 0x06

KNOWN_TYPE_OFFSET = 10
KNOWN_VALUE_OFFSET = 6

WEIGHT_VALUE_MASK = 0x3FFFF
WEIGHT_STABLE_BIT = 0x80000000

def _decrypt_to_int(data: bytes) -> int:
    decrypted = bytes((b ^ 0xA0) for b in data)
    return int.from_bytes(decrypted, byteorder="big", signed=False)


@dataclass(frozen=True, slots=True)
class LaicaParsedPacket:
    kind: Literal["weight", "impedance"]
    type_byte_offset: int
    value_offset: int
    value_length: int
    weight_kg: float | None = None
    impedance_ohm: int | None = None
    is_stable: bool | None = None
    raw_flags: int | None = None
    raw_decrypted_int: int | None = None
    raw_decrypted_hex: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class LaicaParseReport:
    payload_hex: str
    payload_len: int
    candidate_type_offsets: tuple[int, ...]
    attempts: tuple[dict[str, Any], ...]
    parsed: LaicaParsedPacket | None


def _attempt_parse(
    payload: bytes,
    *,
    kind: Literal["weight", "impedance"],
    type_offset: int,
    value_offset: int,
    value_length: int,
    scheme: str,
) -> tuple[LaicaParsedPacket | None, dict[str, Any]]:
    pkt_type = payload[type_offset]

    attempt: dict[str, Any] = {
        "kind": kind,
        "type_offset": type_offset,
        "type_byte": f"0x{pkt_type:02x}",
        "value_offset": value_offset,
        "value_length": value_length,
        "scheme": scheme,
        "status": "rejected",
        "reason": None,
    }

    if value_offset < 0 or value_offset + value_length > len(payload):
        attempt["reason"] = "value_bytes_out_of_range"
        return None, attempt

    raw = _decrypt_to_int(payload[value_offset : value_offset + value_length])

    if kind == "weight":
        raw_masked = raw & WEIGHT_VALUE_MASK
        raw_flags = raw & ~WEIGHT_VALUE_MASK
        is_stable = bool(raw & WEIGHT_STABLE_BIT)
        weight_kg = round(raw_masked / 100) / 10
        attempt.update(
            {
                "raw_decrypted_int": raw,
                "raw_decrypted_hex": f"0x{raw:0{value_length * 2}x}",
                "raw_masked": raw_masked,
                "raw_flags": raw_flags,
                "is_stable": is_stable,
                "weight_kg": weight_kg,
            }
        )

        # Plausibility checks to avoid false positives when probing.
        if not (5 <= weight_kg <= 400):
            attempt["reason"] = "weight_out_of_range"
            return None, attempt

        attempt["status"] = "accepted"
        return (
            LaicaParsedPacket(
                kind="weight",
                type_byte_offset=type_offset,
                value_offset=value_offset,
                value_length=value_length,
                weight_kg=weight_kg,
                is_stable=is_stable,
                raw_flags=raw_flags,
                raw_decrypted_int=raw,
                raw_decrypted_hex=f"0x{raw:0{value_length * 2}x}",
                notes=f"raw_flags=0x{raw_flags:x}",
            ),
            attempt,
        )

    if kind == "impedance":
        impedance = int(raw)
        clamped = max(430, min(630, impedance))

        attempt.update(
            {
                "raw_decrypted_int": raw,
                "raw_decrypted_hex": f"0x{raw:0{value_length * 2}x}",
                "impedance_ohm_raw": impedance,
                "impedance_ohm": clamped,
                "clamped": clamped != impedance,
            }
        )

        # Plausibility checks.
        if not (200 <= impedance <= 1200):
            attempt["reason"] = "impedance_out_of_range"
            return None, attempt

        attempt["status"] = "accepted"
        notes = "clamped_to_[430,630]" if clamped != impedance else None
        return (
            LaicaParsedPacket(
                kind="impedance",
                type_byte_offset=type_offset,
                value_offset=value_offset,
                value_length=value_length,
                impedance_ohm=clamped,
                raw_decrypted_int=raw,
                raw_decrypted_hex=f"0x{raw:0{value_length * 2}x}",
                notes=notes,
            ),
            attempt,
        )

    attempt["reason"] = "unknown_kind"
    return None, attempt


def parse_laica_manufacturer_data(payload: bytes) -> LaicaParseReport:
    """Parse Laica manufacturer payload bytes (Bleak-style: company id excluded)."""

    candidate_offsets = tuple(
        idx for idx, b in enumerate(payload) if b in (PACKET_TYPE_IMPEDANCE, PACKET_TYPE_WEIGHT)
    )

    attempts: list[dict[str, Any]] = []
    parsed: LaicaParsedPacket | None = None

    # Known layout (validated against ble_monitor PR #804 test vector and live weight packets):
    # - payload length: 12 bytes
    # - type byte: payload[10] (unencrypted) in {0x0D, 0x06}
    # - encrypted value bytes: start at payload[6]
    if len(payload) <= KNOWN_TYPE_OFFSET:
        attempts.append(
            {
                "scheme": "known_layout",
                "status": "rejected",
                "reason": "payload_too_short",
                "payload_len": len(payload),
            }
        )
    else:
        pkt_type = payload[KNOWN_TYPE_OFFSET]
        attempts.append(
            {
                "scheme": "known_layout",
                "type_offset": KNOWN_TYPE_OFFSET,
                "type_byte": f"0x{pkt_type:02x}",
                "status": "rejected",
                "reason": None,
            }
        )
        if pkt_type == PACKET_TYPE_WEIGHT:
            parsed, attempt = _attempt_parse(
                payload,
                kind="weight",
                type_offset=KNOWN_TYPE_OFFSET,
                value_offset=KNOWN_VALUE_OFFSET,
                value_length=4,
                scheme="known_layout",
            )
            attempts[-1] = attempt
        elif pkt_type == PACKET_TYPE_IMPEDANCE:
            parsed, attempt = _attempt_parse(
                payload,
                kind="impedance",
                type_offset=KNOWN_TYPE_OFFSET,
                value_offset=KNOWN_VALUE_OFFSET,
                value_length=2,
                scheme="known_layout",
            )
            attempts[-1] = attempt
        else:
            attempts[-1]["reason"] = "unknown_type_byte_at_known_offset"

    return LaicaParseReport(
        payload_hex=payload.hex(),
        payload_len=len(payload),
        candidate_type_offsets=candidate_offsets,
        attempts=tuple(attempts),
        parsed=parsed,
    )
