import importlib.metadata

from .models import ModelExpansion
from .render import render_fieldset_model
from .schema import augment_schema_with_fieldsets

try:
    __version__ = importlib.metadata.version("pydantic_sparsefields")
except importlib.metadata.PackageNotFoundError:
    __version__ = "dev"
