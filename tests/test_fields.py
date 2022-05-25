from typing import List, Optional

import pytest
from pydantic import BaseModel

from .utils import assert_expected_rendered_fieldset_data


def test_no_config_default_behaviour() -> None:
    class Level2Item(BaseModel):
        l2var1: str
        l2var2: int
        l2var3: str

    class Level2ListItem(BaseModel):
        l2lvar1: str
        l2lvar2: str

    class Level1Response(BaseModel):
        var1: str
        var2: str
        var3: int
        var4: int
        item: Level2Item
        items: List[Level2ListItem]

    response = Level1Response(
        var1="foo",
        var2="bar",
        var3=3,
        var4=4,
        item=Level2Item(
            l2var1="l21",
            l2var2=2,
            l2var3="123",
        ),
        items=[
            Level2ListItem(
                l2lvar1="l2l1",
                l2lvar2="l2l2",
            ),
            Level2ListItem(
                l2lvar1="l2l1B",
                l2lvar2="l2l2B",
            ),
            Level2ListItem(
                l2lvar1="l2l1C",
                l2lvar2="l2l2C",
            ),
        ],
    )

    assert_expected_rendered_fieldset_data(
        response,
        [],
        {
            "var1": "foo",
            "var2": "bar",
            "var3": 3,
            "var4": 4,
            "item": {
                "l2var1": "l21",
                "l2var2": 2,
                "l2var3": "123",
            },
            "items": [
                {
                    "l2lvar1": "l2l1",
                    "l2lvar2": "l2l2",
                },
                {
                    "l2lvar1": "l2l1B",
                    "l2lvar2": "l2l2B",
                },
                {
                    "l2lvar1": "l2l1C",
                    "l2lvar2": "l2l2C",
                },
            ],
        },
    )


# Zero config means always return ALL fields
@pytest.mark.parametrize(
    "fields,expected",
    (
        ([], {"field1": "one", "field2": "two", "field3": "three"}),
        (["field1"], {"field1": "one", "field2": "two", "field3": "three"}),
        (["field1", "field2"], {"field1": "one", "field2": "two", "field3": "three"}),
        (
            ["field1", "field2", "field3"],
            {"field1": "one", "field2": "two", "field3": "three"},
        ),
        (["no_such_field"], {"field1": "one", "field2": "two", "field3": "three"}),
        (
            ["no_such_field", "field1"],
            {"field1": "one", "field2": "two", "field3": "three"},
        ),
        (
            ["no_such_field", "field1", "field2"],
            {"field1": "one", "field2": "two", "field3": "three"},
        ),
    ),
)
def test_single_level_by_field_name_no_config(
    fields: List[str], expected: dict
) -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(response, fields, expected)


# Any config means all fields must be asked for or NONE are returned
@pytest.mark.parametrize(
    "fields,expected",
    (
        ([], {}),
        (["field1"], {"field1": "one"}),
        (["field1", "field2"], {"field1": "one", "field2": "two"}),
        (
            ["field1", "field2", "field3"],
            {"field1": "one", "field2": "two", "field3": "three"},
        ),
        (["no_such_field"], {}),
        (["no_such_field", "field1"], {"field1": "one"}),
        (["no_such_field", "field1", "field2"], {"field1": "one", "field2": "two"}),
    ),
)
def test_single_level_by_field_name_any_config(
    fields: List[str], expected: dict
) -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            # XXX: this is a weird control...should be more explicit
            fieldsets: dict = {}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(response, fields, expected)


# Default fieldset always returned regardless of other args
@pytest.mark.parametrize(
    "fields,expected",
    (
        ([], {"field3": "three"}),
        (["field1"], {"field1": "one", "field3": "three"}),
        (["field1", "field2"], {"field1": "one", "field2": "two", "field3": "three"}),
        (
            ["field1", "field2", "field3"],
            {"field1": "one", "field2": "two", "field3": "three"},
        ),
        (["no_such_field"], {"field3": "three"}),
        (["no_such_field", "field1"], {"field1": "one", "field3": "three"}),
        (
            ["no_such_field", "field1", "field2"],
            {"field1": "one", "field2": "two", "field3": "three"},
        ),
    ),
)
def test_single_level_by_field_subset_default(
    fields: List[str], expected: dict
) -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {"default": ["field3"]}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(response, fields, expected)


