from typing import Any, Awaitable, List

import pytest
from aiodataloader import DataLoader  # type: ignore
from pydantic import BaseModel

from pydantic_sparsefields import ModelExpansion

from .utils import assert_expected_rendered_fieldset_data


def test_singleton_expansion() -> None:
    class ExpandedModel(BaseModel):
        thing: str
        thing2: str

        class Config:
            fieldsets: dict = {}

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        class Config:
            fieldsets = {
                "zoom": ModelExpansion(expansion_method_name="get_zoom"),
            }

    api_response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(
        api_response,
        ["zoom.thing", "zoom.thing2"],
        {"zoom": {"thing": "what!", "thing2": "red"}},
    )


def test_nested_singleton_expansion() -> None:
    class SubExpandedModel(BaseModel):
        field1: str

    class ExpandedModel(BaseModel):
        thing: str
        thing2: str

        def get_sub(self, context: Any) -> SubExpandedModel:
            return SubExpandedModel(field1="foo")

        class Config:
            fieldsets = {"sub": ModelExpansion(expansion_method_name="get_sub")}

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        class Config:
            fieldsets = {
                "zoom": ModelExpansion(expansion_method_name="get_zoom"),
            }

    api_response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom.sub"], {"zoom": {"sub": {"field1": "foo"}}}
    )


def test_dataloader_expansion() -> None:
    loader_call_count = 0

    class ExpandedModel(BaseModel):
        expanded_model_id: int
        field1: str

    async def batch_load_expanded_models(keys: List[int]):
        nonlocal loader_call_count
        loader_call_count += 1
        return list([ExpandedModel(expanded_model_id=k, field1=str(k)) for k in keys])

    class ItemDetail(BaseModel):
        item_id: int
        expanded_model_id: int
        fieldA: str

        def expand(self, context: dict) -> Awaitable:
            return context["dataloader"].load(self.item_id + 20)

        class Config:
            fieldsets = {
                "default": ["item_id", "expanded_model_id", "fieldA"],
                "expanded_model": ModelExpansion(
                    expansion_method_name="expand",
                ),
            }

    class ResponseModel(BaseModel):
        items: List[ItemDetail]

    api_response = ResponseModel(
        items=[
            ItemDetail(
                item_id=i,
                expanded_model_id=i + 20,
                fieldA=f"val{i}",
            )
            for i in range(5)
        ]
    )
    context = {"dataloader": DataLoader(batch_load_fn=batch_load_expanded_models)}

    assert_expected_rendered_fieldset_data(
        api_response,
        ["items.expanded_model"],
        {
            "items": [
                {
                    "item_id": i,
                    "expanded_model_id": i + 20,
                    "fieldA": f"val{i}",
                    "expanded_model": {
                        "expanded_model_id": i + 20,
                        "field1": str(i + 20),
                    },
                }
                for i in range(5)
            ]
        },
        context,
    )

    # Super important, make sure we are coalescing all the data loader calls, since
    # it is easy to break batching
    assert loader_call_count == 1


