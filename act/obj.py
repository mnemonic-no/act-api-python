from logging import info, warning
import act
from .schema import Field, schema_doc, MissingField
from .base import ActBase, NameSpace


class ObjectType(ActBase):
    SCHEMA = [
        Field("name"),
        Field("id"),
        Field("validator", default="RegexValidator"),
        Field("validator_parameter", default=act.DEFAULT_VALIDATOR),
        Field("entity_handler", default="IdentityHandler"),
        Field("entity_handler_parameter"),
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

        result_set = act.base.ActResultSet(response, act.fact.Fact)

        # Add authentication information to all facts
        return result_set("configure", self.config)

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
            if "objects" in element:
                result.append(act.fact.Fact(**element))
            elif "statistics" in element:
                result.append(act.fact.Object(**element))
            else:
                warning("Unable to guess element type: {}".format(element))
                result.append(element)

        # This returns the list as is and it is currently not deserialized
        # since it can return multiplel types. An improvement would be to
        # autodetect the types and deserialize accordingly

        return result


def object_binding_serializer(obj):
    binding = {
        "direction": obj.direction
    }

    if "id" in obj.data and obj.id:
        binding["objectID"] = obj.id
    else:
        binding["objectType"] = obj.type.name
        binding["objectValue"] = obj.value

    return binding
