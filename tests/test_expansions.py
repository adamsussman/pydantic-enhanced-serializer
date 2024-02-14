import datetime
from typing import Any, Awaitable, ClassVar, Dict, List, Optional

import pytest
from aiodataloader import DataLoader  # type: ignore
from pydantic import BaseModel, ConfigDict, Field

from pydantic_enhanced_serializer import FieldsetConfig, ModelExpansion

from .utils import assert_expected_rendered_fieldset_data


def test_singleton_expansion() -> None:
    class ExpandedModel(BaseModel):
        thing: str
        thing2: str

        fieldset_config: ClassVar = FieldsetConfig(fieldsets={})

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "zoom": ModelExpansion(expansion_method_name="get_zoom"),
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "sub": ModelExpansion(
                    response_model=SubExpandedModel, expansion_method_name="get_sub"
                )
            },
        )

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "zoom": ModelExpansion(
                    response_model=ExpandedModel, expansion_method_name="get_zoom"
                ),
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["item_id", "expanded_model_id", "fieldA"],
                "expanded_model": ModelExpansion(
                    expansion_method_name="expand",
                ),
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["item_id", "expanded_model_id", "fieldA"],
                "expanded_model": ModelExpansion(
                    expansion_method_name="expand_model",
                ),
                "expanded_model2": ModelExpansion(
                    expansion_method_name="expand_model2",
                ),
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["expanded_model_id", "expanded_model2_id", "field1"],
                "expanded_model2": ModelExpansion(
                    expansion_method_name="expand_model2",
                ),
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["item_id", "expanded_model_id", "fieldA"],
                "expanded_model": ModelExpansion(
                    expansion_method_name="expand_model",
                ),
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }
        )

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom.field1", "zoom"], {"thing": "what!", "thing2": "red"}
    )


def test_merge_upwards_dict() -> None:
    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> dict:
            return {"thing": "what!", "thing2": "red"}

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }
        )

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom"], {"thing": "what!", "thing2": "red"}
    )


def test_merge_upwards_nested_models() -> None:
    class SubExpandedModel(BaseModel):
        field1: str
        field2: str

        fieldset_config: ClassVar = FieldsetConfig(fieldsets={"default": ["field2"]})

    class ExpandedModel(BaseModel):
        thing: str
        thing2: str

        def get_sub(self, context: Any) -> SubExpandedModel:
            return SubExpandedModel(field1="f1", field2="f2")

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "sub": ModelExpansion(
                    expansion_method_name="get_sub", merge_fields_upwards=True
                )
            }
        )

    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "sub": ModelExpansion(
                    expansion_method_name="get_sub", merge_fields_upwards=True
                )
            }
        )

    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> ExpandedModel:
            return ExpandedModel(thing="what!", thing2="red")

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }
        )

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom.sub.field1"], {"zoom": {"field1": "f1", "field2": "f2"}}
    )


def test_expand_to_scalar_value() -> None:
    class ResponseModel(BaseModel):
        def get_zoom(self, context: Any) -> str:
            return "some scalar value"

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={"zoom": ModelExpansion(expansion_method_name="get_zoom")}
        )

    api_response = ResponseModel()

    assert_expected_rendered_fieldset_data(
        api_response, ["zoom"], {"zoom": "some scalar value"}
    )


def test_expand_to_scalar_value_with_merge() -> None:
    class SubModel(BaseModel):
        def get_zoom(self, context: Any) -> str:
            return "some scalar value"

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "zoom": ModelExpansion(
                    expansion_method_name="get_zoom", merge_fields_upwards=True
                )
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(fieldsets={"default": ["field2"]})

    class SubModel(BaseModel):
        thing: str
        thing2: str

        def get_sub(self, context: Any) -> SubExpandedModel:
            return SubExpandedModel(field1=self.thing + "f1", field2=self.thing2 + "f2")

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["thing", "thing2"],
                "sub": ModelExpansion(
                    expansion_method_name="get_sub", merge_fields_upwards=True
                ),
            }
        )

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

        fieldset_config: ClassVar = FieldsetConfig(fieldsets={"default": ["field1"]})

    class ResponseModel(BaseModel):
        f1: str

        def get_sub(self, context: Any) -> List[ExpandedModel]:
            return [
                ExpandedModel(field1="field1value1"),
                ExpandedModel(field1="field1value2"),
                ExpandedModel(field1="field1value3"),
            ]

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["f1"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }
        )

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
                SubExpandedModel(subfield1=f"{self.field1}_subvalue1"),
                SubExpandedModel(subfield1=f"{self.field1}_subvalue2"),
                SubExpandedModel(subfield1=f"{self.field1}_subvalue3"),
            ]

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["field1"],
                "subsub": ModelExpansion(expansion_method_name="get_subsub"),
            }
        )

    class ResponseModel(BaseModel):
        f1: str

        def get_sub(self, context: Any) -> List[ExpandedModel]:
            return [
                ExpandedModel(field1="field1value1"),
                ExpandedModel(field1="field1value2"),
                ExpandedModel(field1="field1value3"),
            ]

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["f1"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }
        )

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
                        {"subfield1": "field1value1_subvalue1"},
                        {"subfield1": "field1value1_subvalue2"},
                        {"subfield1": "field1value1_subvalue3"},
                    ],
                },
                {
                    "field1": "field1value2",
                    "subsub": [
                        {"subfield1": "field1value2_subvalue1"},
                        {"subfield1": "field1value2_subvalue2"},
                        {"subfield1": "field1value2_subvalue3"},
                    ],
                },
                {
                    "field1": "field1value3",
                    "subsub": [
                        {"subfield1": "field1value3_subvalue1"},
                        {"subfield1": "field1value3_subvalue2"},
                        {"subfield1": "field1value3_subvalue3"},
                    ],
                },
            ],
        },
    )


