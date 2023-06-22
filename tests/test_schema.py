from typing import List, Optional

from pydantic import BaseModel

from pydantic_enhanced_serializer import ModelExpansion, augment_schema_with_fieldsets


def test_fields_in_fieldset() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {
                "extra": ["field1", "field2"],
                "extra2": ["field2", "field3"],
            }

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert (
        schema["properties"]["field1"]["description"]
        == "Request using fieldset(s): `extra`."
    )
    assert (
        schema["properties"]["field2"]["description"]
        == "Request using fieldset(s): `extra`, `extra2`."
    )
    assert (
        schema["properties"]["field3"]["description"]
        == "Request using fieldset(s): `extra2`."
    )


def test_fields_in_default() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {
                "default": ["field1", "field2"],
                "extra": ["field2", "field3"],
            }

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert (
        schema["properties"]["field2"]["description"]
        == "Request using fieldset(s): `extra`."
    )
    assert (
        schema["properties"]["field3"]["description"]
        == "Request using fieldset(s): `extra`."
    )


def test_fields_star_default() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {
                "default": ["*"],
            }

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
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

        class Config:
            fieldsets = {"default": ["field1", "field2", "field3"]}

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]
    assert "description" not in schema["properties"]["field3"]


def test_sub_object() -> None:
    class SubThing(BaseModel):
        sfield1: str
        sfield2: str

        class Config:
            fieldsets = {
                "f1": ["sfield1"],
                "f2": ["sfield1", "sfield2"],
            }

    class Thing(BaseModel):
        field1: str
        field2: SubThing

        class Config:
            fieldsets = {"default": ["field1", "field2"]}

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]

    assert "SubThing" in schema["definitions"]
    assert (
        schema["definitions"]["SubThing"]["properties"]["sfield1"]["description"]
        == "Request using fieldset(s): `f1`, `f2`."
    )
    assert (
        schema["definitions"]["SubThing"]["properties"]["sfield2"]["description"]
        == "Request using fieldset(s): `f2`."
    )


def test_sub_object_list() -> None:
    class SubThing(BaseModel):
        sfield1: str
        sfield2: str

        class Config:
            fieldsets = {
                "f1": ["sfield1"],
                "f2": ["sfield1", "sfield2"],
            }

    class Thing(BaseModel):
        field1: str
        field2: List[SubThing]

        class Config:
            fieldsets = {"default": ["field1", "field2"]}

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "description" not in schema["properties"]["field1"]
    assert "description" not in schema["properties"]["field2"]

    assert "SubThing" in schema["definitions"]
    assert (
        schema["definitions"]["SubThing"]["properties"]["sfield1"]["description"]
        == "Request using fieldset(s): `f1`, `f2`."
    )
    assert (
        schema["definitions"]["SubThing"]["properties"]["sfield2"]["description"]
        == "Request using fieldset(s): `f2`."
    )


def test_expansion_model() -> None:
    class ExpandedThing(BaseModel):
        efield1: str
        efield2: str

        class Config:
            fieldsets = {
                "f1": ["efield1", "efield2"],
                "f2": ["efield2"],
            }

    class Thing(BaseModel):
        field1: str

        class Config:
            fieldsets = {
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=ExpandedThing,
                )
            }

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "Expando",
        "description": "Request using fieldset(s): `expando`.",
        "$ref": "#/components/schemas/ExpandedThing",
    }


def test_expansion_model_list() -> None:
    class ExpandedThing(BaseModel):
        efield1: str
        efield2: str

        class Config:
            fieldsets = {
                "f1": ["efield1", "efield2"],
                "f2": ["efield2"],
            }

    class Thing(BaseModel):
        field1: str

        class Config:
            fieldsets = {
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=List[ExpandedThing],
                )
            }

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "Expando",
        "description": "Request using fieldset(s): `expando`.",
        "type": "array",
        "items": {
            "$ref": "#/components/schemas/ExpandedThing",
        },
    }


def test_expansion_scalar() -> None:
    class Thing(BaseModel):
        field1: str

        class Config:
            fieldsets = {
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=int,
                )
            }

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "Expando",
        "description": "Request using fieldset(s): `expando`.",
        "type": "integer",
    }


def test_expansion_scalar_list() -> None:
    class Thing(BaseModel):
        field1: str

        class Config:
            fieldsets = {
                "expando": ModelExpansion(
                    expansion_method_name="foo",
                    response_model=List[int],
                )
            }

    augment_schema_with_fieldsets(Thing)

    schema = Thing.schema()
    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "Expando",
        "description": "Request using fieldset(s): `expando`.",
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

        class Config:
            fieldsets = {
                "expando": ModelExpansion(
                    expansion_method_name="foo", response_model=Optional[Expanded]
                )
            }

    augment_schema_with_fieldsets(Thing)
    schema = Thing.schema()

    assert schema
    assert schema["properties"]

    assert "expando" in schema["properties"]
    assert schema["properties"]["expando"] == {
        "title": "Expando",
        "description": "Request using fieldset(s): `expando`.",
        "$ref": "#/components/schemas/Expanded",
    }


def test_unfieldseted_field_description() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str

        class Config:
            fieldsets = {
                "default": ["field1"],
            }

    augment_schema_with_fieldsets(Thing)
    schema = Thing.schema()

    assert schema
    assert schema["properties"]

    assert "field2" in schema["properties"]
    assert schema["properties"]["field2"] == {
        "title": "Field2",
        "description": "Not returned by default.  Request this field by name.",
        "type": "string",
    }
