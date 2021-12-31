import re
from typing import List

from pydantic import BaseModel

from pydantic_sparsefields import ModelExpansion, augment_schema_with_fieldsets


def test_schema_augment_reponse_description() -> None:
    class ExpandedThing(BaseModel):
        ex1: str
        ex2: str

        class Config:
            fieldsets = {"default": ["ex1", "ex2"]}

    class Response(BaseModel):
        """Regular docstring here"""

        field1: str
        field2: str
        field3: int

        class Config:
            fieldsets = {
                "default": ["field1", "field2"],
                "extra": ["field3"],
                "thing": ModelExpansion(
                    expansion_method_name="foo", response_model=ExpandedThing
                ),
            }

    augment_schema_with_fieldsets(Response)

    response_schema = Response.schema()
    assert response_schema
    assert "Regular docstring here" in response_schema["description"]
    assert "Available fieldsets and expansions" in response_schema["description"]
    assert re.search(
        r"Default Fields:.* field1, field2",
        response_schema["description"],
    )
    assert re.search(r"extra.* field3", response_schema["description"])
    assert re.search(
        r"thing.* Expansion of type ExpandedThing",
        response_schema["description"],
    )

    expanded_schema = ExpandedThing.schema()
    assert expanded_schema
    assert expanded_schema["description"]
    assert "Available fieldsets and expansions" in expanded_schema["description"]
    assert re.search(
        r"Default Fields:.* ex1, ex2",
        expanded_schema["description"],
    )


def test_schema_augment_reponse_nested_description() -> None:
    class Item(BaseModel):
        """Regular docstring here"""

        field1: str
        field2: str

        class Config:
            fieldsets = {"default": ["field1", "field2"]}

    class Response(BaseModel):
        item: Item

        # Test here is top level response does NOT have a config!

    augment_schema_with_fieldsets(Response)
    item_schema = Item.schema()

    assert item_schema
    assert item_schema["description"]

    assert re.search(
        r"Default Fields:.* field1, field2",
        item_schema["description"],
    )


def test_schema_augment_reponse_nested_description_lists() -> None:
    class Input(BaseModel):
        input1: str
        input2: str

    class Item(BaseModel):
        """Regular docstring here"""

        field1: str
        field2: str

        class Config:
            fieldsets = {"default": ["field1", "field2"]}

    class Response(BaseModel):
        item: List[Item]

        # Test here is top level response does NOT have a config!

    augment_schema_with_fieldsets(Response)

    item_schema = Item.schema()

    assert item_schema
    assert item_schema["description"]
    assert re.search(
        r"Default Fields:.* field1, field2",
        item_schema["description"],
    )
