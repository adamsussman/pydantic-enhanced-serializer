# Pydantic Sparse Fields and Expansions

Allow serialization of pydantic models (model.dict()) to include
only specified wanted fields instead of all fields.

Allow serializtion of pydantic models to expand fields into
full models with complex logic, such as database queries.

Both features are useful if you are using pydantic models to
drive REST APIs (ie: FastAPI) and you want to emulate the
field/expansion request model of GraphQL or other sophisticated
APIs.

## Features

* "Fields" Request: When serializing a model, specify which fields you want and get ONLY those fields
* "Field Sets": Ask for specific fields or named groupings of fields
* "Expansions": Create new field names that "expand" into bigger objects via complex loading (for example,
  if you have a user id field, you can ask for the entire user object to be loaded and included
  in the serialization.
* Nested Model: Full support for nested models, lists of models, etc...
* Schema: Augment pydantic json schema generation with fieldset options
* Flask integration
* FastAPI integration

## Installation

```console
$ pip install pydantic-sparsefields
```

## Help


See [documentation](docs/) for full details.

## Quickstart Example - Python

Basically: use `render_fieldset_model` instead of `model.dict()` or `model.json()`.

Note that `render_fieldset_model` is an async function, so you may need
to await it, depending on your application.

```Python
    from pydantic import BaseModel
    from pydantic_sparsefields import render_fieldset_model

    class MyModel(BaseModel):
        field_1: str
        field_2: str
        field_3: str
        field_4: str
        expensive_field_5: str
        expensive_field_6: str

        class Config:
            # This is the key config
            fieldsets = {
                "default": ["field_1", "field_2"],
                "extra": ["field_3", "field_4"],
            }
```

Get only "default" fields:

```Python
    model = MyModel(
        field_1="field1 value",
        field_2="field2 value",
        field_3="field3 value",
        field_4="field4 value",
        expensive_field_5="field5 value",
        expensive_field_6="field6 value",
    )

    # instead of model.dict() do:
    result = await render_fieldset_model(
        model=model,
        fieldsets=[]
    )
```

Result:

```Python
    # Only "default" fieldset fields returned
    result == {
        "field_1": "field1 value",
        "field_2": "field2 value",
    }
```

Ask for specific fields:

```Python
    result = await render_fieldset_model(
        model=model,
        fieldsets=["extra", "expensive_field_5"],
    )
```

Result:

```Python
    # "default" fieldset fields, "extra" fieldset fields and
    # "expensive_field_5" returned, but NOT "expensive_field_6"
    result == {
        "field_1": "field1 value",
        "field_2": "field2 value",
        "field_3": "field3 value",
        "field_4": "field4 value",
        "expensive_field_5": field5 value",
    }
```

## Nested Fields example

```Python
    class SubModel(BaseModel):
        subfield1: str
        subfield2: str

        class Config:
            fieldsets = {
                "default": ["subfield1"],
            }

    class MyModel(BaseModel):
        field1: str
        subfield: SubModel

        class Config:
            fieldsets = {
                "default": ["field1"],
            }

    result = await render_fieldset_model(
        model=mymodel_instance,
        fields=["subfield.field2"]
    )
```

## Quickstart FastAPI Integration

```Python
    from fastapi import FastAPI

    # The critical thing is to use this alternate APIRouter subclass
    from pydantic_sparsefields.integrations.fastapi import APIRouter

    api = APIRouter()

    @api.post("/some/path", response_model=MyModel)
    def some_action() -> MyModel:
        return MyModel(...)

    @api.get("/some/other/path", response_model=MyModel)
    def some_action() -> MyModel:
        return MyModel(...)

    app = FastAPI()
    app.include_router(api, prefix="/")
```

Request specific fields in the response:

```console
$ curl -d '
    {
        "fields": ["extra", "expensive_field_5],
        "more": "data"
    }
    '
    http://localhost/some/path
```


## Quickstart Flask Integration

```Python
    from flask import Flask, make_response
    from pydantic import BaseModel, ValidationError

    from pydantic_sparsefields.integrations.flask import pydantic_api

    class RequestModel(BaseModel):
        ...

    class ResponseModel(BaseModel):
        ...

    app = Flask("my_app")

    @app.post("/some/path")
    @pydantic_api()
    # Note that the body and return type annotations are necessary for the @pydantic_api
    # wrapper to function.
    def my_api(body: RequestModel) -> ResponseModel:
        return MyModel(...)  # or a dict in the shape of MyModel

    # Flask doesn't handle pydantic validation errors natively so its a good idea
    # to add an error handler for when the body data fails validation
    app.register_error_handler(ValidationError, lambda e: make_response({"errors": e.errors()}, 400))
```

Request specific fields in the response:

```console
$ curl -d '
    {
        "fields": ["extra", "expensive_field_5],
        "more": "data"
    }
    '
    http://localhost/some/path
```

## License

This project is licensed under the terms of the MIT license.