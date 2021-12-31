from functools import partial
from typing import Any, Callable, Dict, List, Type, Union

from pydantic import BaseModel

from .models import ExpansionBase


def _fully_list_fieldvalue(value: Union[str, List[str]]) -> List[str]:
    fields: List[str] = []

    if isinstance(value, str):
        fields.extend(value.split(","))

    elif isinstance(value, list):
        for fieldspec in value:
            fields.extend(fieldspec.split(","))

    return sorted(list(set(fields)))


def schema_extra(
    original_schema_extra: Union[Callable, dict, None],
    schema: Dict[str, Any],
    model: Type[BaseModel],
) -> None:
    fieldsets: dict = getattr(model.__config__, "fieldsets", {})

    fieldset_description_blocks = [
        "Available fieldsets and expansions for this object:" "",
    ]

    if "default" in fieldsets:
        fields = _fully_list_fieldvalue(fieldsets["default"])

        fieldset_description_blocks.append(f"* **Default Fields:** {', '.join(fields)}")

    for fieldset in sorted(fieldsets.keys()):
        if fieldset == "default":
            continue

        elif isinstance(fieldsets[fieldset], ExpansionBase):
            response_model = fieldsets[fieldset].response_model

            line = f"* `{fieldset}`: Expansion"
            if response_model:
                title = response_model.__config__.title or response_model.__name__
                line += f" of type {title}"

                augment_schema_with_fieldsets(response_model)

            fieldset_description_blocks.append(line)

        else:
            fields = _fully_list_fieldvalue(fieldsets[fieldset])
            fieldset_description_blocks.append(f"* `{fieldset}` {', '.join(fields)}")

    if schema.get("description"):
        schema["description"] += "\n\n" + "\n".join(fieldset_description_blocks)
    else:
        schema["description"] = "\n".join(fieldset_description_blocks)

    if callable(original_schema_extra):
        _deep_update(schema, original_schema_extra(schema, model) or {})

    elif isinstance(original_schema_extra, dict):
        _deep_update(schema, original_schema_extra)


def augment_schema_with_fieldsets(model: Type[BaseModel]) -> None:
    if (
        isinstance(model.__config__.schema_extra, partial)
        and model.__config__.schema_extra.func == schema_extra
    ):
        # Already augmented this model
        return

    for field_obj in model.__fields__.values():
        # descend subfields
        if issubclass(field_obj.type_, BaseModel):
            augment_schema_with_fieldsets(field_obj.type_)

    if getattr(model.__config__, "fieldsets", None) is None:
        # Not a fieldsets model, skip it
        return

    current_schema_extra: Union[Callable, dict, None] = getattr(
        model.__config__, "schema_extra", None
    )
    model.__config__.schema_extra = partial(schema_extra, current_schema_extra)


def _deep_update(into_dict: Dict[Any, Any], from_dict: Dict[Any, Any]) -> None:
    for key in from_dict.keys():
        if (
            key in into_dict
            and isinstance(from_dict[key], dict)
            and isinstance(into_dict[key], dict)
        ):
            _deep_update(into_dict[key], from_dict[key])
        else:
            into_dict[key] = from_dict[key]
