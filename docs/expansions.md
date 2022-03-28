# Expansions

## Why

Consider the following scenario:

```Python
class User(BaseModel):
    user_id: int
    name: str


class File(BaseModel):
    file_id: int
    file_name: str
    owner_user_id: int


class FileList(BaseModel):
    files: List[File]


@api.get("/users/{user_id}", response_model=User)
def get_user_by_id(user_id: str) -> User:
    return get_user(user_id)


@api.get("/files", response_model=FileList)
def get_files() -> FileList:
    return FileList(files=get_all_files())
```

If we want to get the list of files AND the names of all of the owners of those
files, then we need potentially many API calls:

```Python
response = client.get("/files?fields=files.owner_user_id")
for file in response.json()["files"]:
    owner_response = client.get(f"/user/{file['owner_user_id']}")
    ...
```

One API call can turn into many.  Even if you have the foresight
to provide a bulk `get_user_by_multiple_ids` style endpoint, this
is still two calls instead of one and more complexity for the API
client.  Additionally, in order to scale, you may need to batch one
endpoint differently from the other anyway.

What would be preferred is "one call gets it all", something like:

```
GET /files?fields=files.file_name&fields=files.owner_user.name
```

response:

```json
{
    "files": [
        {
            "file_name": "whatever",
            "owner_user": {
                "name": "Bob"
            }
        }
    ]
}
```

## Simple Expansions on Pydantic Models

```Python
from pydantic_sparsefields import ModelExpansion

class File(BaseModel):
    some_attribute: str
    owner_user_id: int

    def lookup_owner_user(self, context: Any) -> User:
        return get_user_model(self.owner_user_id)

    class Config:
        fieldsets = {
            "owner_user": ModelExpansion(
                expansion_method="lookup_owner_user"
                response_model=User,
            ),
            "default": ["some_attribute", "owner_user_id"],
        }
```

In this configuration when an `owner_user` expansion is requested
then `self.lookup_owner_user()` will be callled on the `File` object
instance to populate the expanded user object.

The result will look like:

```json
{
    "some_attribute": "blah",
    "owner_user_id": 1234,
    "owner_user": {
        "user_id": 1234,
        "more": "user data"
    }
}
```

## Expansion Configuration

```Python
class ModelExpansion:
    expansion_method_name: str
    merge_fields_upwards: Optional[bool] = False
    response_model: Optional[pydantic.BaseModel] = None
```


**expansion_method_name**: Required.  Name of the method
on the model which will be called by the expander.

The expected signature of the `expansion_method` is:

```Python

    def expansion_method(self, context: Any) -> MyExpandedModel:
```

The return type can be:

* A Pydantic BaseModel:  Further nested field/expansion processing will
  be done on this model if configured.

* Any scalar or data structure value that can be JSON encoded.

* A list of BaseModel or scalars

* An `Awaitable` (asyncio Future, Task or coroutine) that resolves
to any of the above.

**merge_fields_upwards**: Optional, default False.  If true, the
expander will attempt to merge items inside the object returned by
expansion into the parent object.  If false, then the name of expansion
will become a key in the parent object with its value set to the expansion
result.

**response_model**: Optional subclass of `pydantic.BaseModel` the
expanded object will be cast to.  This is mainly used as a type
hint by the pydantic JSON spec generator.

If possible, multiple expansions in a single request that return
awaitables will be coalesced for more efficient lookups (such as
bulk database queries).  An `aiodataloader` example is given below.

**Note:** It is important to set the return type of the expansion method
correctly in order for any further fieldset/expansion processing to occur
and for schema generation to be correct.

**Note:** For nested `fieldsets` requests (including nested expansions)
to work here the `expansion_method` **must** return a pydantic model, list
of pydantic models or an awaitable that resolves to the same.

**Warning:** Although easy and convenient, the simple example above
causes code to be run per `File` object.  In otherwords, if returning
a list of many `File` objects and requesting the `owner_user`
expansion on each one then that expansion code will be run for each
`File` object separately.  If `get_user_model` involves a database call, then
that's a database call **per file**.  To get around this, you can
coalesce expansion calls with the `Data Loader` method below.

## Data Loader example

This example uses [aiodataloader](https://pypi.org/project/aiodataloader/)
to consolidate multiple expansions into one database call but any method
using asyncio awaitables could be used.

If you are providing your own implementation, `pydantic_sparsefields`
will expect consolidation of load activity to occur when calling
`asyncio.gather` on all the Awaitable expansion results you give
it.

```Python
from typing import Awaitable

from aiodataloader import DataLoader
from pydantic_sparsefields import ModelExpansion, render_fieldset_model
from sqlalchemy import select

from .mymodels import UserORMModel

# This will be the object we ask to be expanded from inside the File object below
class User(BaseModel):
    user_id: int
    name: str

    class Config:
        orm_mode = True


# The batch loader function.  The DataLoader will aggregate as many individual
# loads as it can into one single call to this function.  This is the place to
# create load efficiency.
async def batch_load_users(user_ids: list[int]) -> list[user]:
    user_db_objects = my_database_session.execute(
        select(UserORMModel).where(UserORMModel.user_id.in_=user_ids)
    )

    # Note that the aiodataloader will wrap this in a future for us although
    # we could also return a coroutine from here.

    # The final product here needs to be pydantic Models and not SQLAlchemy models.
    return list([User.from_orm(row.UserORMModel) for row in user_db_objects.all()])

# Note: Consolidating multiple `load` calls into one database fetch with
# aiodataloader requires insuring that all of the dataloader calls
# occur within the same event loop, otherwise you will get errors
# about events in different loops.
#
# Although this example uses a global data loader, in a real world
# scenario you should use something scoped to at least the thread
# your event loop is running inside of.  For web applications, this
# should probably be scoped to the request object itself.
#
user_data_loader = DataLoader(batch_load_fn=batch_load_users)


# Define the expansion on the "parent" model:
class File(BaseModel):
    file_id: int
    file_name: str
    owner_user_id: int

    def expand_owner_user(self, context: DataLoader) -> Awaitable:
        # Multiple calls to this in one response will turn into
        # a single call to the dataloader `batch_load_fn`.

        # The `context` here is the same value that is passed
        # to `render_fieldset_model.expansion_context` below.

        return context.load(self.owner_user_id)

    class Config:
        fieldsets = {
            "owner_user": ModelExpansion(
                response_model=User,
                expansion_method_name="expand_owner_user",
            )
        }


class ManyFiles(BaseModel):
    files: List[File]



result = render_fieldset_model(
    model=ManyFiles(....),
    fieldsets=["files.owner_user"],
    expansion_context=user_data_loader,
)
```


## Expansion Method: Roll your own

If you want to implement your own expansion method, subclass
`pydantic_sparsefields.models.ExpansionBase` and implement the
`expand` methods.

Note that the `expand` return must be an Awaitable that resolves
to a concrete pydantic model, or something python's JSON serializer
understands (including scalar values).


<a name="deepwarning"></a>
## Warning: Beware Deeply Nested Expansions

Expansions are designed to balance the expense of multiple API
calls against the expense of the server looking up multiple
objects as part of a single request.

Even though the DataLoader expansion will coalesce loading activity
as much as possible, be aware that nested expansions cause a new
set of DataLoader calls for each level.  This is because the secondary
expansions are not known until the first expansions are complete.
Allowing this to arbitrary depth may be a performance issue.  Use
the `maximum_expansion_depth` parameter to set limits on this
behavior.
