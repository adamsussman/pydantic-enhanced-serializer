
## Quickstart FastAPI Integration

```Python
    from fastapi import FastAPI

    # The critical thing is to use this alternate APIRouter subclass
    from pydantic_enhanced_serializer.integrations.fastapi import APIRouter

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


## Quickstart Django Ninja Integration

```python
    from django_ninja import NinjaAPI
    from pydantic_enhanced_serializer.integrations.django_ninja import PydanticFieldSetsRenderer


    api = NinjaAPI(
        # create api object as normal, but override the renderer
        renderer=PydanticFieldSetsRenderer(fields_parameter_name="fields"),
    )

    @api.post("/foo")
    def my_api_call(...):
        ...
```

Request specific fields in the response:

```console
$ curl -d '
    {
        "fields": ["extra", "expensive_field_5],
        "more": "data"
    }
    '
    http://localhost/foo
```

## Quickstart Flask Integration

Since Flask does not offer a pydantic based API natively, we offer here
an example pydantic wrapper you can use.  This is only an example, so
you mileage may vary.

```Python
    from flask import Flask, make_response
    from pydantic import BaseModel, ValidationError

    from pydantic_enhanced_serializer.integrations.flask import pydantic_api

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