def test_expansion_returns_list_of_list() -> None:
    class ExpandedModel(BaseModel):
        field1: str

        fieldset_config: ClassVar = FieldsetConfig(fieldsets={"default": ["field1"]})

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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["f1"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }
        )

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


def test_expand_empty_list() -> None:
    class ResponseModel(BaseModel):
        f1: str

        def get_sub(self, context: Any) -> List[int]:
            return []

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["f1"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }
        )

    api_response = ResponseModel(f1="f1value")

    assert_expected_rendered_fieldset_data(
        api_response,
        ["sub"],
        {"f1": "f1value", "sub": []},
    )


def test_expansion_in_default_fieldset() -> None:
    class SubModelBase(BaseModel):
        f1: str

    class SubModel(SubModelBase):
        f2: str
        f3: str
        f4: str
        f5: str
        f6: str
        f7: str

        def get_sub(self, context: Any) -> str:
            return "sub" + self.f1

        model_config = ConfigDict(from_attributes=True)

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["f1", "f2", "sub"],
                "g1": ["f3"],
                "g2": ["f4", "f5"],
                "sub": ModelExpansion(expansion_method_name="get_sub"),
            }
        )

    class ResponseModel(BaseModel):
        subs: List[SubModel]

    response = ResponseModel(
        subs=[
            SubModel(
                f1="f1.1",
                f2="f1.2",
                f3="f1.3",
                f4="f1.4",
                f5="f1.5",
                f6="f1.6",
                f7="f1.7",
            ),
            SubModel(
                f1="f2.1",
                f2="f2.2",
                f3="f2.3",
                f4="f2.4",
                f5="f2.5",
                f6="f2.6",
                f7="f2.7",
            ),
        ]
    )

    assert_expected_rendered_fieldset_data(
        response,
        ["subs.g1", "subs.g2", "subs.sub", "subs.f6", "subs.f7"],
        {
            "subs": [
                {
                    "f1": "f1.1",
                    "f2": "f1.2",
                    "f3": "f1.3",
                    "f4": "f1.4",
                    "f5": "f1.5",
                    "f6": "f1.6",
                    "f7": "f1.7",
                    "sub": "subf1.1",
                },
                {
                    "f1": "f2.1",
                    "f2": "f2.2",
                    "f3": "f2.3",
                    "f4": "f2.4",
                    "f5": "f2.5",
                    "f6": "f2.6",
                    "f7": "f2.7",
                    "sub": "subf2.1",
                },
            ]
        },
    )


def test_nested_array_expansion_overlap() -> None:
    # Expansions should not overwrite request fields where the request
    # field is a standalone field not part of other fieldset groups

    class SubEntity(BaseModel):
        addr: str

    class Struct(BaseModel):
        num_stuff: int

    class Entity(BaseModel):
        entity_id: str
        structure: Optional[Struct]
        created: datetime.datetime

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["entity_id"],
                "sub_entity": ModelExpansion(
                    response_model=SubEntity, expansion_method_name="get_sub_entity"
                ),
                "timestamps": ["created"],
            }
        )

        def get_sub_entity(self, context: Any) -> SubEntity:
            return SubEntity(addr="somewhere")

    now = datetime.datetime.now()

    class Thing(BaseModel):
        thing_id: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["thing_id"],
                "entities": ModelExpansion(
                    response_model=List[Entity],
                    expansion_method_name="get_entities",
                ),
            }
        )

        def get_entities(self, context: Any) -> List[Entity]:
            return [
                Entity(entity_id="foo", structure=Struct(num_stuff=11), created=now)
            ]

    class Response(BaseModel):
        thing: Thing

    response = Response(thing=Thing(thing_id="bar"))

    assert_expected_rendered_fieldset_data(
        response,
        [
            "thing.entities.sub_entity",
            "thing.entities.structure",
            "thing.entities.timestamps",
        ],
        {
            "thing": {
                "thing_id": "bar",
                "entities": [
                    {
                        "entity_id": "foo",
                        "sub_entity": {
                            "addr": "somewhere",
                        },
                        "structure": {
                            "num_stuff": 11,
                        },
                        "created": now,
                    }
                ],
            }
        },
    )