def test_named_fieldset() -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {"fset1": ["field3"], "fset2": ["field1", "field2"]}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(response, ["fset1"], {"field3": "three"})
    assert_expected_rendered_fieldset_data(
        response, ["fset2"], {"field1": "one", "field2": "two"}
    )
    assert_expected_rendered_fieldset_data(
        response,
        ["fset1", "fset2"],
        {"field1": "one", "field2": "two", "field3": "three"},
    )


def test_named_fieldset_and_named_field() -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {"fset1": ["field3"], "fset2": ["field1", "field2"]}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(
        response, ["fset1", "field1"], {"field1": "one", "field3": "three"}
    )


@pytest.mark.parametrize(
    "fields,expected",
    (
        (
            [],
            {
                "field1": "one",
                "field2": "two",
                "field3": "three",
                "sub": {"subfield1": "sub1", "subfield2": "sub2"},
            },
        ),
        (
            ["field1"],
            {
                "field1": "one",
                "field2": "two",
                "field3": "three",
                "sub": {"subfield1": "sub1", "subfield2": "sub2"},
            },
        ),
        (
            ["field1", "sub"],
            {
                "field1": "one",
                "field2": "two",
                "field3": "three",
                "sub": {"subfield1": "sub1", "subfield2": "sub2"},
            },
        ),
        (
            ["field1", "sub.subfield1"],
            {
                "field1": "one",
                "field2": "two",
                "field3": "three",
                "sub": {"subfield1": "sub1", "subfield2": "sub2"},
            },
        ),
        (
            ["field1", "sub.subfield1", "sub.subfield2"],
            {
                "field1": "one",
                "field2": "two",
                "field3": "three",
                "sub": {"subfield1": "sub1", "subfield2": "sub2"},
            },
        ),
    ),
)
def test_nested_by_field_name_no_config_both(fields: List[str], expected: dict) -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: SubModel

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=SubModel(
            subfield1="sub1",
            subfield2="sub2",
        ),
    )
    assert_expected_rendered_fieldset_data(response, fields, expected)


@pytest.mark.parametrize(
    "fields,expected",
    (
        ([], {}),
        (["field1"], {"field1": "one"}),
        (["field1", "sub"], {"field1": "one", "sub": {}}),
        (["field1", "sub.subfield1"], {"field1": "one", "sub": {"subfield1": "sub1"}}),
        (
            ["field1", "sub.subfield1", "sub.subfield2"],
            {"field1": "one", "sub": {"subfield1": "sub1", "subfield2": "sub2"}},
        ),
    ),
)
def test_nested_by_field_name_any_config_both(
    fields: List[str], expected: dict
) -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            # XXX: this is a weird control...should be more explicit
            fieldsets: dict = {}

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: SubModel

        class Config:
            # XXX: this is a weird control...should be more explicit
            fieldsets: dict = {}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=SubModel(
            subfield1="sub1",
            subfield2="sub2",
        ),
    )

    assert_expected_rendered_fieldset_data(response, fields, expected)


# Default fieldset always returned regardless of other args
@pytest.mark.parametrize(
    "fields,expected",
    (
        ([], {"field3": "three"}),
        (["field1"], {"field1": "one", "field3": "three"}),
        (["sub"], {"field3": "three", "sub": {"subfield2": "sub2"}}),
        (
            ["sub.subfield1"],
            {"field3": "three", "sub": {"subfield1": "sub1", "subfield2": "sub2"}},
        ),
    ),
)
def test_nested_by_field_subset_default(fields: List[str], expected: dict) -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            fieldsets = {"default": ["subfield2"]}

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: SubModel

        class Config:
            fieldsets = {"default": ["field3"]}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=SubModel(
            subfield1="sub1",
            subfield2="sub2",
        ),
    )

    assert_expected_rendered_fieldset_data(response, fields, expected)


@pytest.mark.parametrize(
    "fields,expected",
    (
        ([], {"field3": "three", "sub": {"subfield2": "sub2"}}),
        (
            ["field1"],
            {"field1": "one", "field3": "three", "sub": {"subfield2": "sub2"}},
        ),
        (["sub"], {"field3": "three", "sub": {"subfield2": "sub2"}}),
        (
            ["sub.subfield1"],
            {"field3": "three", "sub": {"subfield1": "sub1", "subfield2": "sub2"}},
        ),
    ),
)
def test_nested_by_field_in_default(fields: List[str], expected: dict) -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            fieldsets = {"default": ["subfield2"]}

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: SubModel

        class Config:
            fieldsets = {"default": ["field3", "sub"]}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=SubModel(
            subfield1="sub1",
            subfield2="sub2",
        ),
    )

    assert_expected_rendered_fieldset_data(response, fields, expected)