def test_multi_dataloader_expansion() -> None:
    loader1_call_count = 0
    loader2_call_count = 0

    class ExpandedModel(BaseModel):
        expanded_model_id: int
        field1: str

    class ExpandedModel2(BaseModel):
        expanded_model2_id: int
        field2: str

    async def batch_load_expanded_models(keys: List[int]) -> Any:
        nonlocal loader1_call_count
        loader1_call_count += 1

        return list([ExpandedModel(expanded_model_id=k, field1=str(k)) for k in keys])

    async def batch_load_expanded_models2(keys: List[int]) -> Any:
        nonlocal loader2_call_count
        loader2_call_count += 1

        return list([ExpandedModel2(expanded_model2_id=k, field2=str(k)) for k in keys])

    class ItemDetail(BaseModel):
        item_id: int
        expanded_model_id: int
        expanded_model2_id: int
        fieldA: str

        def expand_model(self, context: Any) -> Awaitable:
            return context["dataloader1"].load(self.item_id + 20)

        def expand_model2(self, context: Any) -> Awaitable:
            return context["dataloader2"].load(self.item_id + 40)

        class Config:
            fieldsets = {
                "default": ["item_id", "expanded_model_id", "fieldA"],
                "expanded_model": ModelExpansion(
                    expansion_method_name="expand_model",
                ),
                "expanded_model2": ModelExpansion(
                    expansion_method_name="expand_model2",
                ),
            }

    class ResponseModel(BaseModel):
        items: List[ItemDetail]

    api_response = ResponseModel(
        items=[
            ItemDetail(
                item_id=i,
                expanded_model_id=i + 20,
                expanded_model2_id=i + 40,
                fieldA=f"val{i}",
            )
            for i in range(5)
        ]
    )

    context = {
        "dataloader1": DataLoader(batch_load_fn=batch_load_expanded_models),
        "dataloader2": DataLoader(batch_load_fn=batch_load_expanded_models2),
    }

    assert_expected_rendered_fieldset_data(
        api_response,
        ["items.expanded_model", "items.expanded_model2"],
        {
            "items": [
                {
                    "item_id": i,
                    "expanded_model_id": i + 20,
                    "fieldA": f"val{i}",
                    "expanded_model": {
                        "expanded_model_id": i + 20,
                        "field1": str(i + 20),
                    },
                    "expanded_model2": {
                        "expanded_model2_id": i + 40,
                        "field2": str(i + 40),
                    },
                }
                for i in range(5)
            ]
        },
        context,
    )

    # Super important, make sure we are coalescing all the data loader calls, since
    # it is easy to break batching
    assert loader1_call_count == 1
    assert loader2_call_count == 1


def test_dataloader_expansion_nested() -> None:
    loader1_call_count = 0
    loader2_call_count = 0

    class ExpandedModel2(BaseModel):
        expanded_model2_id: int
        field2: str

    async def batch_load_expanded_models2(keys: List[int]) -> List[ExpandedModel2]:
        nonlocal loader2_call_count
        loader2_call_count += 1

        return list([ExpandedModel2(expanded_model2_id=k, field2=str(k)) for k in keys])

    class ExpandedModel(BaseModel):
        expanded_model_id: int
        expanded_model2_id: int
        field1: str

        def expand_model2(self, context: dict) -> Awaitable:
            return context["dataloader2"].load(self.expanded_model2_id)

        class Config:
            fieldsets = {
                "default": ["expanded_model_id", "expanded_model2_id", "field1"],
                "expanded_model2": ModelExpansion(
                    expansion_method_name="expand_model2",
                ),
            }

    async def batch_load_expanded_models(keys: List[int]) -> List[ExpandedModel]:
        nonlocal loader1_call_count
        loader1_call_count += 1

        return list(
            [
                ExpandedModel(
                    expanded_model_id=k, expanded_model2_id=k + 20, field1=str(k)
                )
                for k in keys
            ]
        )

    class ItemDetail(BaseModel):
        item_id: int
        expanded_model_id: int
        fieldA: str

        def expand_model(self, context: dict) -> Awaitable:
            return context["dataloader1"].load(self.expanded_model_id)

        class Config:
            fieldsets = {
                "default": ["item_id", "expanded_model_id", "fieldA"],
                "expanded_model": ModelExpansion(
                    expansion_method_name="expand_model",
                ),
            }

    class ResponseModel(BaseModel):
        items: List[ItemDetail]

    api_response = ResponseModel(
        items=[
            ItemDetail(
                item_id=i,
                expanded_model_id=i + 20,
                fieldA=f"val{i}",
            )
            for i in range(5)
        ]
    )

    context = {
        "dataloader1": DataLoader(batch_load_fn=batch_load_expanded_models),
        "dataloader2": DataLoader(batch_load_fn=batch_load_expanded_models2),
    }

    assert_expected_rendered_fieldset_data(
        api_response,
        ["items.expanded_model", "items.expanded_model.expanded_model2"],
        {
            "items": [
                {
                    "item_id": i,
                    "expanded_model_id": i + 20,
                    "fieldA": f"val{i}",
                    "expanded_model": {
                        "expanded_model_id": i + 20,
                        "expanded_model2_id": i + 40,
                        "field1": str(i + 20),
                        "expanded_model2": {
                            "expanded_model2_id": i + 40,
                            "field2": str(i + 40),
                        },
                    },
                }
                for i in range(5)
            ]
        },
        context,
    )

    # Super important, make sure we are coalescing all the data loader calls, since
    # it is easy to break batching
    assert loader1_call_count == 1
    assert loader2_call_count == 1


