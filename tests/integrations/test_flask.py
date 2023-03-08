from typing import List

from flask import Flask, make_response
from pydantic import BaseModel, ValidationError

from pydantic_enhanced_serializer.integrations.flask import pydantic_api


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

    app = Flask("test_app")

    @app.post("/")
    @pydantic_api()
    def get_response() -> Response:
        return Response(
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

    client = app.test_client()
    response = client.post("/", json={"fields": ["subfields"]})

    assert response.status_code == 200, response.json
    assert response.json == {
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


def test_passthrough_schemas() -> None:
    class RequestModel(BaseModel):
        field1: str
        field2: int

        class Config:
            fieldsets = {
                "default": ["field1"],
            }

    class ResponseModel(BaseModel):
        field1: str
        field2: int

        class Config:
            fieldsets = {
                "default": ["field1"],
            }

    app = Flask("test_app")

    @app.post("/")
    @pydantic_api()
    def get_response(body: RequestModel) -> ResponseModel:
        return ResponseModel(
            field1=body.field1,
            field2=body.field2,
        )

    app.register_error_handler(
        ValidationError, lambda e: make_response({"errors": e.errors()}, 400)
    )

    client = app.test_client()

    # make sure input validation is happening
    response = client.post("/", json={"field1": "one"})
    assert response.status_code == 400, response.json
    assert response.json

    assert response.json["errors"][0]["loc"] == ["field2"]
    assert response.json["errors"][0]["type"] == "value_error.missing"

    # look for echo default fields only
    response = client.post("/", json={"field1": "one", "field2": 2})
    assert response.status_code == 200
    assert response.json

    assert response.json["field1"] == "one"
    assert "field2" not in response.json

    # ask for field2
    response = client.post(
        "/", json={"field1": "one", "field2": 2, "fields": ["field2"]}
    )
    assert response.status_code == 200
    assert response.json

    assert response.json["field1"] == "one"
    assert response.json["field2"] == 2


def test_fields_in_query_string() -> None:
    class ResponseModel(BaseModel):
        field1: str
        field2: str

        class Config:
            fieldsets = {
                "default": ["field1"],
            }

    app = Flask("test_app")

    @app.get("/")
    @pydantic_api()
    def get_response() -> ResponseModel:
        return ResponseModel(
            field1="f1",
            field2="f2",
        )

    client = app.test_client()

    # make sure input validation is happening
    response = client.get("/", query_string={"fields": "field2"})
    assert response.status_code == 200, response.json
    assert response.json

    assert response.json["field1"] == "f1"
    assert response.json["field2"] == "f2"
