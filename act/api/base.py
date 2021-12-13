import copy
import json
import re
import types
from logging import error, info

import requests

from . import DEFAULT_ACCESS_MODE
from .re import UUID_MATCH
from .schema import Field, MissingField, Schema, schema_doc


class NotImplemented(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ArgumentError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ResponseError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ValidationError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


ERROR_HANDLER = {
    # Mapping of message templates provided in 412 errors from backend to
    # Exceptions that will be raised
    "fact.not.valid": lambda msg: ValidationError(
        "{message} ({field}={parameter})".format(**msg)
    ),
    "object.not.valid": lambda msg: ValidationError(
        "{message} ({field}={parameter})".format(**msg)
    ),
    "organization.not.exist": lambda msg: ValidationError(
        "{message} ({field}={parameter})".format(**msg)
    ),
}


def request(method, user_id, url, requests_common_kwargs=None, **kwargs):
    """Perform requests towards API

    Args:
        method (str):         POST|GET
        user_id (int):        Act user ID
        url (str):            Absolute URL for the endpoint
        **kwargs (keywords):  Additional options passed to requests json parameter
                              the following fields:"""

    if not requests_common_kwargs:
        requests_common_kwargs = {}

    requests_kwargs = copy.copy(requests_common_kwargs)

    # Apply common request arguments
    requests_kwargs.update(kwargs)

    # Make sure we have header as argument
    if "headers" not in requests_kwargs:
        requests_kwargs["headers"] = {}

    # Add User ID as header
    if user_id:
        requests_kwargs["headers"]["ACT-User-ID"] = str(user_id)

    try:
        res = requests.request(method, url, **requests_kwargs)
    except requests.exceptions.ConnectionError as e:
        raise ResponseError("Connection error {}".format(e))

    if res.status_code == 412:
        error_messages = res.json()["messages"]

        # Example output on object validation error:
        # {"responseCode": 412, "limit": 0, "count": 0, "messages": [{"type": "FieldError", "message": "Object did not pass validation against ObjectType.", "messageTemplate": "object.not.valid", "field": "objectValue", "parameter": "127.0.0.x", "timestamp": "2019-09-23T18:19:26.476Z"}], "data": null, "size": 0}

        # Raise ValidationError for 412/Object validation errors
        for msg in error_messages:
            msg_template = msg.get("messageTemplate")
            if msg_template in ERROR_HANDLER:
                raise ERROR_HANDLER[msg_template](msg)

        # All other, unhandled errors - log to error() and raise generic exception
        error("Request failed: {}, {}, {}".format(url, kwargs, res.status_code))
        raise ResponseError(res.text)

    elif res.status_code not in (200, 201):
        error("Request failed: {}, {}, {}".format(url, kwargs, res.status_code))
        raise ResponseError(
            "Unknown response error {}: {}".format(res.status_code, res.text)
        )

    try:
        return res.json()

    except json.decoder.JSONDecodeError:
        raise ResponseError(
            "Error decoding response {}: {}".format(res.status_code, res.text)
        )


class ActResultSet(object):
    """Represents a list of Act entries"""

    def __init__(self, response, deserializer, config=None):
        """Initialize result set
        Args:
            response (str):       JSON response from Act. This should include
                                  the following fields:
                                    - count: the number of entries fetched
                                    - limit: the limit in the query
                                    - responseCode: responseCode from the API
                                    - size: the total number of entries in the platform
                                    - data (array): array of entries

            deserializer (class): Deseralizer class"""

        if not isinstance(response["data"], list):
            raise ResponseError("Response should be list: {}".format(response["data"]))

        self.data = [deserializer(**d).configure(config) for d in response["data"]]

        self.size = response["size"]
        self.count = response["count"]
        self.limit = response["limit"]
        self.status_code = response["responseCode"]

    @property
    def complete(self):
        """Returns true if we have recieved all data that exists on the endpoint"""
        return self.size >= self.count

    def __call__(self, func, *args, **kwargs):
        """Call function on each data entry"""

        self.data = [getattr(item, func)(*args, **kwargs) for item in self.data]
        return self

    def __len__(self):
        """Returns the number of entries"""
        return len(self.data)

    def __getitem__(self, sliced):
        return self.data[sliced]

    def __str__(self):
        if not self.data:
            return "No result"
        return "\n".join(["{}".format(item) for item in self.data])

    def __bool__(self):
        """Return True for non empty result sets"""
        if self.size > 0:
            return True

        return False

    def __repr__(self):
        """
        Representation of result set
        """

        return repr(self.data)

    def __iter__(self):
        """Iterate over the entries"""
        return self.data.__iter__()


class Config(object):
    """Config object"""

    act_baseurl = None
    user_id = None
    requests_common_kwargs = {}

    def __init__(
        self,
        act_baseurl,
        user_id,
        requests_common_kwargs=None,
        origin_name=None,
        origin_id=None,
        access_mode=DEFAULT_ACCESS_MODE,
        organization=None,
        object_validator=None,
        object_formatter=None,
        strict_validator=False,
    ):
        """
        act_baseurl - url to ACT instance
        use_id - ACT user ID
        requests_common_kwargs - options that will be passed to requests when connecting to ACT api
        origin_name - ACT origin name that will be added to all facts where origin is not set
        origin_id - ACT origin id that will be added to all facts where origin is not set

        object_validator: function that should return True if object validates, otherwise None
        object_formatter: function that should return a formatted version of the type (e.g. lowercase)

        Only one of origin_name of origin_id must be specified.
        """

        if origin_id and not re.search(UUID_MATCH, origin_id):
            raise ArgumentError("origin_id id not a valaid UUID: {}".format(origin_id))

        self.act_baseurl = act_baseurl
        self.user_id = user_id
        self.requests_common_kwargs = requests_common_kwargs
        self.origin_name = origin_name
        self.origin_id = origin_id
        self.access_mode = access_mode
        self.organization = organization
        self.object_validator = object_validator
        self.object_formatter = object_formatter
        self.strict_validator = strict_validator


class ActBase(Schema):
    """Act object inheriting Schema, to support serializing and
    deserializing."""

    config = None

    SCHEMA = []

    @schema_doc(SCHEMA)
    def __init__(self, *args, **kwargs):
        super(ActBase, self).__init__(*args, **kwargs)

    def configure(self, config):
        """Set config object"""

        self.config = config
        return self

    def api_request(self, method, uri, **kwargs):
        """Send request to API and update current object with result"""

        response = request(
            method,
            self.config.user_id,
            "{}/{}".format(self.config.act_baseurl, uri),
            self.config.requests_common_kwargs,
            **kwargs,
        )

        return response

    def api_post(self, uri, **kwargs):
        """Send POST request to API with keywords as JSON arguments"""

        return self.api_request("POST", uri, json=kwargs)

    def api_put(self, uri, **kwargs):
        """Send PUT request to API with keywords as JSON arguments"""

        return self.api_request("PUT", uri, json=kwargs)

    def api_delete(self, uri, params=None):
        """Send DELETE request to API
        Args:
            uri (str):     URI (relative to base url). E.g. "v1/factType"
            params (Dict): Parameters that are URL enncoded and sent to the API"""

        return self.api_request("DELETE", uri, params=params)

    def api_get(self, uri, params=None):
        """Send GET request to API
        Args:
            uri (str):     URI (relative to base url). E.g. "v1/factType"
            params (Dict): Parameters that are URL enncoded and sent to the API"""

        return self.api_request("GET", uri, params=params)

    def __eq__(self, other):
        "Equality operator"

        return hash(self) == hash(other)

    def __hash__(self):
        "__hash__ should be implemented on all derived classes"
        raise NotImplementedError(
            f"{self.__class__.__name__} is missing __hash__ method"
        )


class NameSpace(ActBase):
    """Namespace - serialized object specifying Namespace"""

    SCHEMA = [
        Field("name"),
        Field("id"),
    ]

    def __hash__(self):
        return hash(
            (
                self.__class__.__name__,
                self.name,
            )
        )


class Organization(ActBase):
    """Manage Organization"""

    SCHEMA = [
        Field("name"),
        Field("id"),
    ]

    def __hash__(self):
        return hash(
            (
                self.__class__.__name__,
                self.name,
            )
        )

    def serialize(self):
        # Return None for empty objects (non initialized objects)
        # otherwize return id or name
        return self.id or self.name or None


def origin_serializer(origin):
    # Return None for empty objects (non initialized origins)
    # otherwize return id or name
    if not origin:
        return None
    return origin.id or origin.name


class Origin(ActBase):
    """Manage Origin"""

    SCHEMA = [
        Field("name"),
        Field("id"),
        Field("namespace", serializer=False, deserializer=NameSpace),
        Field("organization", deserializer=Organization),
        Field("description"),
        Field("trust"),
        Field("type", serializer=False),
        Field("flags", serializer=False),
    ]

    def __hash__(self):
        return hash(
            (self.__class__.__name__, self.name, self.namespace, self.organization)
        )

    @schema_doc(SCHEMA)
    def __init__(self, *args, **kwargs):
        super(Origin, self).__init__(*args, **kwargs)

    def get(self):
        """Get Origin"""

        if not self.id:
            raise MissingField("Must have fact ID to get origin")

        origin = self.api_get("v1/origin/uuid/{}".format(self.id))["data"]
        self.data = {}
        self.deserialize(**origin)
        return self

    def add(self):
        """Add Origin"""
        params = self.serialize()

        origin = self.api_post("v1/origin", **params)["data"]

        # Empty data and load new result from response
        self.data = {}
        self.deserialize(**origin)

        info("Created origin: {}".format(self.name))

        return self

    def delete(self):
        """Delete Origin"""

        if not self.id:
            raise MissingField("Must have fact ID to delete origin")

        origin = self.api_delete("v1/origin/uuid/{}".format(self.id))["data"]
        self.data = {}
        self.deserialize(**origin)

        info("Deleted origin: {}".format(self.name))
        return self


class Comment(ActBase):
    """Namespace - serialized object specifying Namespace"""

    SCHEMA = [
        Field("comment"),
        Field("id"),
        Field("timestamp", serializer=False),
        Field("reply_to"),
        Field("origin", deserializer=Origin, serializer=False),
    ]

    def __hash__(self):
        return hash(
            (
                self.__class__.__name__,
                self.comment,
                self.timestamp,
            )
        )
