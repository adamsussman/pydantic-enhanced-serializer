# Configuration and Usage

## Use `pydantic_enhanced_serialzier.render_fieldset_model` instead of `model.dict()`

```Python
    from pydantic_enhanced_serialzier import render_fieldset_model

    result = render_fieldset_model(
        model=some_pydantic_model_instance,
        fieldsets=["list", "of", "field", "requests"],
        maximum_expansion_depth=5,
        raise_error_on_expansion_not_found=False,
        expansion_context=any_object,
        exclude_unset=False,
        exclude_defaults=False,
        exclude_none=False,
    )
```

Parameters:

* `model`: 
    An instance of `pydantic.BaseModel`, optionally with
    `Config.fieldsets` defined.

    See the [Model Configuration](#config) section for more information.

* `fieldsets`: 
    A string or list of strings specifying which fields, fieldsets
    and expansions are desired in the output.

    See [Fieldsets parameter](#fieldsetsparam) section for more information.

* `maxiumum_expansion_depth`:
    Limit how many levels of deeply nested expansions are executed.
    Defaults to 5.

    See [Expansions](expansions.md#deepwarning) for more information.

* `raise_error_on_expansion_not_found`:
    If true and an expansion expands to `None`, an exception will be raised.
    Defaults to False.

* `expansion_context`:
    An arbitraty object that will be passed though to expansion code at runtime
    as a helper (for example a cache pointer, request object, etc).
    Defaults to None.

* `exclude_unset`:
    Same as [Pydantic's model.dict(...)](https://pydantic-docs.helpmanual.io/usage/exporting_models/#modeldict)

* `exclude_defaults`:
    Same as [Pydantic's model.dict(...)](https://pydantic-docs.helpmanual.io/usage/exporting_models/#modeldict)

* `exclude_none`:
    Same as [Pydantic's model.dict(...)](https://pydantic-docs.helpmanual.io/usage/exporting_models/#modeldict)


<a name="fieldsetsparam"></a>
## The fieldsets paramter

### Dotted String Paths

The value of the `fieldsets` parameter is a list of strings.  Each string
is a dotted path into the response object.


```Python
fieldsets=[
    "field1",
    "submodel.field2",
    "submodel.subsubmodel.field3"
]
```

Would return:

```json
{
    "field1": "value1",
    "submodel": {
        "field2": "value2",
        "subsubmodel": {
            "field3": "value3"
        }
    }
}
```

### Addressing Lists of Models

If a field returns a list of models, the index is not needed in the
field path:

```Python
fieldsets=["items.field1"]
```

Would return:

```json
{
    "items": [
        {
            "field1": "value1"
        },
        {
            "field1": "value2"
        },
        {
            "field1": "value3"
        }
    ]
}
```

### Comma Seperated Paths

For convenience, a single field value can be a comma seperated list of paths.  This can
be used instead of or in combination with lists of field paths.

```Python
fieldsets="path.to.field1,path.to.field2"
```
        
<a name="config"></a>
## Configuring Models and Field lookup behavior

Fieldset definitions are made inside the same "Config" class that pydantic uses.

```python
class MyModel(BaseModel):
    field1: str
    field2: str
    field3: str
    field4: str
    field5: str
    some_other_object_id: str

    class Config:
        fieldsets: dict = {
            "default": ["field1", "field2"],
            "extra_stuff": ["field3", "field4"],
            "some_other_object": ModelExpansion(...),
        }
```

## Field lookup rules:

### 1. No Config

If `Config.fieldsets` is not present at all, then this model will
behave like a default pydantic model when `model.dict()` is called:
ALL fields will be returned regardless of the contents of the
`fieldsets` parameter.

### 2. Default Set/Collection

If `Config.fieldsets` contains a `default` definition, then the
fields listed in the value will ALWAYS be returned, no matter what
else the client does or does not ask for in the `fieldsets` parameter.
If no other fields are requested then ONLY the default fields will be
returned.

```json
fieldsets=[]
```

returns:

```json
{"field1": "value1", "field2": "value2"}
```

Asking for non-default fields only will still include the default fields.

```Python
fieldsets=["field3"]
```

returns:

```json
{"field1": "value1", "field2": "value2", "field3": "value3"}
```

This is also what will be returned if you use the name of a nested
object in `fieldsets`, but not any other field names.

```Python
fieldsets=["some_sub_model"]
```

returns:

```json
{"some_sub_model": {"the": "default", "fields":  "of sub_model..."}}
```

The default fieldset can also contain `"*"` to indicate **all** fields.

```Python
class MyModel(BaseModel):
    field1: str
    field2: str

    class Config:
        fieldsets = {
            "default": ["*"],
        }
```


### 3. Field by Name

If `fieldsets` parameter path contains the name of a defined
field of the model, it will be present in the response.

In the above example, `field5` will never be returned unless it is
specifically asked for in `fieldsets`.

```Python
fieldsets=["field5"]
```

### 4. Field by Named Set/Collection

If the `fieldsets` request path contains a value that is present
as a key in `Config.fieldsets` and which isn't an actual field name,
then the value of that key lists the field names that will be returned.

```Python
fieldsets=["extra_stuff"]
```

returns:

```json
{"field3": "value3", "field4": "value5"}
```

### 5. Nested objects all the way down

You can nest objects inside each other however you want and use the
dotted notation to address them.  The only requirement is that all
nested objects in the response must either by Pydantic Models or
lists of Pydantic models.

This all works based on schemas, so you cannot use `fieldsets` to
address inside of raw dicts, for example.

### 6. Expansions

A fieldset name may refer to an `Expansion` instead of other fields.  If an expansion
is requested, additional code will be run to lookup the expanded object and return it
in the response.

See [Expansions](expansions.md) for more detailed information about expansions.

No expansion:

```Python
fieldsets=["some_other_object_id"]
```

returns:

```json
{
    "some_other_object_id": "12345"
}
```

Expansion:

```Python
fieldsets=[
    "some_other_object_id",
    "some_other_object.other_field"
]
```

returns:

```json
{
    "some_other_object_id": "12345",
    "some_other_object": {              # Even though `some_other_object` is NOT a defined pydantic field!
        "other_field": "other_value"
    }
}
```
