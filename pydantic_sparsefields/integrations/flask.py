import asyncio
from functools import wraps
from typing import Any, Callable, List, Optional, Tuple, Type

from asgiref.sync import async_to_sync
from flask import make_response, request
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import BadRequest

from pydantic_sparsefields.render import render_fieldset_model
from pydantic_sparsefields.schema import augment_schema_with_fieldsets


def pydantic_api(
    name: str = None,
    tags: List[str] = None,
    success_status_code: int = 200,
    maximum_expansion_depth=5,
    request_fields_name: str = "fields",
) -> Callable:
    def wrap(view_func: Callable) -> Callable:
        request_model_param_name, request_model, response_model = _get_annotated_models(
            view_func
        )

        if request_model:
            augment_schema_with_fieldsets(request_model)

        if response_model:
            augment_schema_with_fieldsets(response_model)

        @wraps(view_func)
        def wrapped_endpoint(*args: Any, **kwargs: Any) -> Callable:
            body = None
            if request.is_json:
                body = request.json

            fieldsets = (
                isinstance(body, dict) and body.pop(request_fields_name, [])
            ) or request.args.get(request_fields_name, [])

            if request_model and request_model_param_name:
                kwargs[request_model_param_name] = request_model(**body or {})

            if asyncio.iscoroutine(view_func):
                result = async_to_sync(view_func)(*args, **kwargs)
            else:
                result = view_func(*args, **kwargs)

            if response_model and isinstance(result, dict):
                try:
                    result = response_model(**result)
                except ValidationError:
                    # we don't want the end client to see these errors, just
                    # the local log
                    raise

            if isinstance(result, BaseModel):
                result_data = async_to_sync(render_fieldset_model)(
                    model=result,
                    fieldsets=fieldsets,
                    maximum_expansion_depth=maximum_expansion_depth,
                    raise_error_on_expansion_not_found=False,
                )
                result = make_response(result_data, success_status_code)

            return result

        # Normally wrapping functions with decorators leaves no easy
        # way to tell who is doing the wrapping and for what purpose.
        # This adds some markers that are useful for introspection of
        # endpoints (such as generating schema).
        wrapped_endpoint.__pydantic_api__ = {  # type: ignore
            "name": name,
            "tags": tags,
        }

        return wrapped_endpoint

    return wrap


def _get_annotated_models(
    func: Callable,
) -> Tuple[Optional[str], Optional[Type[BaseModel]], Optional[Type[BaseModel]]]:
    request_model = None
    request_model_param_name = None
    response_model = None

    view_model_args = [
        k
        for k, v in func.__annotations__.items()
        if v and k != "return" and issubclass(v, BaseModel)
    ]

    if len(view_model_args) > 1:
        raise Exception(
            f"Too many model arguments specified for {func.__name__}. "
            "Could not determine which to map to request body"
        )
    elif len(view_model_args) == 1:
        request_model_param_name = view_model_args[0]
        request_model = func.__annotations__[request_model_param_name]

    if func.__annotations__.get("return") and issubclass(
        func.__annotations__.get("return"), BaseModel  # type: ignore
    ):
        response_model = func.__annotations__["return"]

    return request_model_param_name, request_model, response_model