def test_merge_upwards_models() -> None:
    class ExpandedModel(BaseModel):
        thing: str
        thing2: str

    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        class Config:
            fieldsets = {
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom.field1", "zoom"], {"thing": "what!", "thing2": "red"}
    )


def test_merge_upwards_dict() -> None:
    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> dict:
            return {"thing": "what!", "thing2": "red"}

        class Config:
            fieldsets = {
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom"], {"thing": "what!", "thing2": "red"}
    )


def test_merge_upwards_nested_models() -> None:
    class SubExpandedModel(BaseModel):
        field1: str
        field2: str

        class Config:
            fieldsets = {"default": ["field2"]}

    class ExpandedModel(BaseModel):
        thing: str
        thing2: str

        def get_sub(self, context: Any) -> SubExpandedModel:
            return SubExpandedModel(field1="f1", field2="f2")

        class Config:
            fieldsets = {
                "sub": ModelExpansion(
                    expansion_method_name="get_sub", merge_fields_upwards=True
                )
            }

    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        class Config:
            fieldsets = {
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom.sub.field1"], {"zoom": {"field1": "f1", "field2": "f2"}}
    )


def test_merge_upwards_nested_dicts() -> None:
    class ExpandedModel(BaseModel):
        thing: str
        thing2: str

        def get_sub(self, context: Any) -> dict:
            return {"field1": "f1", "field2": "f2"}

        class Config:
            fieldsets = {
                "sub": ModelExpansion(
                    expansion_method_name="get_sub", merge_fields_upwards=True
                )
            }

    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        class Config:
            fieldsets = {
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom.sub.field1"], {"zoom": {"field1": "f1", "field2": "f2"}}
    )


def test_expand_to_scalar_value() -> None:
    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> str:
            return "some scalar value"

        class Config:
            fieldsets = {"zoom": ModelExpansion(expansion_method_name="get_zoom")}

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom"], {"zoom": "some scalar value"}
    )


def test_expand_to_scalar_value_with_merge() -> None:
    class SubModel(BaseModel):
        def get_zoom(self, context: Any) -> str:
            return "some scalar value"

        class Config:
            fieldsets = {
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }

    class ResponseModel(BaseModel):
        sub: SubModel

    api_response = ResponseModel(sub=SubModel())

    with pytest.raises(ValueError) as exc:
        assert_expected_rendered_fieldset_data(api_response, ["sub.zoom"], {})

    assert "merge_fields_upwards=True" in str(exc.value)


def test_merge_upwards_lists() -> None:
    class SubExpandedModel(BaseModel):
        field1: str
        field2: str

        class Config:
            fieldsets = {"default": ["field2"]}

    class SubModel(BaseModel):
        thing: str
        thing2: str

        def get_sub(self, context: Any) -> SubExpandedModel:
            return SubExpandedModel(field1=self.thing + "f1", field2=self.thing2 + "f2")

        class Config:
            fieldsets = {
                "default": ["thing", "thing2"],
                "sub": ModelExpansion(
                    expansion_method_name="get_sub", merge_fields_upwards=True
                ),
            }

    class ResponseModel(BaseModel):
        items: List[SubModel]

    api_response = ResponseModel(
        items=[
            SubModel(thing="t1", thing2="t2"),
            SubModel(thing="t3", thing2="t4"),
        ]
    )

    assert_expected_rendered_fieldset_data(
        api_response,
        ["items.sub"],
        {
            "items": [
                {
                    "thing": "t1",
                    "thing2": "t2",
                    "field2": "t2f2",
                },
                {
                    "thing": "t3",
                    "thing2": "t4",
                    "field2": "t4f2",
                },
            ]
        },
    )


