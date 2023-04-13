from typing import Dict, List, Optional

from pydantic import BaseModel

from pydantic_enhanced_serializer.schema import model_has_fieldsets_defined


def test_model_has_fieldsets_defined_not() -> None:
    class Thing(BaseModel):
        field1: str

    assert not model_has_fieldsets_defined(Thing)


def test_model_has_fieldsets_defined() -> None:
    class Thing(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["*"]}

    assert model_has_fieldsets_defined(Thing)


def test_submodel_has_fieldsets_defined() -> None:
    class SubThing(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["*"]}

    class Thing(BaseModel):
        field1: str
        field2: SubThing

    assert model_has_fieldsets_defined(Thing)


def test_optional_submodel_has_fieldsets_defined() -> None:
    class SubThing(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["*"]}

    class Thing(BaseModel):
        field1: str
        field2: Optional[SubThing]

    assert model_has_fieldsets_defined(Thing)


def test_list_submodel_has_fieldsets_defined() -> None:
    class SubThing(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["*"]}

    class Thing(BaseModel):
        field1: str
        field2: List[SubThing]

    assert model_has_fieldsets_defined(Thing)


def test_list_optional_submodel_has_fieldsets_defined() -> None:
    class SubThing(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["*"]}

    class Thing(BaseModel):
        field1: str
        field2: List[Optional[SubThing]]

    assert model_has_fieldsets_defined(Thing)


def test_dict_optional_submodel_has_fieldsets_defined() -> None:
    class SubThing(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["*"]}

    class Thing(BaseModel):
        field1: str
        field2: Dict[str, Optional[SubThing]]

    assert model_has_fieldsets_defined(Thing)


def test_dict_submodel_has_fieldsets_defined() -> None:
    class SubThing(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["*"]}

    class Thing(BaseModel):
        field1: str
        field2: Dict[str, SubThing]

    assert model_has_fieldsets_defined(Thing)
