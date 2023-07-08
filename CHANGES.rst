Version 1.1.4
-------------

Released TBA

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
