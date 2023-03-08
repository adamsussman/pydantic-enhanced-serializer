from typing import List

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from pydantic_enhanced_serializer.integrations.fastapi import APIRouter


@pytest.mark.parametrize(
    "field_input_method", ("query_array", "query_comma", "post_array", "post_comma")
)
@pytest.mark.parametrize(
    "fields,expected",
    (
        ([], []),
        (["field1", "field2"], ["field1", "field2"]),
        (
            ["field1,field2", "field3", "field4,field5.foo.bar"],
            ["field1", "field2", "field3", "field4", "field5.foo.bar"],
        ),
    ),
)
def test_get_fields_from_request(
    field_input_method: str, fields: List[str], expected: List[str]
) -> None:
    api = APIRouter()

    @api.post("/")
    async def get_fields(request: Request) -> dict:
        return {"fieldsets": await api._get_fields_from_request(request)}

    app = FastAPI()
    app.include_router(api)

    client = TestClient(app)

    # query string comma sep
    if field_input_method == "query_array":
        response = client.post(
            "/?{}".format("&".join([f"fields={f}" for f in fields])), json={}
        )

    elif field_input_method == "query_comma":
        response = client.post("/?fields={}".format(",".join(fields)), json={})

    elif field_input_method == "post_array":
        response = client.post("/", json={"fields": fields})

    elif field_input_method == "post_comma":
        response = client.post("/", json={"fields": ",".join(fields)})

    assert response.status_code == 200
    assert sorted(response.json()["fieldsets"]) == sorted(expected)


def test_field_filtered_response() -> None:
    class SubModel(BaseModel):
        sfield1: str
        sfield2: str

        class Config:
            fieldsets = {
                "default": ["sfield1"],
            }

    class Response(BaseModel):
        field1: str
        subfields: List[SubModel]

        class Config:
            fieldsets = {"default": ["field1"]}

    api_response = Response(
        field1="field1 value",
        subfields=[
            SubModel(
                sfield1="sfield1value1",
                sfield2="sfield2value1",
            ),
            SubModel(
                sfield1="sfield1value2",
                sfield2="sfield2value2",
            ),
        ],
    )

    api = APIRouter()

    @api.post("/")
    def get_response() -> BaseModel:
        return api_response

    app = FastAPI()
    app.include_router(api)

    client = TestClient(app)
    response = client.post("/", json={"fields": ["subfields"]})

    assert response.status_code == 200, response.content
    assert response.json() == {
        "field1": "field1 value",
        "subfields": [
            {
                "sfield1": "sfield1value1",
            },
            {
                "sfield1": "sfield1value2",
            },
        ],
    }
