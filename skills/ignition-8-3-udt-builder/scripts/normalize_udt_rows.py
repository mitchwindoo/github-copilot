#!/usr/bin/env python3
"""Normalize API-read UDT rows without hiding coercion or quality failures."""

import argparse
import json
from pathlib import Path


def cell_value(row, key):
    cell = row.get(key)
    return cell.get("value") if isinstance(cell, dict) else cell


def cell_quality(row, key):
    cell = row.get(key)
    return cell.get("quality") if isinstance(cell, dict) else None


def normalize_int(value, field, warnings, errors):
    if isinstance(value, bool):
        errors.append(f"{field}: Boolean is not an integer")
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            normalized = int(value.strip())
        except ValueError:
            errors.append(f"{field}: cannot normalize {value!r} to integer")
            return None
        warnings.append(f"{field}: coerced string {value!r} to integer")
        return normalized
    errors.append(f"{field}: expected integer, received {type(value).__name__}")
    return None


def normalize_float(value, field, warnings, errors):
    if value is None:
        warnings.append(f"{field}: null value retained")
        return None
    if isinstance(value, bool):
        errors.append(f"{field}: Boolean is not a number")
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            normalized = float(value.strip())
        except ValueError:
            errors.append(f"{field}: cannot normalize {value!r} to number")
            return None
        warnings.append(f"{field}: coerced string {value!r} to number")
        return normalized
    errors.append(f"{field}: expected number, received {type(value).__name__}")
    return None


def normalize_bool(value, field, warnings, errors):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        warnings.append(f"{field}: coerced integer {value} to Boolean")
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in ("true", "false", "0", "1"):
        normalized = value.strip().lower() in ("true", "1")
        warnings.append(f"{field}: coerced string {value!r} to Boolean")
        return normalized
    errors.append(f"{field}: cannot normalize {value!r} to Boolean")
    return None


def normalize_row(row):
    warnings = []
    errors = []
    normalized = {
        "tagPath": row.get("tagPath"),
        "typeId": row.get("typeId"),
    }
    for field in (
        "AssetName", "DisplayName", "Area", "EquipmentType", "Variant",
        "DetailViewKey", "Units", "Status"
    ):
        value = cell_value(row, field)
        if value is None:
            errors.append(f"{field}: missing or null")
        elif not isinstance(value, str):
            warnings.append(f"{field}: stringified {type(value).__name__}")
            value = str(value)
        normalized[field] = value
    normalized["SortOrder"] = normalize_int(cell_value(row, "SortOrder"), "SortOrder", warnings, errors)
    normalized["PV"] = normalize_float(cell_value(row, "PV"), "PV", warnings, errors)
    normalized["Running"] = normalize_bool(cell_value(row, "Running"), "Running", warnings, errors)
    normalized["Attention"] = normalize_bool(cell_value(row, "Attention"), "Attention", warnings, errors)
    qualities = {}
    for field in ("PV", "Status", "Running", "Attention"):
        quality = cell_quality(row, field)
        qualities[field] = quality
        if quality is not None and not quality.startswith("Good"):
            errors.append(f"{field}: quality is {quality}")
    normalized["qualities"] = qualities
    normalized["warnings"] = warnings
    normalized["errors"] = errors
    normalized["valid"] = not errors
    normalized["raw"] = row
    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rows", type=Path)
    args = parser.parse_args()
    with args.rows.open("r", encoding="utf-8-sig") as stream:
        rows = json.load(stream)
    if not isinstance(rows, list):
        raise SystemExit("input must be a JSON array")
    normalized = [normalize_row(row) for row in rows]
    asset_counts = {}
    for row in normalized:
        asset = row.get("AssetName")
        asset_counts[asset] = asset_counts.get(asset, 0) + 1
    duplicates = sorted(key for key, count in asset_counts.items() if key is not None and count > 1)
    for row in normalized:
        if row.get("AssetName") in duplicates:
            row["errors"].append(f"AssetName: duplicate {row['AssetName']!r}")
            row["valid"] = False
    normalized.sort(key=lambda row: (
        row["SortOrder"] is None,
        row["SortOrder"] if row["SortOrder"] is not None else 0,
        row.get("DisplayName") or "",
        row.get("tagPath") or "",
    ))
    print(json.dumps({
        "duplicateAssetNames": duplicates,
        "invalidCount": sum(not row["valid"] for row in normalized),
        "rowCount": len(normalized),
        "rows": normalized,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
