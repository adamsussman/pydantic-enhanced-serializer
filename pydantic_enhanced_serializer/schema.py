import inspect
from collections import defaultdict
from functools import partial
from itertools import chain
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from pydantic.schema import add_field_type_to_schema, model_schema, normalize_name

from .models import ExpansionBase


def _fully_list_fieldvalue(value: Union[str, List[str]]) -> List[str]:
    fields: List[str] = []

    if isinstance(value, str):
        fields.extend(value.split(","))

    elif isinstance(value, list):
        for fieldspec in value:
            fields.extend(fieldspec.split(","))

    return sorted(list(set(fields)))


def is_optional(type_: Any) -> bool:
    return (
        get_origin(type_) is Union
        and len(get_args(type_)) == 2
        and type(None) in get_args(type_)
    )


def get_optional_type(type_: Any) -> Optional[Type]:
    for arg in get_args(type_):
        if arg is not None:
            return arg

    return None


def schema_extra(
    original_schema_extra: Union[Callable, dict, None],
    schema: Dict[str, Any],
    model: Type[BaseModel],
) -> None:
    fieldsets: dict = getattr(model.__config__, "fieldsets", {})
    if not fieldsets:
        return

    fieldsets_per_field: Dict[str, Set[str]] = defaultdict(set)

    for fieldset_name in fieldsets:
        field_names = set()

        if fieldset_name == "default" and "*" in fieldsets[fieldset_name]:
            field_names.update([f.name for f in model.__fields__.values()])
            field_names.update(
                [
                    name
                    for name in fieldsets.keys()
                    if isinstance(fieldsets[fieldset_name], ExpansionBase)
                ]
            )
        elif isinstance(fieldsets[fieldset_name], ExpansionBase):
            schema["properties"][fieldset_name] = {
                "title": fieldset_name.title().replace("_", " "),
            }

            response_model = fieldsets[fieldset_name].response_model
            if is_optional(response_model):
                response_model = get_optional_type(response_model)

            if inspect.isclass(response_model) and issubclass(
                response_model, BaseModel
            ):
                model_name = normalize_name(response_model.__name__)
                schema["properties"][fieldset_name][
                    "$ref"
                ] = f"#/definitions/{model_name}"

                augment_schema_with_fieldsets(response_model)
                if "definitions" not in schema:
                    schema["definitions"] = {}
                schema["definitions"][model_name] = model_schema(response_model)

            else:
                add_field_type_to_schema(
                    get_origin(response_model) or response_model,
                    schema["properties"][fieldset_name],
                )

            if schema["properties"][fieldset_name].get("type") == "array":
                list_models = get_args(response_model)
                if (
                    list_models
                    and inspect.isclass(list_models[0])
                    and issubclass(list_models[0], BaseModel)
                ):
                    model_name = normalize_name(list_models[0].__name__)
                    schema["properties"][fieldset_name]["items"] = {
                        "$ref": f"#/definitions/{model_name}"
                    }

                    augment_schema_with_fieldsets(list_models[0])
                    if "definitions" not in schema:
                        schema["definitions"] = {}
                    schema["definitions"][model_name] = model_schema(list_models[0])

                elif list_models:
                    # add_field_type_to_schema is not copy-safe on subdicts
                    schema["properties"][fieldset_name]["items"] = {}
                    add_field_type_to_schema(
                        list_models[0], schema["properties"][fieldset_name]["items"]
                    )

            field_names = {fieldset_name}

        else:
            field_names = set(_fully_list_fieldvalue(fieldsets[fieldset_name]))

        for field_name in field_names:
            fieldsets_per_field[field_name].add(fieldset_name)

    for field_name in set(chain(model.__fields__.keys(), fieldsets_per_field.keys())):
        fieldset_names = fieldsets_per_field.get(field_name) or set()

        if "default" in fieldset_names and len(fieldset_names) == 1:
            continue

        if len(fieldset_names) > 0:
            description = (
                "Request using fieldset(s): "
                + ", ".join(
                    [f"`{f}`" for f in sorted(fieldset_names) if f != "default"]
                )
                + "."
            )
        else:
            description = "Not returned by default.  Request this field by name."

        schema["properties"][field_name]["description"] = (
            schema["properties"][field_name].get("description", "") + description
        )

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
        if inspect.isclass(field_obj.type_) and issubclass(field_obj.type_, BaseModel):
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


def model_has_fieldsets_defined(model: Any) -> bool:
    if is_optional(model):
        model = get_optional_type(model)

    if inspect.isclass(model) and issubclass(model, BaseModel):
        if getattr(model.__config__, "fieldsets", None):
            return True

        else:
            return any(
                [
                    model_has_fieldsets_defined(field.type_)
                    for field in model.__fields__.values()
                ]
            )

    return False
