from __future__ import annotations

import csv
import json
import base64
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import flowio
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOTS = [
    ROOT / "backend" / "NTA",
    ROOT / "backend" / "nanoFACS",
]
OUTPUT_ROOTS = {
    "NTA": ROOT / "backend" / "NTA_parquet",
    "nanoFACS": ROOT / "backend" / "nanoFACS_parquet",
}

SUPPORTED = {".csv", ".txt", ".json", ".xlsx", ".fcs", ".xml"}


@dataclass
class ConversionResult:
    source: str
    destination: str | None
    status: str
    rows: int | None = None
    columns: int | None = None
    reason: str | None = None


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _try_read_text_table(path: Path) -> pd.DataFrame:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:8192]

    candidates: list[str | None] = []
    try:
        sniffed = csv.Sniffer().sniff(sample, delimiters=",\t;| ")
        candidates.append(sniffed.delimiter)
    except Exception:
        pass

    candidates.extend([",", "\t", ";", "|", None])

    for sep in candidates:
        try:
            if sep is None:
                df = pd.read_csv(path, sep=r"\s+", engine="python", low_memory=False)
            else:
                df = pd.read_csv(path, sep=sep, engine="python", low_memory=False)
            if not df.empty and max(df.shape) > 1:
                return df
            if df.shape[1] > 1:
                return df
        except Exception:
            continue

    text = path.read_text(encoding="utf-8", errors="ignore")
    return pd.DataFrame({
        "line_number": list(range(1, len(text.splitlines()) + 1)) or [1],
        "text": text.splitlines() or [text],
    })


def _read_json(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        data: Any = json.load(f)

    if isinstance(data, list):
        return pd.json_normalize(data)
    if isinstance(data, dict):
        return pd.json_normalize(data)

    return pd.DataFrame({"value": [data]})


def _read_fcs(path: Path) -> pd.DataFrame:
    fcs = flowio.FlowData(str(path), ignore_offset_error=True)
    channel_count = int(fcs.channel_count)
    events = np.array(fcs.events, dtype=np.float64).reshape(-1, channel_count)

    channel_names: list[str] = []
    for i in range(channel_count):
        channel = fcs.channels.get(str(i + 1), {})
        name = channel.get("PnN") or channel.get("PnS") or f"ch_{i + 1}"
        channel_names.append(str(name))

    return pd.DataFrame(events, columns=channel_names)


def _read_xml(path: Path) -> pd.DataFrame:
    try:
        return pd.read_xml(path)
    except Exception:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return pd.DataFrame({"xml_text": [text]})


def _raw_file_frame(path: Path) -> pd.DataFrame:
    payload = path.read_bytes()
    return pd.DataFrame(
        {
            "file_name": [path.name],
            "extension": [path.suffix.lower()],
            "size_bytes": [len(payload)],
            "content_base64": [base64.b64encode(payload).decode("ascii")],
        }
    )


def _to_dataframe(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path, low_memory=False)
    if ext == ".txt":
        return _try_read_text_table(path)
    if ext == ".json":
        return _read_json(path)
    if ext == ".xlsx":
        return pd.read_excel(path)
    if ext == ".fcs":
        return _read_fcs(path)
    if ext == ".xml":
        return _read_xml(path)

    return _raw_file_frame(path)


def convert_tree(input_root: Path, output_root: Path) -> list[ConversionResult]:
    results: list[ConversionResult] = []

    files = sorted(p for p in input_root.rglob("*") if p.is_file())
    for source in files:
        rel = source.relative_to(input_root)
        ext = source.suffix.lower()

        dest = output_root / rel.parent / f"{source.name}.parquet"

        try:
            df = _to_dataframe(source)
            if df is None:
                raise ValueError("No dataframe returned")

            _ensure_parent(dest)
            df.to_parquet(dest, index=False, engine="pyarrow", compression="snappy")

            results.append(
                ConversionResult(
                    source=str(source),
                    destination=str(dest),
                    status="converted",
                    rows=int(df.shape[0]),
                    columns=int(df.shape[1]),
                )
            )
        except Exception as e:
            try:
                df = _raw_file_frame(source)
                _ensure_parent(dest)
                df.to_parquet(dest, index=False, engine="pyarrow", compression="snappy")
                results.append(
                    ConversionResult(
                        source=str(source),
                        destination=str(dest),
                        status="converted_fallback",
                        rows=int(df.shape[0]),
                        columns=int(df.shape[1]),
                        reason=str(e),
                    )
                )
            except Exception as raw_err:
                results.append(
                    ConversionResult(
                        source=str(source),
                        destination=str(dest),
                        status="failed",
                        reason=f"primary: {e}; fallback: {raw_err}",
                    )
                )

    return results


def main() -> None:
    all_results: list[ConversionResult] = []

    for input_root in INPUT_ROOTS:
        if not input_root.exists():
            continue
        output_root = OUTPUT_ROOTS[input_root.name]
        if output_root.exists():
            shutil.rmtree(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        all_results.extend(convert_tree(input_root, output_root))

    report_dir = ROOT / "backend" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "nta_nanofacs_parquet_conversion_report.json"

    converted = [r for r in all_results if r.status in {"converted", "converted_fallback"}]
    converted_fallback = [r for r in all_results if r.status == "converted_fallback"]
    skipped = [r for r in all_results if r.status == "skipped"]
    failed = [r for r in all_results if r.status == "failed"]

    payload = {
        "summary": {
            "total_files_seen": len(all_results),
            "converted": len(converted),
            "converted_with_fallback": len(converted_fallback),
            "skipped": len(skipped),
            "failed": len(failed),
        },
        "results": [r.__dict__ for r in all_results],
    }

    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Report: {report_path}")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
