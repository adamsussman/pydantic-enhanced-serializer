from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, fields

from .models import ExpansionBase, ExpansionInstruction

SEQUENCE_SHAPES = (
    fields.SHAPE_LIST,
    fields.SHAPE_SET,
    fields.SHAPE_TUPLE,
    fields.SHAPE_TUPLE_ELLIPSIS,
    fields.SHAPE_SEQUENCE,
    fields.SHAPE_FROZENSET,
    fields.SHAPE_ITERABLE,
)


def fieldset_to_includes(
    fields_request: Union[str, Set[str], List[str]],
    model_data: Any,
    path: List[Union[str, int]] = None,
    expansion_context: Any = None,
) -> Tuple[dict, Set[ExpansionInstruction]]:
    """
    Recursively descend a fieldsets list along with a pydantic model and produce:

    1) An `include` specification matching fieldsets that pydantic.dict will understand
    2) A list of requested expansions

    :parameters:
        - fields_request: Set of strings, each string is a field or fieldset name.  For nested
                     objects, names should be dot seperated: `top.submodel.subfield`.

        - model: A pydantic model, the top of the object tree that `fields_request` is
                 inteded to match

    :returns:
        - dict in pydantic `include` format meant for passing to model.dict(include=)
        - list of expansion actions needed

    :pydantic model.Config extensions:
        - :`fieldsets`: A dict of names (used as values in `fieldsets`) to one of
            - A list of strings.  These are field names as defined in the model.
            - An Expansion object from .expansions

        - `fieldsets["default"]`.  A set of fields to return when no specific request
           is made in `fieldsets` parameter.

        - If no `fieldsets` config value is present, then ALL fields will be returned
          (ie: normal pydantic.dict behavior).
    """
    includes: Dict[str, Any] = {}
    current_includes_ptr = includes
    expansions: Set[ExpansionInstruction] = set()
    expansion_fieldsets: Dict[str, Set[str]] = defaultdict(set)

    if model_data is None:
        return {}, set()

    if isinstance(fields_request, str):
        fields_request = set(fields_request.split(","))

    if isinstance(fields_request, list):
        fields_request = set(fields_request)

    model = model_data
    while isinstance(model, list):
        current_includes_ptr["__all__"] = {}
        current_includes_ptr = current_includes_ptr["__all__"]
        if len(model) == 0:
            break
        model = list(model)[0]

    if not isinstance(model, BaseModel):
        return {}, set()

    fieldsets: Optional[dict] = getattr(model.__config__, "fieldsets", None)
    default_fieldset: Optional[Set] = None
    if fieldsets and fieldsets.get("default"):
        default_fieldset = (
            set(fieldsets["default"])
            if isinstance(fieldsets["default"], list)
            else set([fieldsets["default"]])
        )

    if fieldsets is None or (default_fieldset and "*" in default_fieldset):
        # no fieldsets set or * in default, enable ALL fields
        fields_request.update([f.name for f in model.__fields__.values()])

        # and add in all expansions
        if fieldsets:
            fields_request.update(
                [
                    name
                    for name in fieldsets.keys()
                    if isinstance(fieldsets[name], ExpansionBase)
                ]
            )

    elif default_fieldset:
        fields_request.update(default_fieldset)

    if path is None:
        path = []

    for fieldset in fields_request:
        if not fieldset:
            continue

        field: str
        subfields: Set[str]

        try:
            field, subfield = fieldset.split(".", 1)
            subfields = set([subfield])
        except ValueError:
            field = fieldset
            subfields = set([])

        field_obj = model.__fields__.get(field)

        if field_obj:
            if issubclass(field_obj.type_, BaseModel):
                if field_obj.shape in SEQUENCE_SHAPES:
                    # Field value is a list of models
                    if field not in current_includes_ptr:
                        current_includes_ptr[field] = defaultdict(dict)

                    # while this could be done abstractly on the model class
                    # and using __all__, we need to examine each item for its
                    # own expansions
                    for idx, item in enumerate(getattr(model, field_obj.name)):
                        sub_includes, sub_expansions = fieldset_to_includes(
                            subfields, item, path + [field, idx]
                        )

                        current_includes_ptr[field][idx].update(sub_includes)
                        expansions.update(sub_expansions)
                else:
                    # Field is a single model
                    if field not in current_includes_ptr:
                        current_includes_ptr[field] = {}

                    sub_includes, sub_expansions = fieldset_to_includes(
                        subfields, getattr(model, field_obj.name), path + [field]
                    )

                    current_includes_ptr[field].update(sub_includes)
                    expansions.update(sub_expansions)

            else:
                current_includes_ptr[field] = ...

        elif (
            expansion := getattr(model.__config__, "fieldsets", {}).get(field)
        ) and isinstance(expansion, ExpansionBase):
            if isinstance(model_data, list):
                # We need to create an expansion per list item
                for idx, source_model in enumerate(model_data):
                    expansions.add(
                        ExpansionInstruction(
                            expansion_definition=expansion,
                            expansion_name=field,
                            path=path + [idx, field],
                            fieldsets=subfields,
                            source_model=source_model,
                        )
                    )
            else:
                # as there may be multiple expansion fieldsets in the request, we need
                # to accumulate them first and then handle them later once all fieldset
                # requests have been seen
                expansion_fieldsets[field].update(subfields)

        elif named_fieldset := getattr(model.__config__, "fieldsets", {}).get(field):
            # Fieldset collection by name
            sub_includes, sub_expansions = fieldset_to_includes(
                named_fieldset, model, path + [field]
            )
            current_includes_ptr.update(sub_includes)
            expansions.update(sub_expansions)

    if expansion_fieldsets:
        for expansion, expansion_fields in expansion_fieldsets.items():
            expansions.add(
                ExpansionInstruction(
                    expansion_definition=getattr(model.__config__, "fieldsets", {}).get(
                        expansion
                    ),
                    expansion_name=expansion,
                    path=path + [expansion],
                    fieldsets=expansion_fields,
                    source_model=model,
                )
            )

    return {k: v for k, v in includes.items() if v is not None}, expansions
