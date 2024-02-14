
# Better pydantic serialization for API use cases

Enhance pydantic's output serialization with features that can help make better APIs:

1) Output only fields and sets of fields requested by the caller, instead of all fields.

For example:

```
    api caller: Give me a User object with only the email and id fields.

    api response: Ok, instead of the usual 20 User fields, here is the object with only two.
```

2) Expand field values into more complex objects when requested

```
    api caller: Give me 10 Blog objects AND the User Objects that created them in ONE API response.

    api response: Ok, in addition to Blog.user_id, I will also give you Blog.User and its fields.
```


Both features are useful if you are using pydantic models to drive
REST APIs (ie: FastAPI) and you want to emulate the field/expansion
request model of GraphQL or other sophisticated APIs.

## Features

* Simply formatted "Fields" Request: When serializing a model, specify which fields you want and get ONLY those fields
* "Field Sets": Ask for specific fields or named groupings of fields
* "Expansions": Create new field names that "expand" into bigger objects via complex loading (for example,
  if you have a user id field, you can ask for the entire user object to be loaded and included
  in the serialization.
* Nested Model: Full support for nested models, lists of models, etc...
* Schema: Augment pydantic json schema generation with fieldset options
* Integration examples are given for:
    - Django Ninja
    - FastAPI
    - Flask

## Installation

```console
$ pip install pydantic-enhanced-serializer
```

## Help


See [documentation](https://github.com/adamsussman/pydantic-enhanced-serializer/tree/main/docs) for full details.

## Quickstart Example - Python

Basically: use `render_fieldset_model` instead of `model.model_dump()` or `model.model_dump_json()`.

Note that `render_fieldset_model` is an async function, so you may need
to await it, depending on your application.

```Python
    from typing import ClassVar

    from pydantic import BaseModel
    from pydantic_enhanced_serializer import render_fieldset_model, FieldsetConfig

    class MyModel(BaseModel):
        field_1: str
        field_2: str
        field_3: str
        field_4: str
        expensive_field_5: str
        expensive_field_6: str

        # This is the key config
        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets = {
                "default": ["field_1", "field_2"],
                "extra": ["field_3", "field_4"],
            }
        )
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

    # instead of model.model_dump() do:
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

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets = {
                "default": ["subfield1"],
            }
        )

    class MyModel(BaseModel):
        field1: str
        subfield: SubModel

        fieldset_config: ClassVar = FieldsetConfig(
            fieldsets = {
                "default": ["field1"],
            }
        )

    result = await render_fieldset_model(
        model=mymodel_instance,
        fields=["subfield.field2"]
    )
```

## License

This project is licensed under the terms of the MIT license.
