from logging import info, warning

import act.api

from . import DEFAULT_VALIDATOR
from .base import ActBase, NameSpace, ActResultSet, Organization
from .schema import Field, MissingField, schema_doc


class ObjectType(ActBase):
    SCHEMA = [
        Field("name"),
        Field("id"),
        Field("validator", default="RegexValidator"),
        Field("validator_parameter", default=DEFAULT_VALIDATOR),
        Field("namespace", deserializer=NameSpace),
    ]

    @schema_doc(SCHEMA)
    def __init__(self, *args, **kwargs):
        super(ObjectType, self).__init__(*args, **kwargs)

    def add(self):
        params = self.serialize()
        object_type = self.api_post("v1/objectType", **params)["data"]

        # Empty data and load new result from response
        self.data = {}
        self.deserialize(**object_type)

        info("Created object type: {}".format(self.name))

        return self


class ObjectStatistics(ActBase):
    """ObjectStatistics - serialized object specifying statistics"""

    SCHEMA = [
        Field("type", deserializer=ObjectType),
        Field("count"),
        Field("last_seen_timestamp", serializer=False),
        Field("last_added_timestamp", serializer=False),
    ]


class Object(ActBase):
    """Manage objects"""
    SCHEMA = [
        Field(
            "type",
            deserializer=ObjectType,
            serializer=lambda object_type: object_type.name),
        Field("value"),
        Field("id"),
        Field(
            "statistics",
            deserializer=ObjectStatistics,
            serializer=False),
        Field("object", flatten=True),
        Field("direction"),
        Field("object_type", deserialize_target="type", serializer=False),
        Field("object_value", deserialize_target="value", serializer=False),
    ]

    @schema_doc(SCHEMA)
    def __init__(self, *args, **kwargs):
        super(Object, self).__init__(*args, **kwargs)

    def facts(self):
        """Get facts"""

        if self.id:
            url = "v1/object/uuid/{}/facts".format(self.id)
        elif self.type.name and self.value:
            url = "v1/object/{}/{}/facts".format(self.type.name, self.value)
        else:
            raise MissingField(
                "Must have either object ID or object type/value to get facts")

        response = self.api_post(url)

        result_set = ActResultSet(response, act.api.fact.Fact)

        # Add authentication information to all facts
        return result_set("configure", self.config)

    def __eq__(self, other):
        """ Check equality with another object """

        # If other is None, return True if id, type and value is None
        if other is None:
            if self.id is None and self.type.name is None and self.value is None:
                return True
            return False

        # Otherwise, use equality check from super class
        return super(Object, self).__eq__(other)

    def serialize(self):
        # Return None for empty objects (non initialized objects)
        if not (self.id or self.value):
            return None
        # return default serializer
        return super(Object, self).serialize()

    def traverse(self, query=None):
        """Traverse from object"""

        if self.id:
            url = "v1/object/uuid/{}/traverse".format(self.id)
        elif self.type.name and self.value:
            url = "v1/object/{}/{}/traverse".format(self.type.name, self.value)
        else:
            raise MissingField(
                "Must have either object ID or object type/value to get facts")

        result = []
        for element in self.api_post(url, query=query)["data"]:
            if any(["sourceObject" in element, "destinationObject" in element]):
                result.append(act.api.fact.Fact(**element))
            elif "statistics" in element:
                result.append(act.api.fact.Object(**element))
            else:
                warning("Unable to guess element type: {}".format(element))
                result.append(element)

        # This returns the list as is and it is currently not deserialized
        # since it can return multiplel types. An improvement would be to
        # autodetect the types and deserialize accordingly

        return result

    def __bool__(self):
        """ Return False unless we either have an id or both type and value """
        if self.id or (self.type and self.value):
            return True

        return False

    def __str__(self):
        """
        Construnct string representation on this format
        (src_obj_type/src_obj_value))
        """

        return "({}/{})".format(self.type.name, self.value)
