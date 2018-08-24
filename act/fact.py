from logging import info
import re
import json
import time
import act
from act import RE_UUID_MATCH

from .schema import Field, schema_doc, MissingField, ValidationError
from .obj import Object, ObjectType, object_binding_serializer
from .base import ActBase, Organization, NameSpace, Comment


class ObjectBinding(ActBase):
    SCHEMA = [
        Field(
            "object_type",
            deserializer=ObjectType,
            serializer=lambda object_type: object_type.id),
        Field("direction"),
    ]


class FactType(ActBase):
    """Manage FactType"""
    SCHEMA = [
        Field("name"),
        Field("id"),
        Field("validator", default="RegexValidator"),
        Field("validator_parameter", default=act.DEFAULT_VALIDATOR),
        Field("entity_handler", default="IdentityHandler"),
        Field("entity_handler_parameter"),
        Field("relevant_object_bindings", deserializer=ObjectBinding),
        Field("namespace", deserializer=NameSpace),
    ]

    @schema_doc(SCHEMA)
    def __init__(self, *args, **kwargs):
        super(FactType, self).__init__(*args, **kwargs)

    def add(self):
        params = self.serialize()
        fact_type = self.api_post("v1/factType", **params)["data"]

        # Empty data and load new result from response
        self.data = {}
        self.deserialize(**fact_type)

        info("Created fact type: {}".format(self.name))

        return self

    def add_binding(self, direction, object_type):
        """Add binding"""
        if not self.id:
            raise MissingField("Must have fact type ID")

        url = "v1/factType/uuid/{}".format(self.id)

        add_object_bindings = [{
            "objectType": object_type,
            "direction": direction
        }]

        fact_type = self.api_put(
            url, addObjectBindings=add_object_bindings)["data"]

        self.data = {}
        self.deserialize(**fact_type)

        info("Added binding to fact type {}: {} ({})".format(
            self.id, object_type, direction))

        return self

    def add_source_binding(self, object_type):
        return self.add_binding(act.FACT_IS_DESTINATION, object_type)

    def add_destination_binding(self, object_type):
        return self.add_binding(act.FACT_IS_SOURCE, object_type)

    def add_bidirectional_binding(self, object_type):
        return self.add_binding(act.BIDIRECTIONAL_FACT, object_type)

    def rename(self, name):
        if not self.id:
            raise MissingField("Must have fact type ID")

        old_name = self.name

        url = "v1/factType/uuid/{}".format(self.id)
        fact_type = self.api_put(url, name=name)["data"]

        self.data = {}
        self.deserialize(**fact_type)

        info("Renamed fact type {}: {} -> {}".format(self.id, old_name, name))

        return self


class RetractedFact(ActBase):
    """Retracted Fact"""

    SCHEMA = [
        Field("type", deserializer=FactType,
              serializer=lambda fact_type: fact_type.name),
        Field("value", default="-"),
        Field("id", serializer=False),
    ]


