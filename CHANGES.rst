Version 2.1.0
-------------

Released 2023-12-01

- Fix how the json schema generator handles references to request, response and expansion
  objects, and especially references to objects nested inside them.  Make sure such references
  are propagated correctly.

Version 2.0.0
-------------

Released 2023-11-27

BREAKING CHANGES

- Converted to Pydantic 2.x
- New Configuration method: No longer uses `class Config:` as that was removed in pydantic 2

    ```
        from typing import ClassVar
        from pydantic_enhanced_serializer import FieldsetConfig

        class SomeModel(BaseModel):
            some_field: str

            model_config = ConfigDict(...)  # new form of class Config

            fieldset_config: ClassVar = FieldsetConfig(
                fieldsets={ ... as before ... }
    ```

- New Augmented JSON Schema calling convention:

    ```
        from pydantic_enhanced_serializer import FieldsetGenerateJsonSchema

        schema = SomeModel.model_json_schema(schema_generator=FieldsetGenerateJsonSchema)
    ```

- Removed `augment_schema_with_fieldsets`, replaced with new `model_json_schema` usage.


Version 1.1.5
-------------

Released 2023-10-01

- Fix bug where dicts nested inside the same model schema but with different individual key sets
  were interfering with each other and causing some dicts to not return all (often any) of their keys.


Version 1.1.4
-------------

Released 2023-07-08

- Fix case of nested array expansions with added fields overwritting each others attributes.


Version 1.1.3
-------------

Released 2023-06-22

- Remove all export of unrelated "#components", since nothing actually uses it.  Callers will have
  to manage extra/unknown referenced components themselves.


Version 1.1.2
-------------

Released 2023-06-15

- Change expansion object schema $ref in openapi to point at #/components/schema root to be more
  in line with OpenAPI 3.x standards.


Version 1.1.1
-------------

Released 2023-04-26

- Fix case of Optional[Dict] where value is None


Version 1.1.0
-------------

Released 2023-04-13

- Removed the flask integration and moved it to its own library: `flask-pydantic-api`
  https://github.com/adamsussman/flask-pydantic-api

- Improved extra fieldset description per field in schemas.

- Added fieldset notes for fields that do not appear in any fieldset configuration.

- Added test method to see if models or submodels have fieldset configurations.


Version 1.0.1
-------------

Released 2023-03-08

- Added README.md text as pypi project description with pointer to full documentation on github.


Version 1.0.0
-------------

Released 2023-03-08

- Initial public release.
