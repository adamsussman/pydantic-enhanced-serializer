from inspect import isclass
from typing import (
    Annotated,
    Any,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
    get_args,
    get_origin,
)

import pydantic
from packaging.version import Version
from packaging.version import parse as parse_version
from pydantic import BaseModel
from pydantic._internal._config import ConfigWrapper
from pydantic._internal._generate_schema import GenerateSchema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core.core_schema import CoreSchema, ModelSchema

from .models import ExpansionBase

pydantic_version = parse_version(pydantic.__version__)
namespace_refactored_pydantic_version = Version("2.10")

DEFS_PREFIX_LENGTH = 8  # "#/$defs/"


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
            if field_name not in json_schema.get("properties", {}):
                continue

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
        if pydantic_version < namespace_refactored_pydantic_version:
            generator = GenerateSchema(
                config_wrapper=ConfigWrapper(config={}), types_namespace=None  # type: ignore
            )
        else:
            generator = GenerateSchema(config_wrapper=ConfigWrapper(config={}))  # type: ignore

        for expansion_name, expansion in fieldsets.items():
            if not isinstance(expansion, ExpansionBase):
                continue

            if expansion.response_model is None:
                continue

            target_type = self.find_first_non_annotated_type(expansion.response_model)
            self.cache_inner_target_refs(target_type, generator)

            expansion_description = (
                f"Request by name or using fieldset(s): `{expansion_name}`."
            )

            if isclass(target_type) and issubclass(target_type, BaseModel):
                model_schema: Optional[CoreSchema] = generator._model_schema(
                    target_type
                )
                if not model_schema:
                    raise TypeError(
                        f"Could not find model schema for {type(target_type)}"
                    )

                defs_ref = self.get_defs_ref((model_schema["schema_ref"], self.mode))
                title = (
                    self.definitions.get(defs_ref, {}).get("title") or expansion_name
                )

                expansion_schema = {
                    "title": title,
                    "$ref": self.ref_template.format(model=defs_ref),
                }
            else:
                core_schema = generator.match_type(target_type)
                expansion_schema = self.generate_inner(core_schema)
                expansion_schema["title"] = (
                    self.find_first_ref_title(expansion_schema) or expansion_name
                )

            json_schema["properties"][expansion_name] = {
                "description": expansion_description,
                **expansion_schema,
            }

        return json_schema

    def find_first_ref_title(self, schema: Any) -> Optional[str]:
        if (
            isinstance(schema, dict)
            and "$ref" in schema
            and (
                sub_schema := self.definitions.get(schema["$ref"][DEFS_PREFIX_LENGTH:])
            )
        ):
            return sub_schema.get("title")

        if isinstance(schema, dict):
            for value in schema.values():
                if title := self.find_first_ref_title(value):
                    return title

        if isinstance(schema, list):
            # in list cases, picking the first, or any, model is wrong, let the
            # caller use something more generic UNLESS this is an Optional:
            # (anyOf [Something, null])
            if (
                len(schema) == 2
                and schema[0].get("type") != "null"
                and schema[1].get("type") == "null"
            ):
                return self.find_first_ref_title(schema[0])

            return None

        return None

    def find_first_non_annotated_type(self, target_type: Any) -> Any:
        if get_origin(target_type) == Annotated:
            return self.find_first_non_annotated_type(get_args(target_type)[0])

        return target_type

    def cache_inner_target_refs(self, target_type: Any, generator) -> None:
        target_type = self.find_first_non_annotated_type(target_type)

        if _is_optional(target_type):
            target_type = _get_optional_type(target_type)

        if get_origin(target_type) == Union:
            for sub_target in get_args(target_type):
                self.cache_inner_target_refs(sub_target, generator)

        if _is_list(target_type) and (list_args := get_args(target_type)):
            self.cache_inner_target_refs(list_args[0], generator)

        if (
            isclass(get_origin(target_type))
            and issubclass(get_origin(target_type), (dict, Dict))
            and (dict_args := get_args(target_type))
            and len(dict_args) == 2
        ):
            self.cache_inner_target_refs(dict_args[1], generator)

        if isclass(target_type) and issubclass(target_type, BaseModel):
            model_schema: Optional[CoreSchema] = generator._model_schema(target_type)
            if not model_schema:
                raise TypeError(f"Could not find model schema for {type(target_type)}")

            defs_ref = self.get_defs_ref((model_schema["schema_ref"], self.mode))
            if defs_ref not in self.definitions:
                # guard against recursion on the same object
                self.definitions[defs_ref] = {}
                self.generate_inner(target_type.__pydantic_core_schema__)  # type: ignore


def _concat_description(description: Optional[str], additional: str) -> str:
    if description is None:
        return additional

    if description.endswith("."):
        return " ".join([description, additional])
    else:
        return ". ".join([description, additional])


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


def _is_list(type_: Any) -> bool:
    return bool(
        (origin := get_origin(type_))
        and isclass(origin)
        and issubclass(get_origin(type_), (list, List, set, Set))
    )


def model_has_fieldsets_defined(model: Any) -> bool:
    if _is_optional(model):
        model = _get_optional_type(model)

    if isclass(model) and issubclass(model, BaseModel):
        if getattr(model, "fieldset_config", None):
            return True

        else:
            return any(
                [
                    model_has_fieldsets_defined(field.annotation)
                    for field in model.model_fields.values()
                ]
            )

    return False
