"""
SunPy Fido "full client" that fetches CloudCatalog filelists (manifests), not the data files.

Key idea:
- Fido.search(...) returns a QueryResponseTable containing one row per data file
  (start/end time, s3 url/key, size, etc.).
- Fido.fetch(...) writes the filelist to one (or more) local CSV manifest file(s) and
  returns the manifest path(s).

References:
- SunPy Fido: https://docs.sunpy.org/en/stable/generated/api/sunpy.net.Fido.html  :contentReference[oaicite:0]{index=0}
- Extending Fido (full client pattern): https://docs.sunpy.org/en/stable/topic_guide/extending_fido.html  :contentReference[oaicite:1]{index=1}
- CloudCatalog Python usage (request_cloud_catalog returns a pandas DataFrame): :contentReference[oaicite:2]{index=2}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

import cloudcatalog

from astropy.table import Table
from sunpy.net.attr import SimpleAttr
from sunpy.net.base_client import BaseClient, QueryResponseTable, QueryResponseRow

from sunpy.util.parfive_helpers import Results

# -----------------------
# CloudCatalog-specific attrs
# -----------------------

class Bucket(SimpleAttr):
    """CloudCatalog endpoint / bucket, e.g. 's3://gov-nasa-hdrl-data1/'."""
    pass
    #def __init__(self, value: str):
    #    super().__init__()
    #    self.value = value


class DataID(SimpleAttr):
    """CloudCatalog dataset ID within the bucket catalog, e.g. 'aia_0094'."""
    def __init__(self, value: str):
        super().__init__(value)
        self.value = str(value)


# -----------------------
# Helpers
# -----------------------

def _dt_to_isoz(dt: datetime) -> str:
    """
    Convert datetime to ISO-8601 with 'Z'.
    CloudCatalog examples use e.g. '2007-02-01T00:00:00Z'. :contentReference[oaicite:3]{index=3}
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class _CCQuery:
    bucket: str
    dataid: str
    start_isoz: str
    end_isoz: Optional[str]


def _extract_first(query, attr_type):
    for q in query:
        if isinstance(q, attr_type):
            return q
    return None


def _ensure_time_attr(query):
    # Accept sunpy.net.attrs.Time (from sunpy.net import attrs as a).
    # We avoid importing it directly to keep this file self-contained w.r.t. SunPy attr modules.
    for q in query:
        if q.__class__.__name__ == "Time":
            return q
    return None


def _sunpy_time_to_isoz(time_attr) -> tuple[str, str]:
    """
    SunPy a.Time stores start/end as astropy Time-like objects; commonly accessible as:
    - time_attr.start
    - time_attr.end
    They can be converted via .datetime.
    """
    start_dt = time_attr.start.datetime
    end_dt = time_attr.end.datetime
    return _dt_to_isoz(start_dt), _dt_to_isoz(end_dt)


# -----------------------
# The Fido client
# -----------------------

