import uuid
import copy
import re
import pickle
import random
import pytest
from act.api.schema import Schema, Field
from act.api import RE_UUID_MATCH, RE_TIMESTAMP_MATCH

# the Object/Fact and testdata here is a simplified version of the Object/Facts used in ACT
# The purpose is to only test core functionality of the Schema

DIRECTIONS = ["FactIsDestination", "FactIsSource", "BidirectionalFact"]


def random_hostname():
    """Return random (dummy) hostname"""
    return "".join([chr(random.randint(ord("a"), ord("z")))
                    for i in range(1, random.randint(5, 12))]) + ".com"


class ObjectType(Schema):
    SCHEMA = [
        Field("name"),
        Field("id"),
    ]


class Object(Schema):
    SCHEMA = [
        Field("type", deserializer=ObjectType),
        Field("value"),
        Field("id"),
        Field("object", flatten=True),
        Field("direction"),
    ]

    def serialize(self, exclude_empty=True, to_camel_case=True):
        """Custom serializer for Object"""

        return {
            "object": {
                "id": self.id,
                "value": self.value,
                "type": {
                    "id": self.type.name,
                    "name": self.value,
                }
            },
            "direction": self.direction
        }


class FactType(Schema):
    SCHEMA = [
        Field("name"),
        Field("id"),
    ]


class Fact(Schema):
    SCHEMA = [
        Field("type", deserializer=FactType,
              serializer=lambda fact_type: fact_type.name),
        Field("value"),
        Field("id", serializer=False),
        Field("timestamp", serializer=False),
        Field("objects", default=[], serialize_target="bindings",
              deserializer=Object),
    ]


fact_test_data = {
    "id": "00fb833d-3f74-4d70-9f00-d189eba6d038",
    "type": {
        "id": "c07d55c8-d976-4b06-841c-9d687c69bfe7",
        "name": "seenIn"
    },
    "value": "report",
    "timestamp": "2018-03-21T09:31:44.541Z",
    "objects": []
}


object_test_data = {
    "object": {
        "id": "7dbf4d10-ff46-4d70-a681-ad08c2047d96",
        "type": {
            "id": "dbab2678-5110-405e-89b9-df6d5efe4a61",
            "name": "fqdn"
        },
        "value": "ukuoka.cloud-maste.com"
    },
    "direction": "FactIsDestination"
}

def __test_data():
    # Generate test data
    objects = []
    for _ in range(0, 5):  # Generate random facts
        obj = copy.copy(object_test_data)
        obj["id"] = str(uuid.uuid4())
        obj["object"]["value"] = random_hostname()
        obj["object"]["direction"] = random.choice(DIRECTIONS)
        objects.append(obj)

    fact = copy.copy(fact_test_data)
    fact["objects"] = objects

    return Fact(**fact)


def test_schema():
    f = __test_data()
    assert re.search(RE_UUID_MATCH, f.id)
    assert re.search(RE_UUID_MATCH, f.type.id)
    assert re.search(RE_TIMESTAMP_MATCH, f.timestamp)

    # Facts should not have "bindings" as they are stored in "objects"
    with pytest.raises(AttributeError):
        # pylint: disable=pointless-statement
        f.bindings

    # Get first object
    obj = f.objects[0]

    # Objects should not have "object property" (the content from it should be
    # flattened into parrent)
    with pytest.raises(AttributeError):
        # pylint: disable=pointless-statement
        obj.object

    # When serialized, we should get back data in "object"
    assert isinstance(f.serialize()["bindings"][0]["object"], dict)


def test_pickle():
    """
    Test that we can pickle and unpickle a schema object and get the same schema
    """
    fact = __test_data()

    pickled_fact = pickle.dumps(fact)

    assert fact == pickle.loads(pickled_fact)


def test_set_get():
    f = __test_data()

    # type.name should be seenIn, both when referenced using dot
    # notation and when obtaining value through data dictionary
    assert f.type.name == "seenIn"
    assert f.data["type"].data["name"] == "seenIn"

    # Verify that we can set schema attributes directly using dot notation
    f.type.name = "mentions"

    # The name should then be the same when we reference it from the data dictionary
    assert f.data["type"].data["name"] == "mentions"
