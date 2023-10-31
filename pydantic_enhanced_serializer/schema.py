from inspect import isclass
from typing import Any, Dict, List, Optional, Set, Type, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic._internal._config import ConfigWrapper
from pydantic._internal._generate_schema import GenerateSchema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core.core_schema import CoreSchema, ModelSchema

from .models import ExpansionBase


class FieldsetGenerateJsonSchema(GenerateJsonSchema):
    def model_schema(self, schema: ModelSchema) -> JsonSchemaValue:
        json_schema = super().model_schema(schema)

        model = schema["cls"]

        # Not configured with fieldsets or expansions
        if not hasattr(model, "fieldset_config"):
            return json_schema

        fieldsets = model.fieldset_config.get("fieldsets")

        # for regular fields, set a description based on their fieldset configuration
        for field_name in model.model_fields.keys():
            field_schema = json_schema["properties"][field_name]
            fieldset_names = [
                fieldset_name
                for fieldset_name in fieldsets.keys()
                if isinstance(fieldsets[fieldset_name], list)
                and (
                    field_name in fieldsets[fieldset_name]
                    or "*" in fieldsets[fieldset_name]
                )
            ]

            if not fieldset_names:
                # nothing is returned by default, must always ask for this field explicity
                field_schema["description"] = _concat_description(
                    field_schema.get("description"),
                    "Not returned by default.  Request this field by name.",
                )

            elif "default" not in fieldset_names and len(fieldset_names) > 0:
                field_schema["description"] = _concat_description(
                    field_schema.get("description"),
                    "Request by name or using fieldset(s): "
                    + ", ".join(
                        [f"`{f}`" for f in sorted(fieldset_names) if f != "default"]
                    )
                    + ".",
                )

        # detail expansions
        generator = GenerateSchema(
            config_wrapper=ConfigWrapper(config={}), types_namespace=None
        )

        for expansion_name, expansion in fieldsets.items():
            if not isinstance(expansion, ExpansionBase):
                continue

            if expansion.response_model is None:
                continue

            target_type = _get_target_type(expansion.response_model)

            # If this is a not before seen model class, it needs to be registered
            # before we can $ref it
            model_schema: Optional[CoreSchema] = None

            if isclass(target_type) and issubclass(target_type, BaseModel):
                model_schema = generator._model_schema(target_type)
                defs_ref = self.get_defs_ref((model_schema["schema_ref"], "validation"))

                if defs_ref not in self.definitions:
                    self.definitions[defs_ref] = target_type.model_json_schema()

            if model_schema and target_type == expansion.response_model:
                core_schema = model_schema
            else:
                core_schema = generator.match_type(expansion.response_model)

            sub_json_schema = self.generate_inner(core_schema)
            json_schema["properties"][expansion_name] = {
                "title": expansion_name.title().replace("_", " "),
                "description": f"Request by name or using fieldset(s): `{expansion_name}`.",
                **sub_json_schema,
            }

        return json_schema


def _concat_description(description: Optional[str], additional: str) -> str:
    if description is None:
        return additional

    if description.endswith("."):
        return " ".join([description, additional])
    else:
        return ". ".join([description, additional])


def _get_target_type(value: Any) -> Any:
    """Find the underlying contained type and its level of "structured" (dict/list) nesting"""
    if _is_optional(value):
        value = _get_optional_type(value)

    if not get_origin(value) or not isclass(get_origin(value)):
        return value

    if issubclass(get_origin(value), (list, List, set, Set)) and (
        list_args := get_args(value)
    ):
        return _get_target_type(list_args[0])

    if (
        issubclass(get_origin(value), (dict, Dict))
        and (dict_args := get_args(value))
        and len(dict_args) == 2
    ):
        return _get_target_type(dict_args[1])

    return value


def _is_optional(type_: Any) -> bool:
    return (
        get_origin(type_) is Union
        and len(get_args(type_)) == 2
        and type(None) in get_args(type_)
    )


def _get_optional_type(type_: Any) -> Optional[Type]:
    for arg in get_args(type_):
        if arg is not None:
            return arg

    return None