class CloudCatalogClient(BaseClient):
    """
    SunPy Fido client for CloudCatalog filelists.

    This is a "full client" (not a URL scraper), because we query an API
    (cloudcatalog.CloudCatalog.request_cloud_catalog) to obtain file listings. :contentReference[oaicite:4]{index=4}
    """

    info_url = "https://github.com/heliocloud-data/cloudcatalog"
    
    @classmethod
    def _can_handle_query(cls, *query) -> bool:
        """
        Tell Fido when this client applies: requires Time + Bucket + DataID.
        """
        time_attr = _ensure_time_attr(query)
        return (
            time_attr is not None
            and _extract_first(query, Bucket) is not None
            and _extract_first(query, DataID) is not None
        )

    @classmethod
    def register_values(cls):
        """
        Optional: advertise supported attrs for discoverability.
        """
        # This is intentionally minimal: Bucket/DataID are user-provided strings.
        return {
            Bucket: [("s3://...", "CloudCatalog bucket/endpoint URI")],
            DataID: [("...", "CloudCatalog dataset ID within the bucket catalog")],
        }

    def search(self, *query, **kwargs) -> QueryResponseTable:
        """
        Return one row per data file listed by CloudCatalog.
        """
        time_attr = _ensure_time_attr(query)
        bucket_attr = _extract_first(query, Bucket)
        dataid_attr = _extract_first(query, DataID)

        if time_attr is None or bucket_attr is None or dataid_attr is None:
            raise ValueError("CloudCatalogClient requires a.Time(...), Bucket(...), and DataID(...)")

        start_isoz, end_isoz = _sunpy_time_to_isoz(time_attr)
        q = _CCQuery(
            bucket=bucket_attr.value,
            dataid=dataid_attr.value,
            start_isoz=start_isoz,
            end_isoz=end_isoz,
        )

        # CloudCatalog usage per package docs: CloudCatalog(bucket).request_cloud_catalog(dataid, start_date, end_date). :contentReference[oaicite:5]{index=5}
        cc = cloudcatalog.CloudCatalog(q.bucket)

        df: pd.DataFrame = cc.request_cloud_catalog(
            q.dataid,
            start_date=q.start_isoz,
            stop_date=q.end_isoz,
            overwrite=False,
        )

        # Expected columns per docs: startdate, stopdate, key, filesize. :contentReference[oaicite:6]{index=6}
        # Normalize/validate defensively.
        #required = {"startdate", "stopdate", "key"}
        required = {"start", "stop", "datakey"}
        missing = required - set(df.columns)
        if missing:
            raise RuntimeError(f"CloudCatalog returned DataFrame missing columns: {sorted(missing)}")

        if "filesize" not in df.columns:
            df["filesize"] = None

        # Build URLs. CloudCatalog "key" is typically the object key within the bucket. :contentReference[oaicite:7]{index=7}
        # For an s3:// bucket URI, a reasonable "file URL" is bucket.s3.amazonaws.com/file
        bucket_prefix = q.bucket.rstrip("/")
        df["url"] = "https://" + bucket_prefix[5:] + ".s3.amazonaws.com/" + df["datakey"].astype(str).str.replace(bucket_prefix,"",regex=False).str.lstrip("/")

        # Convert to an astropy table then to QueryResponseTable.
        # Keep column names friendly for interactive display.
        out = Table.from_pandas(
            df[["start", "stop", "url", "datakey", "filesize"]].rename(
                columns={
                    "start": "Start Time",
                    "stop": "End Time",
                    "filesize": "Size",
                    "datakey": "Key",
                    "url": "URL",
                }
            ),
            index=False,
        )
        ###out["Bucket"] = q.bucket
        out["DataID"] = q.dataid

        # Order columns
        ###out = out[["Start Time", "End Time", "Bucket", "DataID", "URL", "Key", "Size"]]
        out = out[["Start Time", "End Time", "DataID", "URL", "Key", "Size"]]

        # Tag the table with the client (SunPy uses this internally).
        qrt = QueryResponseTable(out)
        qrt.client = self
        return qrt
        #return QueryResponseTable(out)


    def fetch(self, query_results, *, path, downloader, **kwargs):
        # Normalize single-row inputs
        if isinstance(query_results, QueryResponseRow):
            query_results = query_results.as_table()

        if len(query_results) == 0:
            return Results()

        # Build a single manifest filename (customize as you like)
        row0 = query_results[0]
        dataid = str(row0["DataID"])
        start = str(row0["Start Time"]).replace(":", "").replace(" ", "T")
        end = str(row0["End Time"]).replace(":", "").replace(" ", "T")
        manifest_name = f"{dataid}_{start}_{end}.csv"

        # IMPORTANT: path includes "{file}" -> supply file=...
        # Also allow other placeholders via response_block_map if present
        out_path = Path(str(path).format(file=manifest_name, **row0.response_block_map)).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write manifest (entire table)
        query_results.to_pandas().to_csv(out_path, index=False)

        r = Results()
        r.data.append(str(out_path))
        return r

    def fetch_bad(
        self,
        query_results: QueryResponseTable,
        path: str | Path = "./cloudcatalog_manifests/{dataid}_{start}_{end}.csv",
        **kwargs,
    ) -> list[str]:
        """
        Write the filelist as one CSV "manifest" and return the local path.

        Note: this does not download the science data; it only materializes the listing.
        """
        if len(query_results) == 0:
            return []

        # Derive metadata for naming.
        dataid = str(query_results["DataID"][0])
        start = str(query_results["Start Time"][0]).replace(":", "").replace(" ", "T")
        end = str(query_results["End Time"][0]).replace(":", "").replace(" ", "T")

        out_path = Path(str(path).format(dataid=dataid, start=start, end=end)).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        df = query_results.to_pandas()
        df.to_csv(out_path, index=False)

        return [str(out_path)]


if __name__ == "__main__":
    pass
from pathlib import Path
from sunpy.util.parfive_helpers import Results
from sunpy.net.base_client import QueryResponseRow
