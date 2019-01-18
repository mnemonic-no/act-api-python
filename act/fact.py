import json
import re
import time
from logging import info, warning

import act
from act import RE_UUID_MATCH

from .base import ActBase, Comment, NameSpace, Organization
from .obj import Object, ObjectType
from .schema import Field, MissingField, ValidationError, schema_doc


class RelevantObjectBindings(ActBase):
    SCHEMA = [
        Field(
            "source_object_type",
            deserializer=ObjectType,
            serializer=lambda source_object_type: source_object_type.id),
        Field(
            "destination_object_type",
            deserializer=ObjectType,
            serializer=lambda destination_object_type: destination_object_type.id),
        Field(
            "bidirectional_binding",
            default=False)]

    def __hash__(self):
        """
        Hash of the object binding is the combination of
        source/destination object and bidirectional
        """

        if self.source_object_type:
            source = self.source_object_type.id
        else:
            source = None

        if self.destination_object_type:
            destination = self.destination_object_type.id
        else:
            destination = None

        return hash((source, destination, self.bidirectional_binding))

    def __eq__(self, other):
        "Equality operator"

        return hash(self) == hash(other)


class RelevantFactBindings(ActBase):
    """Meta Fact Type"""
    SCHEMA = [
        Field("name"),
        Field("id"),
        Field("fact_type", flatten=True),
    ]

    def __hash__(self):
        "Hash of the fact bindings is the ID itself"

        return hash(self.id)

    def __eq__(self, other):
        "Equality operator"

        return hash(self) == hash(other)

    def serialize(self):
        # Return None for empty objects (non initialized objects)
        if not self.id:
            return None

        return {"factType": self.id}

    def __bool__(self):
        # Return None for empty objects (non initialized objects)
        if not self.id:
            return False

        return True


