import asyncio
import inspect
from functools import wraps
from json.decoder import JSONDecodeError
from typing import Any, Callable, List, Optional

from fastapi import APIRouter as BaseAPIRouter
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from ..render import render_fieldset_model


class APIRouter(BaseAPIRouter):
    def __init__(
        self,
        *args: Any,
        request_fields_name: str = "fields",
        maximum_expansion_depth: int = 5,
        raise_error_on_expansion_not_found: bool = False,
        **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.serializer_request_fields_name = request_fields_name
        self.serializer_maximum_expansion_depth = maximum_expansion_depth
        self.serializer_raise_error_on_expansion_not_found = (
            raise_error_on_expansion_not_found
        )

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        maximum_expansion_depth: Optional[int] = None,
        raise_error_on_expansion_not_found: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        # Wrap the endpoint function with actions to get fields from
        # the request and alter the render of the result based on it.

        # At runtime, we will need a request object to get the
        # fields parameter.  If the endpoint does not have a request
        # parameter, then add one in that we can use and hide it from
        # the real endpoint at runtime.
        signature = inspect.signature(endpoint)
        request_in_original_signature = False

        for param in signature.parameters.values():
            if issubclass(param.annotation, Request):
                request_param = param
                request_in_original_signature = True
                break

        if not request_in_original_signature:
            request_param = inspect.Parameter(
                name="_fsaaar_request",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Request,
            )

        @wraps(endpoint)
        async def field_aware_endpoint_wrapper(
            *endpoint_args: Any, **endpoint_kwargs: Any
        ) -> Any:
            request = endpoint_kwargs[request_param.name]
            if not request_in_original_signature:
                # Hide request object from real endpoint
                del endpoint_kwargs[request_param.name]

            result = endpoint(*endpoint_args, **endpoint_kwargs)
            if asyncio.iscoroutine(result):
                result = await result

            fields_request = await self._get_fields_from_request(request)

            if isinstance(result, BaseModel):
                content = await render_fieldset_model(
                    model=result,
                    fieldsets=fields_request,
                    maximum_expansion_depth=(
                        maximum_expansion_depth
                        if maximum_expansion_depth is not None
                        else self.serializer_maximum_expansion_depth
                    ),
                    raise_error_on_expansion_not_found=(
                        raise_error_on_expansion_not_found
                        if raise_error_on_expansion_not_found is not None
                        else self.serializer_raise_error_on_expansion_not_found
                    ),
                    expansion_context=request,
                    exclude_unset=kwargs.get("response_model_exclude_unset", False),
                    exclude_defaults=kwargs.get(
                        "response_model_exclude_defaults", False
                    ),
                    exclude_none=kwargs.get("response_model_exclude_none", False),
                )

                return JSONResponse(content=content)

            return result

        if not request_in_original_signature:
            # Add request to signature
            new_signature = signature.replace(
                parameters=[request_param, *signature.parameters.values()]
            )
            field_aware_endpoint_wrapper.__signature__ = new_signature  # type: ignore

        return super().add_api_route(path, field_aware_endpoint_wrapper, **kwargs)

    async def _get_fields_from_request(self, request: Request) -> List[str]:
        raw_fields: Any = None
        from_body: bool = False

        body_bytes = await request.body()
        if body_bytes:
            try:
                data = await request.json()
                raw_fields = data.get(self.serializer_request_fields_name)
                from_body = True
            except JSONDecodeError:
                pass

        if not raw_fields:
            raw_fields = [
                f
                for f in request.query_params.getlist(
                    self.serializer_request_fields_name
                )
                if f
            ]
            from_body = False

        if not raw_fields:
            return []

        if isinstance(raw_fields, str):
            return raw_fields.split(",")

        elif isinstance(raw_fields, list) and all(
            [isinstance(f, str) for f in raw_fields]
        ):
            fields = set()
            for field in raw_fields:
                fields.update(field.split(","))
            return list(fields)

        raise RequestValidationError(
            [
                ValidationError.from_exception_data(
                    title="Invalid value",
                    line_errors=[
                        {
                            "type": "invalid",
                            "msg": (  # type: ignore
                                "`{self.serializer_request_fields_name}` must be a "
                                "(optionally  comma saperated) string or "
                                "list of (optionally comma separated) strings"
                            ),
                            "loc": (
                                "body" if from_body else "query",
                                self.serializer_request_fields_name,
                            ),
                            "input": raw_fields,
                        }
                    ],
                )
            ]
        )
