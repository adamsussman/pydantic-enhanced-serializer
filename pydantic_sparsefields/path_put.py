from copy import copy
from typing import Any, Dict, List, Union, cast

PATH_TYPE = List[Union[str, int]]


def path_put(data: Any, path: Union[PATH_TYPE, str], value: Any) -> Any:
    """
    >>> path_put({}, "foo", "bar")
    {'foo': 'bar'}

    >>> path_put({}, "foo.bar.baz", "zoom")
    {'foo': {'bar': {'baz': 'zoom'}}}

    >>> path_put({}, "boo", [1, 2, 3, 4])
    {'boo': [1, 2, 3, 4]}

    >>> path_put({"aa": {"bb": "cc"}}, "aa.cc", "dd")
    {'aa': {'bb': 'cc', 'cc': 'dd'}}

    >>> path_put({"aa": {"bb": "cc"}}, "zz", {"foo": "bar"})
    {'aa': {'bb': 'cc'}, 'zz': {'foo': 'bar'}}

    >>> path_put({"aa": {"bb": "cc"}}, "aa.foo", "bar")
    {'aa': {'bb': 'cc', 'foo': 'bar'}}

    >>> path_put({}, "aa.0", "bar")
    {'aa': ['bar']}

    >>> path_put({}, "aa.3", "bar")
    {'aa': [None, None, None, 'bar']}

    >>> path_put({}, "aa.1.2", "bar")
    {'aa': [None, [None, None, 'bar']]}

    >>> path_put({}, "aa.1", {"foo": "bar"})
    {'aa': [None, {'foo': 'bar'}]}

    >>> path_put({}, "aa.1.foo", "bar")
    {'aa': [None, {'foo': 'bar'}]}

    >>> path_put({}, "aa.1.foo", {"bar": "baz"})
    {'aa': [None, {'foo': {'bar': 'baz'}}]}

    >>> path_put({"aa": [{"foo": "bar"}]}, "aa.0", {"moo": "shoo"})
    {'aa': [{'foo': 'bar', 'moo': 'shoo'}]}

    >>> path_put({"aa": [{"foo": "bar"}]}, "aa.0.baz.1", {"moo": "shoo"})
    {'aa': [{'foo': 'bar', 'baz': [None, {'moo': 'shoo'}]}]}

    >>> path_put({}, [], {"foo": "bar"})
    {'foo': 'bar'}

    >>> path_put({"aa": "bb"}, "", {"foo": "bar"})
    {'aa': 'bb', 'foo': 'bar'}

    """
    if data is None:
        return value

    if not path:
        path = []

    if isinstance(path, str):
        rendered_path = cast(PATH_TYPE, path.split("."))
    else:
        rendered_path = path

    if isinstance(data, dict):
        _path_put_dict(data, rendered_path, value)

    elif isinstance(data, list):
        _path_put_list(data, rendered_path, value)

    else:
        raise ValueError(
            f"path_put can only be used on dicts or lists, got {str(type(data))}"
        )

    return data


def _path_put_dict(data: Dict, path: PATH_TYPE, value: Any) -> None:
    if not path and isinstance(value, dict):
        data.update(value)
        return

    if len(path) == 1:
        data[path[0]] = value
        return

    path0 = path.pop(0)
    if path0 not in data:
        data[path0] = [] if isinstance(path[0], int) or path[0].isnumeric() else {}

    path_put(data[path0], path, value)


def _path_put_list(data: List, path: PATH_TYPE, value: Any) -> None:
    original_path = copy(path)

    try:
        path0 = int(path.pop(0))
    except (ValueError, IndexError):
        raise KeyError(str(original_path))

    if len(data) < path0 + 1:
        for _i in range((path0 + 1) - len(data)):
            data.append(None)

    if len(path):
        # more depth
        if data[path0] is None:
            data[path0] = [] if isinstance(path[0], int) or path[0].isnumeric() else {}

        path_put(data[path0], path, value)

    elif isinstance(value, dict):
        if data[path0] is None:
            data[path0] = {}

        if not isinstance(data[path0], dict):
            raise ValueError(
                f"{str(original_path)} is not a dict but value asking to be merged is"
            )

        data[path0].update(value)

    else:
        data[path0] = value