def test_expansion_returns_list() -> None:
    class ExpandedModel(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["field1"]}

    class ResponseModel(BaseModel):
        f1: str

        def get_sub(self, context: Any) -> List[ExpandedModel]:
            return [
                ExpandedModel(field1="field1value1"),
                ExpandedModel(field1="field1value2"),
                ExpandedModel(field1="field1value3"),
            ]

        class Config:
            fieldsets = {
                "default": ["f1"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }

    api_response = ResponseModel(f1="f1value")

    assert_expected_rendered_fieldset_data(
        api_response,
        ["sub"],
        {
            "f1": "f1value",
            "sub": [
                {"field1": "field1value1"},
                {"field1": "field1value2"},
                {"field1": "field1value3"},
            ],
        },
    )


def test_expansion_returns_list_nested() -> None:
    class SubExpandedModel(BaseModel):
        subfield1: str

    class ExpandedModel(BaseModel):
        field1: str

        def get_subsub(self, context: Any) -> List[SubExpandedModel]:
            return [
                SubExpandedModel(subfield1="subfield1value1"),
                SubExpandedModel(subfield1="subfield1value2"),
                SubExpandedModel(subfield1="subfield1value3"),
            ]

        class Config:
            fieldsets = {
                "default": ["field1"],
                "subsub": ModelExpansion(expansion_method_name="get_subsub"),
            }

    class ResponseModel(BaseModel):
        f1: str

        def get_sub(self, context: Any) -> List[ExpandedModel]:
            return [
                ExpandedModel(field1="field1value1"),
                ExpandedModel(field1="field1value2"),
                ExpandedModel(field1="field1value3"),
            ]

        class Config:
            fieldsets = {
                "default": ["f1"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }

    api_response = ResponseModel(f1="f1value")

    assert_expected_rendered_fieldset_data(
        api_response,
        ["sub", "sub.subsub"],
        {
            "f1": "f1value",
            "sub": [
                {
                    "field1": "field1value1",
                    "subsub": [
                        {"subfield1": "subfield1value1"},
                        {"subfield1": "subfield1value2"},
                        {"subfield1": "subfield1value3"},
                    ],
                },
                {
                    "field1": "field1value2",
                    "subsub": [
                        {"subfield1": "subfield1value1"},
                        {"subfield1": "subfield1value2"},
                        {"subfield1": "subfield1value3"},
                    ],
                },
                {
                    "field1": "field1value3",
                    "subsub": [
                        {"subfield1": "subfield1value1"},
                        {"subfield1": "subfield1value2"},
                        {"subfield1": "subfield1value3"},
                    ],
                },
            ],
        },
    )


def test_expansion_returns_list_of_list() -> None:
    class ExpandedModel(BaseModel):
        field1: str

        class Config:
            fieldsets = {"default": ["field1"]}

    class ResponseModel(BaseModel):
        f1: str

        def get_sub(self, context: Any) -> List[List[ExpandedModel]]:
            return [
                [
                    ExpandedModel(field1="field1value1"),
                    ExpandedModel(field1="field1value2"),
                ],
                [ExpandedModel(field1="field1value3")],
            ]

        class Config:
            fieldsets = {
                "default": ["f1"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }

    api_response = ResponseModel(f1="f1value")

    assert_expected_rendered_fieldset_data(
        api_response,
        ["sub"],
        {
            "f1": "f1value",
            "sub": [
                [{"field1": "field1value1"}, {"field1": "field1value2"}],
                [{"field1": "field1value3"}],
            ],
        },
    )
