import json
import copy
import functools
from logging import error, info, debug
import re
import requests
from .schema import Schema, Field, schema_doc, MissingField
from . import RE_UUID_MATCH, DEFAULT_ACCESS_MODE


class NotImplemented(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class InvalidData(Exception):
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

class OriginMismatch(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class OriginDoesNotExist(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class NotConnected(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


ERROR_HANDLER = {
        # Mapping of message templates provided in 412 errors from backend to
        # Exceptions that will be raised
        "object.not.valid": lambda msg: ValidationError(
            "{message} ({field}={parameter})".format(**msg)),
        "organization.not.exist": lambda msg: ValidationError(
            "{message} ({field}={parameter})".format(**msg))
}


def request(method, user_id, url, requests_common_kwargs = None, **kwargs):
    """Perform requests towards API

Args:
    method (str):         POST|GET
    user_id (int):        Act user ID
    url (str):            Absolute URL for the endpoint
    **kwargs (keywords):  Additional options passed to requests json parameter
                          the following fields:
"""

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
        res = requests.request(
            method,
            url,
            **requests_kwargs
        )
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
        error("Request failed: {}, {}, {}".format(
            url, kwargs, res.status_code))
        raise ResponseError(res.text)

    elif res.status_code not in (200, 201):
        error("Request failed: {}, {}, {}".format(
            url, kwargs, res.status_code))
        raise ResponseError(
            "Unknown response error {}: {}".format(res.status_code, res.text))

    try:
        return res.json()

    except json.decoder.JSONDecodeError:
        raise ResponseError(
            "Error decoding response {}: {}".format(res.status_code, res.text))


class ActResultSet(object):
    """Represents a list of Act entries"""

    def __init__(self, response, deserializer):
        """Initialize result set
Args:
    response (str):       JSON response from Act. This should include
                          the following fields:
                            - count: the number of entries fetched
                            - limit: the limit in the query
                            - responseCode: responseCode from the API
                            - size: the total number of entries in the platform
                            - data (array): array of entries

    deserializer (class): Deseralizer class
"""

        if not isinstance(response["data"], list):
            raise ResponseError(
                "Response should be list: {}".format(
                    response["data"]))

        self.data = [deserializer(**d) for d in response["data"]]

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

        self.data = [getattr(item, func)(*args, **kwargs)
                     for item in self.data]
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
        """ Return True for non empty result sets """
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
            requests_common_kwargs = None,
            origin_name=None,
            origin_id=None,
            access_mode=DEFAULT_ACCESS_MODE,
            organization=None):
        """
        act_baseurl - url to ACT instance
        use_id - ACT user ID
        requests_common_kwargs - options that will be passed to requests when connecting to ACT api
        origin_name - ACT origin name that will be added to all facts where origin is not set
        origin_id - ACT origin id that will be added to all facts where origin is not set

        Only one of origin_name of origin_id must be specified.
        """

        if origin_id and not re.search(RE_UUID_MATCH, origin_id):
            raise ArgumentError("origin_id id not a valaid UUID: {}".format(origin_id))

        self.act_baseurl = act_baseurl
        self.user_id = user_id
        self.requests_common_kwargs = requests_common_kwargs
        self.origin_name = origin_name
        self.origin_id = origin_id
        self.access_mode = access_mode
        self.organization = organization


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
            **kwargs
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
    params (Dict): Parameters that are URL enncoded and sent to the API
"""

        return self.api_request("DELETE", uri, params=params)

    def api_get(self, uri, params=None):
        """Send GET request to API
Args:
    uri (str):     URI (relative to base url). E.g. "v1/factType"
    params (Dict): Parameters that are URL enncoded and sent to the API
"""

        return self.api_request("GET", uri, params=params)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False # Different types -> not equal

        for field, value in self.data.items():
            # Only compare serialized fields. The other fields
            # have different representation if they are created locally
            # and not recieved from the back end
            if self.get_field(field).serializer is False:
                continue
            if field == "id":
                # Facts/objects may not have an ID, unless they are returned from the backend
                # We will check for inconsistencies below
                continue
            if other.data.get(field) != value:
                return False # Different field value

        # Two objects where all fields are equal do not have the same id
        if self.id and other.id and self.id != other.id:
            raise InvalidData("Two objects with equal fields do not have the same id")

        # All field values are equal
        return True


class NameSpace(ActBase):
    """Namespace - serialized object specifying Namespace"""

    SCHEMA = [
        Field("name"),
        Field("id"),
    ]


class Organization(ActBase):
    """Manage Organization"""

    SCHEMA = [
        Field("name"),
        Field("id"),
    ]

    def serialize(self):
        # Return None for empty objects (non initialized objects)
        # otherwize return id or name
        return self.id or self.name or None


@functools.lru_cache(maxsize=128)
def origin_map(config):
    """ Return lookup dictionary (name: uuid) for all known origins """

    # We put this as a separate function, with only config (baseurl, etc)
    # as the parameter. In this way, the cache will be used, since
    # the config will always be the same within the same session

    if not config.act_baseurl:
        raise NotConnected("act_baseurl is not configured, unable to fetch origins")

    # Create base object using the specified configuration
    base = ActBase()
    base.configure(config)

    debug("Looking up origins")

    # Return dictionary of name -> uuid of origins
    return {
        origin["name"]: origin["id"]
        for origin in base.api_get(
            "v1/origin",
            params={"limit": 0, "includeDeleted": False})["data"]
    }


def origin_lookup_serializer(origin, config=None):
    """ Serializer for origins that will lookup by name and verify name/id"""

    if config and config.act_baseurl:  # type: ignore
        # If we have specified act_baseurl, i.e we are connected to a backend,
        # serialize origin to uuid (or None)

        if not origin:
            return None

        if origin.id and not origin.name:
            # Origin specified by uuid, use this directly
            return origin.id

        if origin.name and not origin.id:
            # Lookup uuid by name
            origin_id = origin_map(config).get(origin.name)
            if not origin_id:
                raise OriginDoesNotExist("Unable to find origin with name {}".format(origin.name))
            return origin_id

        if origin.id and origin.name:
            if origin_map(config).get(origin.name) == origin.id:
                return origin.id

            raise OriginMismatch("Origin name and uuid specified, " +
                                 "but the uuid ({}) does not represent ".format(origin.id) +
                                 "the origin with this name ({})".format(origin.name))
        # No origin
        return None

    # Use default serialization, which will include a dictionary of the origin
    # object
    return origin.serialize()


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

    @schema_doc(SCHEMA)
    def __init__(self, *args, **kwargs):
        super(Origin, self).__init__(*args, **kwargs)

    def get(self):
        """Get Origin"""

        if not self.id:
            raise MissingField(
                "Must have fact ID to get origin")

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
            raise MissingField(
                "Must have fact ID to delete origin")

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
