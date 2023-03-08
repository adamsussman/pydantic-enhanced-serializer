from asgiref.sync import async_to_sync
from django.http import HttpRequest
from ninja.parsers import Parser
from ninja.renderers import JSONRenderer
from pydantic import BaseModel

from pydantic_enhanced_serializer import render_fieldset_model


class PydanticFieldSetsRenderer(JSONRenderer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields_parameter_name = kwargs.get("fields_parameter_name", "fields")

    def pydantic_to_dict(
        self,
        data: BaseModel,
        request: HttpRequest,
        *,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> dict:
        # not very efficent to have to reparse the request...
        parser = Parser()
        fieldsets = (
            parser.parse_body(request).get(self.fields_parameter_name)
            or parser.parse_querydict(request.GET).get(self.fields_parameter_name)
            or []
        )

        result_data = async_to_sync(render_fieldset_model)(
            model=data,
            fieldsets=fieldsets,
            maximum_expansion_depth=5,
            raise_error_on_expansion_not_found=False,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        return result_data
