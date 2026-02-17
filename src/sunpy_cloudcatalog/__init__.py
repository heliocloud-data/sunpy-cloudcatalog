"""
SunPy CloudCatalog Fido client.

Importing this package registers the CloudCatalogClient with sunpy.net.Fido.
"""

from importlib.metadata import version, PackageNotFoundError

# Import the module that defines the BaseClient subclass
# This ensures registration into BaseClient._registry at import time.
from .main import CloudCatalogClient, Bucket, DataID  # noqa: F401


__all__ = [
    "CloudCatalogClient",
    "Bucket",
    "DataID",
]


# Optional: expose package version
try:
    __version__ = version("sunpy-cloudcatalog")
except PackageNotFoundError:
    __version__ = "0.0.0"