def test_nested_expansion_dict_vary_keys() -> None:
    class Storey(BaseModel):
        s_attr1: str
        component_counts: Optional[Dict[str, int]]

    class ItemStructure(BaseModel):
        attr1: str
        storeys: List[Storey] = Field(min_length=1)

    class Item(BaseModel):
        item_id: str
        structure: Optional[ItemStructure] = None

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["item_id"],
            }
        )

    class Thing(BaseModel):
        thing_id: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["thing_id"],
                "items": ModelExpansion(
                    response_model=List[Item],
                    expansion_method_name="get_items",
                ),
            }
        )

        def get_items(self, context: Any) -> List[Item]:
            return [
                Item(
                    item_id="1234",
                    structure=ItemStructure(
                        attr1="a_val1",
                        storeys=[
                            Storey(
                                s_attr1="Floor 1-1",
                                component_counts={
                                    "key11": 11,
                                    "key12": 12,
                                },
                            ),
                            Storey(
                                s_attr1="Floor 1-2",
                                component_counts={
                                    "key21": 21,
                                    "key22": 22,
                                    "key23": 23,
                                },
                            ),
                        ],
                    ),
                ),
                Item(
                    item_id="5678",
                    structure=ItemStructure(
                        attr1="a_val2",
                        storeys=[
                            Storey(
                                s_attr1="Floor 2-1",
                                component_counts={
                                    "key211": 211,
                                    "key212": 212,
                                },
                            ),
                            Storey(
                                s_attr1="Floor 2-2",
                                component_counts={
                                    "key221": 221,
                                    "key222": 222,
                                    "key223": 223,
                                },
                            ),
                            Storey(
                                s_attr1="Floor 3-2",
                                component_counts={
                                    "key321": 321,
                                    "key322": 322,
                                    "key323": 323,
                                    "key324": 324,
                                },
                            ),
                        ],
                    ),
                ),
            ]

    class Response(BaseModel):
        thing: Thing

    response = Response(
        thing=Thing(
            thing_id="abc",
        )
    )

    assert_expected_rendered_fieldset_data(
        response,
        [
            "thing.items.structure",
        ],
        {
            "thing": {
                "thing_id": "abc",
                "items": [
                    {
                        "item_id": "1234",
                        "structure": {
                            "attr1": "a_val1",
                            "storeys": [
                                {
                                    "s_attr1": "Floor 1-1",
                                    "component_counts": {
                                        "key11": 11,
                                        "key12": 12,
                                    },
                                },
                                {
                                    "s_attr1": "Floor 1-2",
                                    "component_counts": {
                                        "key21": 21,
                                        "key22": 22,
                                        "key23": 23,
                                    },
                                },
                            ],
                        },
                    },
                    {
                        "item_id": "5678",
                        "structure": {
                            "attr1": "a_val2",
                            "storeys": [
                                {
                                    "s_attr1": "Floor 2-1",
                                    "component_counts": {
                                        "key211": 211,
                                        "key212": 212,
                                    },
                                },
                                {
                                    "s_attr1": "Floor 2-2",
                                    "component_counts": {
                                        "key221": 221,
                                        "key222": 222,
                                        "key223": 223,
                                    },
                                },
                                {
                                    "s_attr1": "Floor 3-2",
                                    "component_counts": {
                                        "key321": 321,
                                        "key322": 322,
                                        "key323": 323,
                                        "key324": 324,
                                    },
                                },
                            ],
                        },
                    },
                ],
            }
        },
    )


def test_dict_nested_list_dicts() -> None:
    class Thing(BaseModel):
        str1: str

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets={
                "default": ["str1"],
                "subdata": ModelExpansion(
                    response_model=Optional[Dict[str, Any]],
                    expansion_method_name="get_subdata",
                ),
            }
        )

        def get_subdata(self, *args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
            return {
                "list": [
                    {
                        "a": "b",
                    }
                ]
            }

    class ThingContainer(BaseModel):
        things: List[Thing]

    thing = Thing(
        str1="foo",
    )

    things = ThingContainer(things=[thing, thing])

    assert_expected_rendered_fieldset_data(
        things,
        "things.subdata",
        {
            "things": [
                {
                    "str1": "foo",
                    "subdata": {
                        "list": [
                            {
                                "a": "b",
                            }
                        ]
                    },
                },
                {
                    "str1": "foo",
                    "subdata": {
                        "list": [
                            {
                                "a": "b",
                            }
                        ]
                    },
                },
            ]
        },
    )
