import importlib.metadata

from .models import FieldsetConfig, ModelExpansion
from .render import render_fieldset_model
from .schema import FieldsetGenerateJsonSchema

try:
    __version__ = importlib.metadata.version("pydantic_enhanced_serializer")
except importlib.metadata.PackageNotFoundError:
    __version__ = "dev"