class FactType(ActBase):
    """Manage FactType"""
    SCHEMA = [
        Field("name"),
        Field("id"),
        Field("validator", default="RegexValidator"),
        Field("validator_parameter", default=act.DEFAULT_VALIDATOR),
        Field("relevant_object_bindings", deserializer=RelevantObjectBindings),
        Field("relevant_fact_bindings", deserializer=RelevantFactBindings),
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

    def add_object_binding(
            self,
            source_object_type,
            destination_object_type,
            bidirectional_binding=False):
        """Add bindings
Args:
    source_object_type (objectType):        Source Object Type
    destination_object_type (objectType):   Destination Object Type
    bidirectional_binding (boolean):        Whether the binding is bidirectional
"""
        return self.add_object_bindings([
            RelevantObjectBindings(
                source_object_type,
                destination_object_type,
                bidirectional_binding)])

    def add_object_bindings(self, add_bindings):
        """Add multiple object bindings
Args:
    add_bindings (relevantObjectBindings[]): List of bindings which must be a
                                             tuple of RelevantObjectBindings
"""
        if not self.id:
            raise MissingField("Must have fact type ID")

        url = "v1/factType/uuid/{}".format(self.id)

        existing_bindings = set(self.relevant_object_bindings)

        # Exclude already existing bindings
        new_bindings = [
            binding
            for binding
            in add_bindings
            if binding not in existing_bindings]

        if not new_bindings:
            warning(
                "All bindings specified for {} already exists".format(
                    self.name))
            return self

        serialized_bindings = [binding.serialize() for binding in new_bindings]

        fact_type = self.api_put(
            url, addObjectBindings=serialized_bindings)["data"]

        self.data = {}
        self.deserialize(**fact_type)

        # Emit log of created bindings
        for binding in new_bindings:
            info(
                "Added bindings to fact type {}: {} -> {} (bidirectional_binding={})".format(
                    self.name, binding.source_object_type.data.get(
                        "name", None), binding.destination_object_type.data.get(
                            "name", None), binding.bidirectional_binding))

        return self

    def add_fact_binding(self, fact_type):
        """Add bindings
Args:
    fact_type (factType):   Fact type
"""
        return self.add_fact_bindings([RelevantFactBindings(name=fact_type.name, id=fact_type.id)])

    def add_fact_bindings(self, add_bindings):
        """Add multiple fact bindings
Args:
    add_bindings (relevantFactBindings[]): List of Fact bindings
"""
        if not self.id:
            raise MissingField("Must have fact type ID")

        url = "v1/factType/uuid/{}".format(self.id)

        existing_bindings = set(self.relevant_fact_bindings)

        # Exclude already existing bindings
        new_bindings = [
            binding
            for binding
            in add_bindings
            if binding not in existing_bindings]

        if not new_bindings:
            warning("All bindings specified for {} already exists".format(self.name))
            return self

        serialized_bindings = [binding.serialize() for binding in new_bindings]

        fact_type = self.api_put(
            url, addFactBindings=serialized_bindings)["data"]

        self.data = {}
        self.deserialize(**fact_type)

        # Emit log of created bindings
        for binding in new_bindings:
            info("Added bindings to meta fact type {}: {}".format(self.name, binding.name))
        return self

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


class ReferencedFact(ActBase):
    """Retracted Fact"""

    SCHEMA = [
        Field("type", deserializer=FactType,
              serializer=lambda fact_type: fact_type.name),
        Field("value", default=""),
        Field("id")
    ]

    def __eq__(self, other):
        """ Check equality with other object """

        # If other is None, return True if id, type and value is None
        if other is None:
            if not (self.id or self.type.name or self.value):
                return True
            return False

        # Otherwise, use equality check from super class
        return super(ReferencedFact, self).__eq__(other)

    def serialize(self):
        # Return None for empty objects (non initialized objects)
        if not (self.id or self.type.name):
            return None
        # return default serializer
        return super(ReferencedFact, self).serialize()

    def __bool__(self):
        # Return None for empty objects (non initialized objects)
        if (self.type.name or self.value or self.id):
            return True
        return False


def object_serializer(obj):
    if not obj:
        return None

    if obj.id is None and obj.type.name is None and obj.value is None:
        return None

    if obj.id:
        return obj.id

    return "{}/{}".format(obj.type.name, obj.value)


class Fact(ActBase):
    """Manage facts"""

    SCHEMA = [
        Field("type", deserializer=FactType,
              serializer=lambda fact_type: fact_type.name),
        Field("value", default=""),
        Field("id", serializer=False),
        # For now, do not serialize/deserialize source
        Field("source", deserializer=False, serializer=False),
        Field("timestamp", serializer=False),
        Field("last_seen_timestamp", serializer=False),
        Field("in_reference_to", deserializer=ReferencedFact),
        Field("organization", deserializer=Organization, serializer=False),
        Field("access_mode", default="Public"),
        Field("source_object", deserializer=Object),
        Field("destination_object", deserializer=Object),
        Field("bidirectional_binding", default=False),
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
        """Add source binding. Accepts the same arguments as Object()"""

        self.data["source_object"] = Object(*args, **kwargs)

        if not self.source_object.id and not (
                self.source_object.type and self.source_object.value):
            raise MissingField(
                "Must have either object_id or object_type and object_value")

        return self

    def destination(self, *args, **kwargs):
        """Add source binding. Accepts the same arguments as Object()"""

        self.data["destination_object"] = Object(*args, **kwargs)

        if not self.destination_object.id and not (
                self.destination_object.type and self.destination_object.value):
            raise MissingField(
                "Must have either object_id or object_type and object_value")

        return self

    def bidirectional(
            self,
            source_object_type,
            source_object_value,
            destination_object_type,
            destination_object_value):
        """Add bidirectional binding."""

        self.data["source_object"] = Object(
            source_object_type,
            source_object_value)
        self.data["destination_object"] = Object(
            destination_object_type,
            destination_object_value)
        self.data["bidirectional_binding"] = True

        return self

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
        """Add (meta) fact
Add this fact to the platform.

Reutrns the newly created fact.
"""
        if self.in_reference_to:
            # This is a meta fact
            return self.__add_meta()

        # This is not a meta fact
        return self.__add_fact()

    def __add_fact(self):
        """Add fact

This is not called directly, but are called from add() if Fact is not a meta fact.
        """
        started = time.time()

        # Special serializer for source/destination objects
        self.data["source_object"] = object_serializer(self.source_object)
        self.data["destination_object"] = object_serializer(
            self.destination_object)

        params = {
            k: v
            for k, v in self.serialize().items()
            # Exclude inReferenceTo, which is added automatically for retracted facts and meta facts
            if k not in ("inReferenceTo")
        }

        fact = self.api_post("v1/fact", **params)["data"]

        # Empty data and load new result from response
        self.data = {}
        self.deserialize(**fact)

        info("Created fact in %.2fs: data=%s" % (time.time() - started, json.dumps(fact)))

        return self

    def __add_meta(self):
        """Add meta fact to platform

This is not called directly, but are called from add() if Fact is a meta fact.
"""
        started = time.time()
        if not self.in_reference_to:
            raise MissingField("Fact is not a meta fact (in_reference_to is not set)")

        if not self.in_reference_to.id:
            raise MissingField("Referenced fact must have fact ID")

        params = {
            k: v
            for k, v in self.serialize().items()
            if k not in ("inReferenceTo", "bidirectionalBinding") and v
        }

        url = "v1/fact/uuid/{}/meta".format(self.in_reference_to.id)
        meta_fact = self.api_post(url, **params)["data"]

        self.data = {}
        self.deserialize(**meta_fact)
        info("Created meta fact in %.2fs: data=%s" % (time.time() - started, json.dumps(meta_fact)))

        return self

    # pylint: disable=unused-argument,dangerous-default-value
    def meta(self, *args, **kwargs):
        """Create meta fact
Creates a new meta fact with reference to this fact.
Takes the same arguments as Fact(), except for in_reference_to.
Returns meta fact
    """

        ref = ReferencedFact(type=self.type, value=self.value, id=self.id)

        meta = Fact(*args, in_reference_to=ref, **kwargs)

        # Add config to meta fact (user/auth)
        meta.configure(self.config)

        return meta

    # pylint: disable=unused-argument,dangerous-default-value

    def get_acl(self):
        """Get acl"""

        if not self.id:
            raise MissingField("Must have fact ID to resolve ACL")

        return self.api_get("v1/fact/uuid/{}/access".format(self.id))["data"]

    def grant_access(self, subject_uuid):
        """Grant access - not implemented yet"""

        raise act.base.NotImplemented(
            "Grant access is not implemented, ignoring {}".format(subject_uuid))

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
            raise ValidationError(
                "reply_to is not a valid UUID: {}".format(reply_to))

        self.api_post(
            "v1/fact/uuid/{}/comments".format(self.id),
            comment=comment, replyTo=reply_to)

        return self

    # pylint: disable=unused-argument,dangerous-default-value
    def get_meta(
            self,
            before=None,
            after=None,
            limit=None):
        """Get meta facts
Args:
    before (timestamp):           Only return Facts added before a specific
                                  timestamp. Timestamp is on this format:
                                  2016-09-28T21:26:22Z
    after (timestamp):            Only return Facts added after a specific
                                  timestamp. Timestamp is on this format:
                                  2016-09-28T21:26:22Z
    limit (integer):              Limit the number of returned Objects
                                  (default 25, 0 means all)
    """

        params = act.utils.prepare_params(locals())

        if not self.id:
            raise MissingField("Must have fact ID to get comments")

        res = self.api_get("v1/fact/uuid/{}/meta".format(self.id), params=params)
        return act.base.ActResultSet(res, Fact)

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

    def __str__(self):
        """
        Construnct string representation on this format
        (src_obj_type/src_obj_value) -[fact_type/fact_value]-> (dest_obj_type/dest_obj_value)
        """

        out = ""

        # Include source object if set
        if self.source_object:
            out += "({}/{}) -".format(self.source_object.type.name, self.source_object.value)

        # Add fact type
        out += "[{}".format(self.type.name)

        # Add value if set
        if self.value and not self.value.startswith("-"):
            out += "/{}".format(self.value)
        out += "]"

        # Add destination object if set
        if self.destination_object:

            # Use arrow unless bidirectional
            if self.bidirectional_binding:
                out += "-"
            else:
                out += "->"

            out += " ({}/{})".format(self.destination_object.type.name,
                                     self.destination_object.value)

        return out
