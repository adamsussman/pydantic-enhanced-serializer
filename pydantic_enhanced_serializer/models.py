from __future__ import annotations

import abc
from asyncio import get_event_loop, isfuture
from typing import Any, Awaitable, Dict, List, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict, Field


class ExpansionBase(BaseModel, abc.ABC):
    response_model: Optional[Any] = Field(
        default=None,
        description=(
            "Response model the expanded object will be cast to.  This is "
            "mainly used as a type hint by the schema generator"
        ),
    )
    merge_fields_upwards: Optional[bool] = Field(
        description=(
            "If true, the expander will attempt to merge items inside the "
            "object returned by `expand` into the parent object.  If false, "
            "then the name of expansion will become a key in the parent "
            "object with a value of the object returned by `expand`."
        ),
        default=False,
    )

    @abc.abstractmethod
    def expand(self, source_model: BaseModel, context: Any) -> Awaitable:
        """
        Seek out and expand based on a model.

        parameters:
            source_model:  A BaseModel instance from which to pick attributes
                           that drive the expansion.

            context:       The object passed in to render_fieldset_model.expansion_context

        Return:
            Any Awaitable that will resolve to:
                * A BaseModel instance
                * A scalar value
                * A list of the BaseModel or a list of scalar values
        """
        ...


class FieldsetConfig(TypedDict, total=False):
    fieldsets: Optional[Dict[str, List[str] | ExpansionBase]]


class ModelExpansion(ExpansionBase):
    """
    Expander will call:
        def expansion_method(self) -> response_model:

    Where self is the model on which the expansion was requested.
    """

    expansion_method_name: str

    def expand(self, source_model: BaseModel, context: Any) -> Awaitable:
        method = getattr(source_model, self.expansion_method_name, None)
        if not method:
            raise Exception(
                f"No such expansion method `{self.expansion_method_name}` found "
                f"on `{source_model.__class__}`"
            )

        value = method(context=context) if callable(method) else method
        if not isfuture(value):
            future = get_event_loop().create_future()
            future.set_result(value)
            return future

        return value


class ExpansionInstruction(BaseModel):
    expansion_definition: ExpansionBase
    expansion_name: str
    path: List[Union[str, int]]
    fieldsets: List[str]
    source_model: BaseModel

    # render time
    future: Optional[Awaitable] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __hash__(self) -> int:
        return sum([hash(str(p)) for p in self.path] + [hash(self.expansion_name)])
