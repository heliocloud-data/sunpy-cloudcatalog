# sunpy-cloudcatalog

[![PyPI](https://img.shields.io/pypi/v/sunpy-cloudcatalog.svg)](https://pypi.org/project/sunpy-cloudcatalog/)
[![License](https://img.shields.io/badge/license-MIT.svg)](#license)
[![SunPy
Affiliated](https://img.shields.io/badge/SunPy-Affiliated-orange.svg)](https://sunpy.org/affiliated/)

A SunPy-affiliated package providing a `sunpy.net.Fido` client for
querying file manifests from the
[CloudCatalog](https://github.com/heliocloud-data/cloudcatalog) service.

This package integrates CloudCatalog datasets directly into the SunPy
data discovery ecosystem.

------------------------------------------------------------------------

## Overview

`sunpy-cloudcatalog` implements a SunPy `BaseClient` that allows:

-   Searching CloudCatalog datasets via `Fido.search()`
-   Returning results as `QueryResponseTable`
-   Generating CSV manifest files via `Fido.fetch()`
-   Using custom query attributes (`Bucket`, `DataID`)

The package follows the official SunPy Fido extension mechanism:
https://docs.sunpy.org/en/stable/topic_guide/extending_fido.html

------------------------------------------------------------------------

## Installation

### From PyPI

``` bash
pip install sunpy-cloudcatalog
```

### Development Installation

``` bash
git clone https://github.com/<org>/sunpy-cloudcatalog.git
cd sunpy-cloudcatalog
pip install -e .
```

------------------------------------------------------------------------

## Usage

Importing the package registers the client with SunPy automatically.

``` python
import sunpy_cloudcatalog

from sunpy.net import Fido, attrs as a
from sunpy_cloudcatalog import Bucket, DataID
```

### Example Search

``` python
res = Fido.search(
    a.Time("2012-01-01", "2012-01-02"),
    Bucket("s3://gov-nasa-hdrl-data1/"),
    DataID("aia_0094"),
)

print(res[0][:2])
```

### Fetch a Manifest

``` python
manifest = Fido.fetch(res)
print(list(manifest))
```

This writes a CSV manifest file describing the matching CloudCatalog
entries.

------------------------------------------------------------------------

## Query Attributes

### `Bucket`

CloudCatalog bucket URI:

``` python
Bucket("s3://gov-nasa-hdrl-data1/")
```

### `DataID`

Dataset identifier within the CloudCatalog bucket:

``` python
DataID("aia_0094")
```

------------------------------------------------------------------------

## Returned Columns

Search results contain:

-   `Start Time`
-   `End Time`
-   `Bucket`
-   `DataID`
-   `URL`
-   `Key`
-   `Size`

------------------------------------------------------------------------

## Testing

Run unit tests:

``` bash
pytest
```

Run integration tests (network required):

``` bash
pytest -m integration
```

------------------------------------------------------------------------

## Project Structure

    sunpy-cloudcatalog/
    ├── pyproject.toml
    ├── pytest.ini
    ├── src/
    │   └── sunpy_cloudcatalog/
    │       ├── __init__.py
    │       ├── main.py
    └── tests/

------------------------------------------------------------------------

## SunPy Affiliated Package Status

This project follows the SunPy affiliated package guidelines:

-   Uses the official Fido extension interface
-   Provides documentation and tests
-   Is versioned and distributed via PyPI
-   Maintains compatibility with supported SunPy releases

Affiliation information: https://sunpy.org/affiliated/

------------------------------------------------------------------------

## Contributing

Contributions are welcome. Please:

1.  Open an issue to discuss changes.
2.  Submit pull requests with tests.
3.  Ensure `pytest` passes locally.

------------------------------------------------------------------------

## License

The MIT License (MIT)

