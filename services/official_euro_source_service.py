from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from io import StringIO
from pathlib import Path
import csv
import shutil
from time import sleep

import requests

from macro_import_manifest import get_macro_import
from services.euro_fingerprint_store import (
    SOURCE_DATASET,
    TARGET_DATASET,
    temporary_fingerprint_store,
)
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    canonical_row_hash,
    mapped_source_columns,
    normalize_row,
    normalize_source_frame,
    source_chunks,
)


ECB_DATA_API_BASE = "https://data-api.ecb.europa.eu/service/data"
DEFAULT_CHUNK_SIZE = 25_000
DEFAULT_TIMEOUT = (30, 900)
DEFAULT_DOWNLOAD_ATTEMPTS = 3
DEFAULT_STAGING_RESERVE_BYTES = 2 * 1024**3
USER_AGENT = (
    "FinancialMarketsAnalyticsPlatform/0.7.4 "
    "(+https://github.com/dinisan1992/financial-markets-analytics-platform)"
)


@dataclass(frozen=True)
class EcbSourceProbe:
    import_key: str
    dataflow: str
    request_url: str
    status_code: int
    content_type: str
    key_code: str
    time_period: str
    obs_value: str
    columns: tuple[str, ...]
    database_write_performed: bool = False
    active_csv_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class EcbSourceDownload:
    import_key: str
    dataflow: str
    request_url: str
    destination: str
    bytes: int
    sha256: str
    columns: tuple[str, ...]
    attempts: int
    database_write_performed: bool = False
    active_csv_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class EcbSourceFileComparison:
    import_key: str
    dataflow: str
    candidate_path: str
    active_path: str
    columns: tuple[str, ...]
    candidate_bytes: int
    active_bytes: int
    candidate_sha256: str
    active_sha256: str
    candidate_rows: int
    active_rows: int
    candidate_unique_keys: int
    active_unique_keys: int
    candidate_null_keys: int
    active_null_keys: int
    candidate_invalid_numeric_rows: int
    active_invalid_numeric_rows: int
    candidate_duplicate_groups: int
    active_duplicate_groups: int
    candidate_duplicate_rows: int
    active_duplicate_rows: int
    candidate_hash_conflicts: int
    active_hash_conflicts: int
    new_keys: int
    removed_keys: int
    changed_rows: int
    candidate_first_period: str | None
    candidate_last_period: str | None
    active_first_period: str | None
    active_last_period: str | None
    comparison_store_bytes: int
    safe_for_read_only_sql_plan: bool
    database_write_performed: bool = False
    active_csv_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


def _ecb_contract(import_key, source_path=None):
    import_key = str(import_key).upper()
    contract = get_macro_import(import_key)
    if contract.get("group") != "EURO":
        raise ValueError(f"Not a EURO import contract: {import_key}")
    if not contract.get("source_dataflow"):
        raise ValueError(f"Official ECB dataflow is not configured: {import_key}")
    if source_path is not None:
        contract["csv_path"] = Path(source_path).expanduser().resolve()
    return import_key, contract


def _session(session=None):
    if session is not None:
        return session, False
    output = requests.Session()
    output.headers.update(
        {
            "Accept": "text/csv",
            "Accept-Encoding": "gzip",
            "User-Agent": USER_AGENT,
        }
    )
    return output, True


def _raw_header(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), None)
    if not header:
        raise ValueError(f"ECB CSV has no header: {path}")
    return tuple(header)


