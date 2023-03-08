import asyncio
from typing import Any, List, Optional, Union

from pydantic import BaseModel

from pydantic_enhanced_serializer.render import render_fieldset_model


def assert_expected_rendered_fieldset_data(
    model_instance: BaseModel,
    fields: Union[str, List[str]],
    expected: dict,
    expansion_context: Optional[Any] = None,
) -> None:
    event_loop = asyncio.get_event_loop()

    cor = render_fieldset_model(
        model=model_instance,
        fieldsets=fields,
        maximum_expansion_depth=5,
        raise_error_on_expansion_not_found=False,
        expansion_context=expansion_context,
    )
    rendered_data = event_loop.run_until_complete(cor)
    assert rendered_data == expected