def test_nested_named_fieldset_and_named_field() -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            fieldsets = {
                "subfset1": ["subfield2"],
                "subfset2": ["subfield1", "subfield2"],
            }

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: SubModel

        class Config:
            fieldsets = {
                "default": ["field3"],
            }

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=SubModel(
            subfield1="sub1",
            subfield2="sub2",
        ),
    )

    assert_expected_rendered_fieldset_data(
        response, ["sub.subfset1"], {"field3": "three", "sub": {"subfield2": "sub2"}}
    )


def test_nested_named_fieldset_sublist() -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            fieldsets = {
                "subfset1": ["subfield2"],
                "subfset2": ["subfield1", "subfield2"],
            }

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: List[SubModel]

        class Config:
            fieldsets = {
                "default": ["field3"],
            }

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=[
            SubModel(
                subfield1="sub1",
                subfield2="sub2",
            ),
            SubModel(
                subfield1="sub3",
                subfield2="sub4",
            ),
        ],
    )

    assert_expected_rendered_fieldset_data(
        response,
        ["sub.subfset1"],
        {"field3": "three", "sub": [{"subfield2": "sub2"}, {"subfield2": "sub4"}]},
    )


def test_nested_model_with_default() -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            fieldsets = {
                "default": ["subfield2"],
            }

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: List[SubModel]

        class Config:
            fieldsets = {
                "default": ["field3"],
            }

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=[
            SubModel(
                subfield1="sub1",
                subfield2="sub2",
            ),
            SubModel(
                subfield1="sub3",
                subfield2="sub4",
            ),
        ],
    )

    assert_expected_rendered_fieldset_data(
        response,
        ["sub"],
        {"field3": "three", "sub": [{"subfield2": "sub2"}, {"subfield2": "sub4"}]},
    )


def test_nested_model_with_default_at_all_levels() -> None:
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            fieldsets = {
                "default": ["subfield2"],
            }

    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str
        sub: List[SubModel]

        class Config:
            fieldsets = {
                "default": ["field3", "sub"],
            }

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
        sub=[
            SubModel(
                subfield1="sub1",
                subfield2="sub2",
            ),
            SubModel(
                subfield1="sub3",
                subfield2="sub4",
            ),
        ],
    )

    assert_expected_rendered_fieldset_data(
        response,
        [],
        {"field3": "three", "sub": [{"subfield2": "sub2"}, {"subfield2": "sub4"}]},
    )


def test_nested_optional_model_not_given() -> None:
    class QueryModel(BaseModel):
        what: str

    class ResponseModel(BaseModel):
        items: List[str]
        query: Optional[QueryModel] = None

    response = ResponseModel(items=[])

    assert_expected_rendered_fieldset_data(response, [], {"items": [], "query": None})


def test_default_start() -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {"default": "*"}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(
        response, [], {"field1": "one", "field2": "two", "field3": "three"}
    )


def test_fieldsets_as_string() -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str
        field3: str

        class Config:
            fieldsets = {"default": "field1"}

    response = ResponseModel(
        field1="one",
        field2="two",
        field3="three",
    )

    assert_expected_rendered_fieldset_data(
        response, "field2,field3", {"field1": "one", "field2": "two", "field3": "three"}
    )


def test_fieldset_that_references_itself() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str

        class Config:
            fieldsets = {
                "default": ["field1"],
                "field2": ["field2"],
            }

    class ResponseModel(BaseModel):
        things: List[Thing]

    response = ResponseModel(
        things=[
            Thing(
                field1="one",
                field2="two",
            )
        ]
    )

    assert_expected_rendered_fieldset_data(
        response,
        "things.other,things.field2,things.field5",
        {"things": [{"field1": "one", "field2": "two"}]},
    )


def test_fieldset_that_references_itself_but_does_not_exist_as_a_field() -> None:
    class Thing(BaseModel):
        field1: str
        field2: str

        class Config:
            fieldsets = {
                "default": ["field1"],
                "does_not_exist": ["does_not_exist", "field2"],
            }

    class ResponseModel(BaseModel):
        things: List[Thing]

    response = ResponseModel(
        things=[
            Thing(
                field1="one",
                field2="two",
            )
        ]
    )

    assert_expected_rendered_fieldset_data(
        response,
        "things.does_not_exist",
        {"things": [{"field1": "one", "field2": "two"}]},
    )
