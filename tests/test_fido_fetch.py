#! /usr/bin/env python3
"""Comprehensive test suite with fantastic code coverage goes here."""

from __future__ import annotations

import os
import pytest
import sys
from pathlib import Path

# --- Make imports work even if the package wasn't installed (fallback for local runs) ---
# Preferred in CI/dev is: `pip install -e .` so you can delete this block.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
if _SRC_DIR.exists():
    sys.path.insert(0, str(_SRC_DIR))

## Add project root to Python path
#sys.path.insert(0, os.path.abspath(os.path.join(
#    os.path.dirname(__file__), '../')))

# This import must execute the class definition so it gets registered
import sunpy_cloudcatalog.main  # defines CloudCatalogClient (subclass of BaseClient)

from sunpy.net import Fido, attrs as a
from sunpy_cloudcatalog import Bucket, DataID

@pytest.mark.integration
def test_fido_fetch(tmp_path: Path):
    """ Basic data fetch using Fido of a know data item
    
    Parameters
    ----------
    None

    Returns
    -------
    None

    Examples
    --------
    >>> test_fido_fetch()

    """

    res = Fido.search(
        a.Time("2012-01-01", "2012-01-02"),
        Bucket("s3://gov-nasa-hdrl-data1/"),
        DataID("aia_0094"),
    )
    print("Sample:\n",res[0][:2])

    # Write the manifest CSV locally (returns list of CSV paths)                
    manifest_paths = Fido.fetch(res, path=str(tmp_path / "{file}"))
    print("Wrote manifests:", manifest_paths)
    
    paths = list(manifest_paths)

    assert len(paths) >= 1
    for p in paths:
        assert Path(p).exists()
        assert Path(p).suffix.lower() == ".csv"

if __name__ == "__main__":
    test_fido_fetch()
