import abc
import inspect
from asyncio import get_event_loop, isfuture
from typing import Any, Awaitable, List, Optional, Type, Union

from pydantic import BaseModel, Field


class ExpansionBase(BaseModel, abc.ABC):
    response_model: Optional[Type[BaseModel]] = Field(
        description=(
            "Response model the expanded object will be cast to.  This is "
            "mainly used as a type hint by the schema generator"
        )
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
        ...

    @abc.abstractmethod
    def get_shape(self, source_model: BaseModel) -> Type:
        ...


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

    def get_shape(self, source_model: BaseModel) -> Type:
        method = getattr(source_model, self.expansion_method_name, None)
        if not method:
            raise Exception(
                f"No such expansion method `{self.expansion_method_name}` found "
                f"on `{source_model.__class__}`"
            )

        signature = inspect.signature(method)
        return signature.return_annotation


class ExpansionInstruction(BaseModel):
    expansion_definition: ExpansionBase
    expansion_name: str
    path: List[Union[str, int]]
    fieldsets: List[str]
    source_model: BaseModel

    # render time
    future: Optional[Awaitable] = None

    class Config:
        arbitrary_types_allowed = True