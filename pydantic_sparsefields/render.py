from asyncio import gather
from copy import copy
from typing import Any, List

from pydantic import BaseModel

from .fieldsets import fieldset_to_includes
from .models import ExpansionInstruction
from .path_put import path_put


async def render_fieldset_model(
    model: BaseModel,
    fieldsets: List[str],
    maximum_expansion_depth: int,
    raise_error_on_expansion_not_found: bool,
    expansion_context: Any = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> dict:
    includes, expansions = fieldset_to_includes(fieldsets, model)
    rendered_model = model.dict(
        include=includes,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
    )

    expansion_depth = 0
    while expansions and expansion_depth < maximum_expansion_depth:
        expansions = await render_expansions(
            rendered_model,
            expansions,
            raise_error_on_expansion_not_found=raise_error_on_expansion_not_found,
            expansion_context=expansion_context,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        expansion_depth += 1

    return rendered_model


async def render_expansions(
    rendered_content: dict,
    expansions: List[ExpansionInstruction],
    raise_error_on_expansion_not_found: bool,
    expansion_context: Any = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> List[ExpansionInstruction]:

    new_expansions = []

    for expansion in expansions:
        expansion.future = expansion.expansion_definition.expand(  # type: ignore
            source_model=expansion.source_model, context=expansion_context
        )

    await gather(*[e.future for e in expansions if e.future])

    for expansion in expansions:
        expanded_value = None
        if expansion.future:
            expanded_value = await expansion.future

        if expanded_value is None:
            if raise_error_on_expansion_not_found:
                raise Exception(
                    f"Expansion `{'.'.join([str(p) for p in expansion.path])}` not found"
                )
            continue

        includes, sub_expansions = fieldset_to_includes(
            expansion.fieldsets, expanded_value
        )

        if expansion.expansion_definition.merge_fields_upwards and not isinstance(
            expanded_value, (BaseModel, dict)
        ):
            raise ValueError(
                f"Expansion `{expansion.expansion_name}` on "
                f"`{str(expansion.source_model.__class__)}` "
                "is defined with `merge_fields_upwards=True`, but the expansion did not return "
                "a pydantic.BaseModel or a dict.  Found `{type(expanded_value)}`."
            )

        # expanded_value may be a model or it might be a list/dict/etc...
        # pydantic's _get_value can handle this complexity for any value
        # whereas model.dict only works on a model.
        rendered_value = BaseModel._get_value(
            v=expanded_value,
            to_dict=True,
            by_alias=False,
            include=includes,
            exclude=None,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        if (
            expansion.expansion_definition.merge_fields_upwards
            and len(expansion.path) > 0
        ):
            path_put(rendered_content, copy(expansion.path)[:-1], rendered_value)
        else:
            path_put(rendered_content, copy(expansion.path), rendered_value)

        # Note that new expansions are not executed here nor are they done recursively here
        # we need to aggregate them up a level so that there is a chance to coalesce
        # calls to the same data loader.
        if sub_expansions:
            for sub_expansion in sub_expansions:
                sub_expansion.path = expansion.path + sub_expansion.path
            new_expansions.extend(sub_expansions)

    return new_expansions