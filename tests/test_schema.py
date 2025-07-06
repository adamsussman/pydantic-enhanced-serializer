from typing import Annotated, ClassVar, List, Optional, Union

from pydantic import BaseModel

from pydantic_enhanced_serializer import (
    FieldsetConfig,
    FieldsetGenerateJsonSchema,
    ModelExpansion,
)


def test_fields_in_fieldset() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str
        field3: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "extra": ["field1", "field2"],
                "extra2": ["field2", "field3"],
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert (
        schema["properties"]["field1"]["description"]
        == "Request by name or using fieldset(s): `extra`."
    )
    assert (
        schema["properties"]["field2"]["description"]
        == "Request by name or using fieldset(s): `extra`, `extra2`."
    )
    assert (
        schema["properties"]["field3"]["description"]
        == "Request by name or using fieldset(s): `extra2`."
    )


def test_fields_in_default() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str
        field3: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["field1", "field2"],
                "extra": ["field2", "field3"],
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]
    assert (
        schema["properties"]["field3"]["description"]
        == "Request by name or using fieldset(s): `extra`."
    )


def test_fields_star_default() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str
        field3: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["*"],
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]
    assert "description" not in schema["properties"]["field3"]


def test_fields_named_default() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str
        field3: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={"default": ["field1", "field2", "field3"]}
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]
    assert "description" not in schema["properties"]["field3"]


def test_sub_object() -> None:
    class SubThing(BaseModel):
        sfield1: str
        sfield2: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "f1": ["sfield1"],
                "f2": ["sfield1", "sfield2"],
            }
        )

    class Thing(BaseModel):
        field1: str
        field2: SubThing

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={"default": ["field1", "field2"]}
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]

    assert "SubThing" in schema["$defs"]
    assert (
        schema["$defs"]["SubThing"]["properties"]["sfield1"]["description"]
        == "Request by name or using fieldset(s): `f1`, `f2`."
    )
    assert (
        schema["$defs"]["SubThing"]["properties"]["sfield2"]["description"]
        == "Request by name or using fieldset(s): `f2`."
    )


def test_sub_object_list() -> None:
    class SubThing(BaseModel):
        sfield1: str
        sfield2: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "f1": ["sfield1"],
                "f2": ["sfield1", "sfield2"],
            }
        )

    class Thing(BaseModel):
        field1: str
        field2: List[SubThing]

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={"default": ["field1", "field2"]}
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]

    assert "SubThing" in schema["$defs"]
    assert (
        schema["$defs"]["SubThing"]["properties"]["sfield1"]["description"]
        == "Request by name or using fieldset(s): `f1`, `f2`."
    )
    assert (
        schema["$defs"]["SubThing"]["properties"]["sfield2"]["description"]
        == "Request by name or using fieldset(s): `f2`."
    )


def test_expansion_model() -> None:
    class ExpandedThing(BaseModel):
        efield1: str
        efield2: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "f1": ["efield1", "efield2"],
                "f2": ["efield2"],
            }
        )

    from pydantic import Field

    class Thing(BaseModel):
        field1: str
        boo: ExpandedThing = Field(description="yo!")

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=ExpandedThing,
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]
    assert schema["$defs"]
    assert "ExpandedThing" in schema["$defs"]
    assert "properties" in schema["$defs"]["ExpandedThing"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "ExpandedThing",
        "description": "Request by name or using fieldset(s): `expando`.",
        "$ref": "#/$defs/ExpandedThing",
    }


def test_expansion_model_list() -> None:
    class ExpandedThing(BaseModel):
        efield1: str
        efield2: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "f1": ["efield1", "efield2"],
                "f2": ["efield2"],
            }
        )

    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=List[ExpandedThing],
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "ExpandedThing",
        "description": "Request by name or using fieldset(s): `expando`.",
        "type": "array",
        "items": {
            "$ref": "#/$defs/ExpandedThing",
        },
    }


def test_expansion_scalar() -> None:
    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=int,
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "expando",
        "description": "Request by name or using fieldset(s): `expando`.",
        "type": "integer",
    }


def test_expansion_scalar_list() -> None:
    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=List[int],
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "expando",
        "description": "Request by name or using fieldset(s): `expando`.",
        "type": "array",
        "items": {
            "type": "integer",
        },
    }


def test_optional_expansion_response_model() -> None:
    class Expanded(BaseModel):
        efield1: str

    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo", response_model=Optional[Expanded]
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)

    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "Expanded",
        "description": "Request by name or using fieldset(s): `expando`.",
        "anyOf": [{"$ref": "#/$defs/Expanded"}, {"type": "null"}],
    }


def test_unfieldseted_field_description() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["field1"],
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)

    assert schema
    assert schema["properties"]

    assert "field2" in schema["properties"]
    assert schema["properties"]["field2"] == {
        "title": "Field2",
        "description": "Not returned by default.  Request this field by name.",
        "type": "string",
    }


def test_expansion_union_response() -> None:
    class ExpandedA(BaseModel):
        efield1: str

    class ExpandedB(BaseModel):
        efield2: str

    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=Union[ExpandedA, ExpandedB],
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)

    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "expando",
        "description": "Request by name or using fieldset(s): `expando`.",
        "anyOf": [{"$ref": "#/$defs/ExpandedA"}, {"$ref": "#/$defs/ExpandedB"}],
    }


def test_expansion_annotated_union_response() -> None:
    class ExpandedA(BaseModel):
        efield1: str

    class ExpandedB(BaseModel):
        efield2: str

    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=Annotated[Union[ExpandedA, ExpandedB], "blank"],
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)

    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "expando",
        "description": "Request by name or using fieldset(s): `expando`.",
        "anyOf": [{"$ref": "#/$defs/ExpandedA"}, {"$ref": "#/$defs/ExpandedB"}],
    }


def test_expansion_list_union_response() -> None:
    class ExpandedA(BaseModel):
        efield1: str

    class ExpandedB(BaseModel):
        efield2: str

    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=List[Union[ExpandedA, ExpandedB]],
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)

    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "expando",
        "description": "Request by name or using fieldset(s): `expando`.",
        "type": "array",
        "items": {
            "anyOf": [{"$ref": "#/$defs/ExpandedA"}, {"$ref": "#/$defs/ExpandedB"}],
        },
    }


def test_expansion_annotated_list_union_response() -> None:
    class ExpandedA(BaseModel):
        efield1: str

    class ExpandedB(BaseModel):
        efield2: str

    class Thing(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=Annotated[List[Union[ExpandedA, ExpandedB]], "blah"],
                )
            }
        )

    schema = Thing.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)

    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "expando",
        "description": "Request by name or using fieldset(s): `expando`.",
        "type": "array",
        "items": {
            "anyOf": [{"$ref": "#/$defs/ExpandedA"}, {"$ref": "#/$defs/ExpandedB"}],
        },
    }