class Fact(ActBase):
    """Manage facts"""

    SCHEMA = [
        Field("type", deserializer=FactType,
              serializer=lambda fact_type: fact_type.name),
        Field("value", default="-"),
        Field("id", serializer=False),
        # For now, do not serialize/deserialize source
        Field("source", deserializer=False, serializer=False),
        Field("timestamp", serializer=False),
        Field("last_seen_timestamp", serializer=False),
        Field("in_reference_to", deserializer=RetractedFact, serializer=False),
        Field("organization", deserializer=Organization, serializer=False),
        Field("access_mode", default="Public"),
        Field("objects", default=[], serialize_target="bindings",
              deserializer=Object, serializer=object_binding_serializer),
        Field("bindings", deserialize_target="objects", serializer=False),
    ]

    @schema_doc(SCHEMA)
    def __init__(self, *args, **kwargs):
        super(Fact, self).__init__(*args, **kwargs)

    def __add_if_not_exists(self, *args, **kwargs):
        """Add binding if it does not exist"""
        binding = Object(*args, **kwargs)
        if binding not in self.data["objects"]:
            self.data["objects"].append(binding)

        return self

    def source(self, *args, **kwargs):
        """Add source binding. Takes all arguments applicable to
        act.Act.object"""

        return self.__add_if_not_exists(
            *args, direction=act.FACT_IS_DESTINATION, **kwargs)

    def destination(self, *args, **kwargs):
        """Add destination binding. Takes all arguments applicable to
        act.Act.object"""

        return self.__add_if_not_exists(
            *args, direction=act.FACT_IS_SOURCE, **kwargs)

    def bidirectional(self, *args, **kwargs):
        """Add bidirectional binding. Takes all arguments applicable to act.Act.object"""
        return self.__add_if_not_exists(
            *args, direction=act.BIDIRECTIONAL_FACT, **kwargs)

    def get(self):
        """Get fact"""

        if not self.id:
            raise MissingField(
                "Must have fact ID to get, or use search instead")

        fact = self.api_get("v1/fact/uuid/{}".format(self.id))["data"]
        self.data = {}
        self.deserialize(**fact)
        return self

    def add(self):
        """Add fact"""

        started = time.time()

        params = self.serialize()
        fact = self.api_post("v1/fact", **params)["data"]

        # Empty data and load new result from response
        self.data = {}
        self.deserialize(**fact)

        info("Created fact in %.2fs: data=%s" %
             (time.time() - started, json.dumps(fact)))

        return self

    def get_acl(self):
        """Get acl"""

        if not self.id:
            raise MissingField("Must have fact ID to resolve ACL")

        return self.api_get("v1/fact/uuid/{}/access".format(self.id))["data"]

    def grant_access(self, subject_uuid):
        """Grant access - not implemented yet"""

        raise act.base.NotImplemented("Grant access is not implemented")

    def get_comments(self):
        """Get comments
Args:
    None

Returns ActResultSet of Comments.

        """

        if not self.id:
            raise MissingField("Must have fact ID to get comments")

        res = self.api_get("v1/fact/uuid/{}/comments".format(self.id))
        return act.base.ActResultSet(res, Comment)

    def add_comment(self, comment, reply_to=None):
        """Add comment
Args:
    comment (str):    Comment to add
    reply_to (uuid):  Comment is a reply to another comment (specified by uuid)

Returns Fact object
        """

        if not self.id:
            raise MissingField("Must have fact ID to add comment")

        if reply_to and not re.search(RE_UUID_MATCH, reply_to):
            raise ValidationError("reply_to is not a valid UUID: {}".format(reply_to))

        self.api_post(
            "v1/fact/uuid/{}/comments".format(self.id),
            comment=comment, replyTo=reply_to)

        return self

    # pylint: disable=unused-argument,dangerous-default-value
    def retract(
            self,
            organization=None,
            source=None,
            access_mode=None,
            comment=None,
            acl=[]):
        """Retract fact
Args:
    organization (str): Set owner of new Fact. If not set the current user's
                        organization will be used (takes Organization UUID)
    source (str):       Set Source of new Fact. If not set the current user
                        will be used as Source (takes Source UUID)
    access_mode:        Set access mode of new Fact. If not set the accessMode
                        from the retracted Fact will be used = ['Public',
                        'RoleBased', 'Explicit']
    comment (str):      If set adds a comment to new Fact
    acl (str[] | str):  If set defines explicitly who has access to new Fact (takes Subject UUIDs)

All arguments are optional.

Returns retracted fact.
    """

        params = act.utils.prepare_params(locals(), ensure_list=["acl"])

        if self.id:
            url = "v1/fact/uuid/{}/retract".format(self.id)
        else:
            raise MissingField(
                "Must have object ID to retract object")

        fact = self.api_post(url, **params)["data"]

        self.data = {}
        self.deserialize(**fact)

        return self
