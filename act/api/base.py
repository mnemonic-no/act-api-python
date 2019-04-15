import json
import copy
from logging import error
import requests
from .schema import Schema, Field, schema_doc


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
    requests_kwargs["headers"]["ACT-User-ID"] = str(user_id)

    res = requests.request(
        method,
        url,
        **requests_kwargs
    )

    if res.status_code == 412:
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
            requests_common_kwargs = None):
        """Set URL and USER ID, and optionally other arguments that will be passed on to request"""

        self.act_baseurl = act_baseurl
        self.user_id = user_id
        self.requests_common_kwargs = requests_common_kwargs


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
    """Manage FactSource"""

    SCHEMA = [
        Field("name"),
        Field("id"),
    ]


class Source(ActBase):
    """Manage FactSource"""

    SCHEMA = [
        Field("name"),
        Field("id"),
    ]


class Comment(ActBase):
    """Namespace - serialized object specifying Namespace"""

    SCHEMA = [
        Field("comment"),
        Field("id"),
        Field("timestamp", serializer=False),
        Field("reply_to"),
        Field("source", deserializer=Source, serializer=False),
    ]
