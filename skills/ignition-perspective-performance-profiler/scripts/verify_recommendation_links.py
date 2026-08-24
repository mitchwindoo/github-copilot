#!/usr/bin/env python3
"""Verify remediation recommendations link to observed findings and metrics.

This checker is offline and read-only. It validates a structured JSON report
or a Markdown report with an embedded JSON block. The expected shape is:

{
  "findings": [
    {"id": "F-001", "observed": true, "metrics": ["browser.longTaskTotalMs"]}
  ],
  "recommendations": [
    {
      "id": "REC-001",
      "findingRefs": ["F-001"],
      "expectedMetrics": [{"name": "browser.longTaskTotalMs", "direction": "decrease"}]
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


FINDING_LIST_KEYS = ("findings", "observedFindings", "observations", "issues")
RECOMMENDATION_LIST_KEYS = ("recommendations", "remediationCandidates", "candidateRecommendations", "candidates")
FINDING_ID_KEYS = ("id", "findingId", "key", "name")
RECOMMENDATION_ID_KEYS = ("id", "recommendationId", "key", "title")
REFERENCE_KEYS = ("findingRefs", "observedFindingRefs", "findingIds", "linkedFindings", "evidenceRefs", "findings")
METRIC_LIST_KEYS = ("expectedMetrics", "metricsExpectedToChange", "primaryMetrics", "targetMetrics")
SINGLE_METRIC_KEYS = ("expectedMetric", "expectedMetricName", "primaryMetric", "metric")
FINDING_METRIC_KEYS = ("metrics", "observedMetrics", "metricNames", "metric", "metricName")
METRIC_NAME_KEYS = ("name", "metric", "metricName", "id")
CHANGE_SPEC_KEYS = ("direction", "expectedChange", "change", "targetDirection", "threshold", "target", "expectedDelta", "minImprovementPercent")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def load_report(path: Path) -> Tuple[Optional[Any], List[str]]:
    errors: List[str] = []
    if path.is_dir():
        candidates = [
            path / "recommendation-report.json",
            path / "recommendations.json",
            path / "remediation-report.json",
            path / "report.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured recommendation report: {path}"]

    try:
        if path.suffix.lower() == ".md":
            return load_markdown_json(path)
        return read_json(path), []
    except Exception as exc:  # noqa: BLE001 - include exact parse failure
        errors.append(f"failed to load {path}: {type(exc).__name__}: {exc}")
    return None, errors


def load_markdown_json(path: Path) -> Tuple[Optional[Any], List[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    for block in blocks:
        try:
            data = json.loads(block)
        except Exception:
            continue
        if isinstance(data, dict) and any(key in data for key in RECOMMENDATION_LIST_KEYS):
            return data, []
    return None, [f"markdown report has no parseable JSON block with recommendations: {path}"]


def first_present(row: Dict[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def clean_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("findingId", "recommendationId", "id", "ref", "key", "name"):
            if value.get(key) is not None:
                return str(value.get(key)).strip()
        return ""
    return str(value).strip()


def normalize_metric_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def find_list(root: Dict[str, Any], keys: Sequence[str]) -> List[Dict[str, Any]]:
    for key in keys:
        value = root.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def truthy_observed(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"observed", "direct", "correlated", "causal", "true", "yes", "passed"}
    return False


def finding_observed(row: Dict[str, Any]) -> bool:
    for key in ("observed", "directlyObserved", "evidenceObserved"):
        if key in row:
            return truthy_observed(row.get(key))
    grade = first_present(row, ("evidenceGrade", "grade", "status"))
    return truthy_observed(grade)


def finding_metrics(row: Dict[str, Any]) -> List[str]:
    metrics: List[str] = []
    for key in FINDING_METRIC_KEYS:
        value = row.get(key)
        for item in as_list(value):
            if isinstance(item, dict):
                name = first_present(item, METRIC_NAME_KEYS)
            else:
                name = item
            cleaned = str(name or "").strip()
            if cleaned:
                metrics.append(cleaned)
    return metrics


def extract_references(row: Dict[str, Any]) -> List[str]:
    refs: List[str] = []
    for key in REFERENCE_KEYS:
        for item in as_list(row.get(key)):
            if isinstance(item, dict):
                ref = clean_id(item)
                if not ref and item.get("type") == "finding":
                    ref = clean_id(item.get("id"))
            else:
                ref = clean_id(item)
            if ref:
                refs.append(ref)
    return sorted(set(refs))


def extract_expected_metrics(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_metrics: List[Any] = []
    for key in METRIC_LIST_KEYS:
        raw_metrics.extend(as_list(row.get(key)))
    for key in SINGLE_METRIC_KEYS:
        if key in row:
            raw_metrics.extend(as_list(row.get(key)))

    metrics: List[Dict[str, Any]] = []
    for item in raw_metrics:
        if isinstance(item, dict):
            name = first_present(item, METRIC_NAME_KEYS)
            has_change_spec = any(item.get(key) not in (None, "") for key in CHANGE_SPEC_KEYS)
            metrics.append(
                {
                    "name": str(name or "").strip(),
                    "hasChangeSpec": has_change_spec,
                    "raw": item,
                }
            )
        else:
            metrics.append({"name": str(item or "").strip(), "hasChangeSpec": False, "raw": item})
    return metrics


def validate_report(
    data: Any,
    *,
    require_metric_change_spec: bool = True,
    require_metric_evidence_link: bool = False,
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(data, dict):
        return {
            "ok": False,
            "checkedAt": utc_now(),
            "errors": ["report must be a JSON object"],
            "warnings": [],
        }

    findings = find_list(data, FINDING_LIST_KEYS)
    recommendations = find_list(data, RECOMMENDATION_LIST_KEYS)
    finding_map: Dict[str, Dict[str, Any]] = {}
    finding_details: Dict[str, Dict[str, Any]] = {}
    for index, finding in enumerate(findings):
        finding_id = clean_id(first_present(finding, FINDING_ID_KEYS))
        if not finding_id:
            errors.append(f"finding[{index}] is missing an id")
            continue
        if finding_id in finding_map:
            errors.append(f"duplicate finding id: {finding_id}")
        finding_map[finding_id] = finding
        finding_details[finding_id] = {
            "observed": finding_observed(finding),
            "metrics": finding_metrics(finding),
        }

    if not findings:
        errors.append("report has no findings list")
    if not recommendations:
        errors.append("report has no recommendations list")

    recommendation_results: List[Dict[str, Any]] = []
    for index, recommendation in enumerate(recommendations):
        rec_id = clean_id(first_present(recommendation, RECOMMENDATION_ID_KEYS)) or f"recommendation[{index}]"
        rec_errors: List[str] = []
        refs = extract_references(recommendation)
        if not refs:
            rec_errors.append("recommendation has no finding/evidence references")
        unknown_refs = [ref for ref in refs if ref not in finding_map]
        if unknown_refs:
            rec_errors.append(f"references unknown findings: {', '.join(unknown_refs)}")
        observed_refs = [ref for ref in refs if finding_details.get(ref, {}).get("observed")]
        if refs and not observed_refs:
            rec_errors.append("recommendation does not reference an observed finding")

        metrics = extract_expected_metrics(recommendation)
        metric_names = [metric["name"] for metric in metrics if metric.get("name")]
        if not metric_names:
            rec_errors.append("recommendation declares no expected metric to change")
        for metric in metrics:
            if not metric.get("name"):
                rec_errors.append("expected metric entry is missing name")
            if require_metric_change_spec and metric.get("name") and not metric.get("hasChangeSpec"):
                rec_errors.append(f"expected metric lacks direction/threshold: {metric.get('name')}")

        if require_metric_evidence_link and metric_names and observed_refs:
            linked_metric_names = {
                normalize_metric_name(metric)
                for ref in observed_refs
                for metric in finding_details.get(ref, {}).get("metrics", [])
            }
            for name in metric_names:
                if normalize_metric_name(name) not in linked_metric_names:
                    rec_errors.append(f"expected metric is not listed on referenced observed findings: {name}")

        errors.extend(f"{rec_id}: {error}" for error in rec_errors)
        recommendation_results.append(
            {
                "id": rec_id,
                "ok": not rec_errors,
                "findingRefs": refs,
                "observedFindingRefs": observed_refs,
                "expectedMetrics": metric_names,
                "errors": rec_errors,
            }
        )

    unreferenced_findings = sorted(set(finding_map) - {ref for item in recommendation_results for ref in item["findingRefs"]})
    if unreferenced_findings:
        warnings.append(f"findings not referenced by any recommendation: {', '.join(unreferenced_findings)}")

    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "findingCount": len(findings),
        "observedFindingCount": sum(1 for item in finding_details.values() if item.get("observed")),
        "recommendationCount": len(recommendations),
        "recommendationsPassed": sum(1 for item in recommendation_results if item["ok"]),
        "recommendationsFailed": sum(1 for item in recommendation_results if not item["ok"]),
        "requireMetricChangeSpec": require_metric_change_spec,
        "requireMetricEvidenceLink": require_metric_evidence_link,
        "recommendations": recommendation_results,
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify recommendation-to-finding and metric linkage.")
    parser.add_argument("report", help="Structured recommendation JSON, Markdown with embedded JSON, or a directory containing recommendation-report.json.")
    parser.add_argument("--out-json", help="Optional path for full verification JSON.")
    parser.add_argument("--allow-metric-without-change-spec", action="store_true", help="Allow expected metrics without direction/threshold.")
    parser.add_argument("--require-metric-evidence-link", action="store_true", help="Require expected metrics to appear on referenced observed findings.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    data, load_errors = load_report(Path(args.report))
    if load_errors:
        result = {
            "ok": False,
            "checkedAt": utc_now(),
            "errors": load_errors,
            "warnings": [],
        }
    else:
        result = validate_report(
            data,
            require_metric_change_spec=not args.allow_metric_without_change_spec,
            require_metric_evidence_link=args.require_metric_evidence_link,
        )
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(
        json.dumps(
            {
                "ok": result.get("ok"),
                "findingCount": result.get("findingCount", 0),
                "recommendationCount": result.get("recommendationCount", 0),
                "errors": result.get("errors", [])[:6],
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