def _first_series_key(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        row = next(reader, None)
    if row is None or not str(row.get("KEY", "")).strip():
        raise ValueError(f"ECB CSV has no usable series key: {path}")
    return str(row["KEY"]).strip()


def _response_rows(response):
    encoding = response.encoding or "utf-8-sig"
    reader = csv.DictReader(StringIO(response.content.decode(encoding)))
    rows = list(reader)
    return tuple(reader.fieldnames or ()), rows


def probe_official_euro_source(import_key, *, source_path=None, session=None):
    import_key, contract = _ecb_contract(import_key, source_path=source_path)
    source_path = Path(contract["csv_path"])
    expected_header = _raw_header(source_path)
    key_code = _first_series_key(source_path)
    dataflow = contract["source_dataflow"]
    prefix = f"{dataflow}."
    if not key_code.startswith(prefix):
        raise ValueError(
            f"ECB key does not belong to {dataflow}: {key_code}"
        )
    series_key = key_code.removeprefix(prefix)
    url = f"{ECB_DATA_API_BASE}/{dataflow}/{series_key}"
    client, owns_session = _session(session)
    response = None
    try:
        response = client.get(
            url,
            params={"format": "csvdata", "lastNObservations": 1},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        columns, rows = _response_rows(response)
        if columns != expected_header:
            raise ValueError(
                f"ECB probe schema differs for {import_key}: {columns}"
            )
        if len(rows) != 1:
            raise ValueError(
                f"ECB probe returned {len(rows)} observations for {import_key}"
            )
        row = rows[0]
        if str(row.get("KEY", "")).strip() != key_code:
            raise ValueError(f"ECB probe returned a different key for {import_key}")
        return EcbSourceProbe(
            import_key=import_key,
            dataflow=dataflow,
            request_url=str(response.url),
            status_code=int(response.status_code),
            content_type=str(response.headers.get("Content-Type", "")),
            key_code=key_code,
            time_period=str(row.get("TIME_PERIOD", "")),
            obs_value=str(row.get("OBS_VALUE", "")),
            columns=columns,
        )
    finally:
        if response is not None:
            response.close()
        if owns_session:
            client.close()


def download_official_euro_source(
    import_key,
    staging_dir,
    *,
    source_path=None,
    timeout=DEFAULT_TIMEOUT,
    attempts=DEFAULT_DOWNLOAD_ATTEMPTS,
    chunk_bytes=1024 * 1024,
    minimum_free_bytes=DEFAULT_STAGING_RESERVE_BYTES,
    session=None,
    progress_callback=None,
):
    import_key, contract = _ecb_contract(import_key, source_path=source_path)
    source_path = Path(contract["csv_path"])
    expected_header = _raw_header(source_path)
    staging_dir = Path(staging_dir).expanduser().resolve()
    staging_dir.mkdir(parents=True, exist_ok=True)
    required_free = source_path.stat().st_size + max(0, int(minimum_free_bytes))
    available_free = shutil.disk_usage(staging_dir).free
    if available_free < required_free:
        raise OSError(
            f"Insufficient staging space for {import_key}: "
            f"required={required_free}, available={available_free}"
        )
    destination = staging_dir / source_path.name
    if destination.exists():
        raise FileExistsError(f"ECB staging destination already exists: {destination}")
    temporary = destination.with_suffix(destination.suffix + ".partial")
    temporary.unlink(missing_ok=True)
    dataflow = contract["source_dataflow"]
    url = f"{ECB_DATA_API_BASE}/{dataflow}"
    attempts = max(1, int(attempts))
    client, owns_session = _session(session)
    request_url = contract["source_download_url"]

    try:
        for attempt in range(1, attempts + 1):
            digest = sha256()
            downloaded = 0
            response = None
            try:
                response = client.get(
                    url,
                    params={"format": "csvdata"},
                    stream=True,
                    timeout=timeout,
                )
                response.raise_for_status()
                request_url = str(response.url)
                content_type = str(response.headers.get("Content-Type", ""))
                if "csv" not in content_type.lower():
                    raise ValueError(
                        f"ECB response is not CSV for {import_key}: {content_type}"
                    )
                with temporary.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=chunk_bytes):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(import_key, downloaded)
                if downloaded == 0:
                    raise ValueError(f"ECB download is empty: {import_key}")
                columns = _raw_header(temporary)
                if columns != expected_header:
                    raise ValueError(
                        f"ECB download schema differs for {import_key}: {columns}"
                    )
                temporary.replace(destination)
                return EcbSourceDownload(
                    import_key=import_key,
                    dataflow=dataflow,
                    request_url=request_url,
                    destination=str(destination),
                    bytes=downloaded,
                    sha256=digest.hexdigest().upper(),
                    columns=columns,
                    attempts=attempt,
                )
            except requests.RequestException:
                temporary.unlink(missing_ok=True)
                if attempt >= attempts:
                    raise
                sleep(min(2**attempt, 10))
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
            finally:
                if response is not None:
                    response.close()
    finally:
        if owns_session:
            client.close()


def _file_sha256(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _scan_file(store, dataset, contract, path, chunk_size, progress_callback):
    scan_contract = dict(contract)
    scan_contract["csv_path"] = Path(path)
    columns = mapped_source_columns(scan_contract)
    rows = 0
    null_keys = 0
    invalid_numeric_rows = 0
    store.clear(dataset)

    with store.connection:
        for raw_chunk in source_chunks(scan_contract, chunk_size):
            chunk = normalize_source_frame(scan_contract, raw_chunk, columns)
            records = []
            for values in chunk.itertuples(index=False, name=None):
                rows += 1
                record, invalid_columns = normalize_row(columns, values)
                if invalid_columns:
                    invalid_numeric_rows += 1
                    continue
                key = tuple(record[column] for column in BUSINESS_KEY)
                if any(value is None for value in key):
                    null_keys += 1
                    continue
                records.append(
                    (
                        key[0],
                        key[1],
                        bytes.fromhex(canonical_row_hash(columns, record)),
                    )
                )
            store.insert_records(dataset, records)
            if progress_callback:
                progress_callback(dataset, rows)
    return columns, rows, null_keys, invalid_numeric_rows, store.summary(dataset)


def compare_euro_source_files(
    import_key,
    candidate_path,
    *,
    active_path=None,
    workspace_dir=None,
    chunk_size=DEFAULT_CHUNK_SIZE,
    minimum_free_bytes=2 * 1024**3,
    progress_callback=None,
):
    import_key, contract = _ecb_contract(import_key)
    candidate_path = Path(candidate_path).expanduser().resolve()
    active_path = Path(active_path or contract["csv_path"]).expanduser().resolve()
    if not candidate_path.is_file():
        raise FileNotFoundError(f"ECB candidate CSV not found: {candidate_path}")
    if not active_path.is_file():
        raise FileNotFoundError(f"ECB active CSV not found: {active_path}")
    if workspace_dir is not None:
        workspace_dir = Path(workspace_dir).expanduser().resolve()
        workspace_dir.mkdir(parents=True, exist_ok=True)
    with temporary_fingerprint_store(
        import_key,
        workspace_dir=workspace_dir,
        minimum_free_bytes=minimum_free_bytes,
    ) as store:
        candidate = _scan_file(
            store,
            SOURCE_DATASET,
            contract,
            candidate_path,
            chunk_size,
            progress_callback,
        )
        active = _scan_file(
            store,
            TARGET_DATASET,
            contract,
            active_path,
            chunk_size,
            progress_callback,
        )
        if candidate[0] != active[0]:
            raise ValueError(
                f"ECB candidate columns differ from the active CSV: {candidate[0]}"
            )
        differences = store.comparison()
        store_bytes = store.size_bytes

    candidate_summary = candidate[4]
    active_summary = active[4]
    safe = (
        candidate[1] > 0
        and candidate[2] == 0
        and candidate[3] == 0
        and candidate_summary["duplicate_groups"] == 0
        and candidate_summary["hash_conflicts"] == 0
    )
    return EcbSourceFileComparison(
        import_key=import_key,
        dataflow=contract["source_dataflow"],
        candidate_path=str(candidate_path),
        active_path=str(active_path),
        columns=candidate[0],
        candidate_bytes=candidate_path.stat().st_size,
        active_bytes=active_path.stat().st_size,
        candidate_sha256=_file_sha256(candidate_path),
        active_sha256=_file_sha256(active_path),
        candidate_rows=candidate[1],
        active_rows=active[1],
        candidate_unique_keys=candidate_summary["unique_keys"],
        active_unique_keys=active_summary["unique_keys"],
        candidate_null_keys=candidate[2],
        active_null_keys=active[2],
        candidate_invalid_numeric_rows=candidate[3],
        active_invalid_numeric_rows=active[3],
        candidate_duplicate_groups=candidate_summary["duplicate_groups"],
        active_duplicate_groups=active_summary["duplicate_groups"],
        candidate_duplicate_rows=candidate_summary["duplicate_rows"],
        active_duplicate_rows=active_summary["duplicate_rows"],
        candidate_hash_conflicts=candidate_summary["hash_conflicts"],
        active_hash_conflicts=active_summary["hash_conflicts"],
        new_keys=differences["source_rows_missing_from_target"],
        removed_keys=differences["target_rows_missing_from_source"],
        changed_rows=differences["row_hash_mismatches"],
        candidate_first_period=candidate_summary["first_period"],
        candidate_last_period=candidate_summary["last_period"],
        active_first_period=active_summary["first_period"],
        active_last_period=active_summary["last_period"],
        comparison_store_bytes=store_bytes,
        safe_for_read_only_sql_plan=safe,
    )
