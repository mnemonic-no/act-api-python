import itertools
import logging
import sys
from logging import warning

import act

from .base import ActBase, Config
from .fact import Fact, FactType, RelevantFactBindings, RelevantObjectBindings
from .obj import Object, ObjectType
from .schema import schema_doc


def as_list(value):
    "Encapsulate value in list if value is not already a list/tuple"

    if not isinstance(value, (list, tuple)):
        return [value]

    return value


class Act(ActBase):
    """Act class exposing most of the ACT API"""

    SCHEMA = []

    def __init__(
            self,
            act_baseurl,
            user_id,
            log_level="debug",
            log_file=None,
            log_prefix="act",
            requests_common_kwargs=None):
        super(Act, self).__init__()

        self.configure(Config(act_baseurl, user_id, requests_common_kwargs))

        self.setup_logging(log_level, log_file, log_prefix)

    def setup_logging(
            self,
            log_level="debug",
            log_file=None,
            log_prefix="act"):
        numeric_level = getattr(logging, log_level.upper(), None)

        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % log_level)

        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = "[%(asctime)s] app=" + log_prefix + \
            " level=%(levelname)s msg=%(message)s"

        if log_file:
            logging.basicConfig(
                level=numeric_level,
                filename=log_file,
                format=formatter,
                datefmt=datefmt)
        else:
            logging.basicConfig(
                level=numeric_level,
                stream=sys.stdout,
                format=formatter,
                datefmt=datefmt)

    # pylint: disable=unused-argument,dangerous-default-value
    def fact_search(
            self,
            keywords="",
            object_type=[],
            fact_type=[],
            object_value=[],
            fact_value=[],
            organization=[],
            source=[],
            include_retracted=None,
            before=None,
            after=None,
            limit=None):
        """Search objects
Args:
    keywords (str):               Only return Facts matching a keyword query
    object_type (str[] | str):    Only return Facts with objects having a specific
                                  ObjectType
    fact_type (str[] | str):      Only return Facts having a specific FactType
    object_value (str[] | str):   Only return Facts with objects matching a specific
                                  value
    fact_value (str[] | str):     Only return Facts matching a specific value
    organization (str[] | str):   Only return Facts belonging to
                                  a specific Organization
    source (str[] | str):         Only return Facts coming from a specific Source
    include_retracted (bool):     Include retracted Facts (default=False)
    before (timestamp):           Only return Facts added before a specific
                                  timestamp. Timestamp is on this format:
                                  2016-09-28T21:26:22Z
    after (timestamp):            Only return Facts added after a specific
                                  timestamp. Timestamp is on this format:
                                  2016-09-28T21:26:22Z
    limit (integer):              Limit the number of returned Objects
                                  (default 25). Limit must be <= 10000.

All arguments are optional.

Returns ActResultSet of Facts.
    """

        params = act.utils.prepare_params(
            locals(),
            ensure_list=[
                "object_type",
                "object_value",
                "fact_type",
                "fact_value",
                "organization",
                "source"])

        res = self.api_post("v1/fact/search", **params)

        return act.base.ActResultSet(res, self.fact)

    # pylint: disable=unused-argument,dangerous-default-value
    def object_search(
            self,
            keywords="",
            object_type=[],
            fact_type=[],
            object_value=[],
            fact_value=[],
            organization=[],
            source=[],
            before=None,
            after=None,
            limit=None):
        """Search objects
Args:
    keywords (str):               Only return Objects matching a keyword query
    object_type (str[] | str):    Only return Objects with a specific ObjectType
    fact_type (str[] | str):      Only return Objects with Facts having a
                                  specific FactType
    object_value (str[] | str):   Only return Objects matching a specific
                                  value
    fact_value (str[] | str):     Only return Objects with Facts matching a
                                  specific value
    organization (str[] | str):   Only return Objects with Facts belonging to
                                  a specific Organization
    source (str[] | str):         Only return Objects with Facts coming from a
                                  specific Source
    before (timestamp):           Only return Objects with Facts added before
                                  a specific timestamp. Timestamp is on
                                  this format: 2016-09-28T21:26:22Z
    after (timestamp):            Only return Objects with Facts added after a
                                  specific timestamp. Timestamp is on
                                  this format: 2016-09-28T21:26:22Z
    limit (integer):              Limit the number of returned Objects
                                  (default 25, 0 means all)

All arguments are optional.

Returns ActResultSet of Objects.
    """

        params = act.utils.prepare_params(
            locals(),
            ensure_list=[
                "object_type",
                "object_value",
                "fact_type",
                "fact_value",
                "organization",
                "source"])

        res = self.api_post("v1/object/search", **params)

        return act.base.ActResultSet(res, self.object)

    @schema_doc(Fact.SCHEMA)
    def fact(self, *args, **kwargs):
        """Manage facts. All arguments are passed to create a Fact
object and authentication information is passed from the
act object."""

        return Fact(*args, **kwargs).configure(self.config)

    @schema_doc(Object.SCHEMA)
    def object(self, *args, **kwargs):
        """Manage objects. All arguments are passed to create an Object
object and authentication information is passed from the
act object."""

        return Object(*args, **kwargs).configure(self.config)

    @schema_doc(FactType.SCHEMA)
    def fact_type(self, *args, **kwargs):
        """Manage Fact Types. All arguments are passed to create a FactType
object and authentication information is passed from the
act object."""

        return FactType(*args, **kwargs).configure(self.config)

    @schema_doc(ObjectType.SCHEMA)
    def object_type(self, *args, **kwargs):
        """Manage Object Types. All arguments are passed to create a ObjectType
object and authentication information is passed from the
act object."""

        return ObjectType(*args, **kwargs).configure(self.config)

    def get_fact_types(self):
        """Get fact types"""

        return act.base.ActResultSet(
            self.api_get("v1/factType"), self.fact_type)

    def get_object_types(self):
        """Get object types"""

        return act.base.ActResultSet(
            self.api_get("v1/objectType"),
            self.object_type)

    def create_fact_type(
            self,
            name,
            validator=act.DEFAULT_VALIDATOR,
            object_bindings=None):
        """Create fact type with given source, destination and bidirectional objects
Args:
    name (str):                  Fact type name
    validator (str):             Regular expression valdiator. Default = %s
    object_bindings (dict[]):    List of object_dict bindings

Returns created fact type, or exisiting fact type if it already exists.
""" % act.DEFAULT_VALIDATOR

        if not object_bindings:
            object_bindings = []

        existing_fact_types = {fact_type.name: fact_type
                               for fact_type in self.get_fact_types()}
        object_types = {
            object_type.name: object_type
            for object_type in self.get_object_types()}

        object_types[None] = None

        # Verify that all object types exists
        for object_binding in object_bindings:
            for object_direction in (
                "sourceObjectType",
                    "destinationObjectType"):
                for object_type in as_list(
                        object_binding.get(object_direction)):
                    if object_type and object_type not in object_types:
                        raise act.base.ArgumentError(
                            "Object does not exist: {}".format(object_type))

        relevant_object_bindings = []

        for binding in object_bindings:
            # Default -> binding is not directional
            bidirectional = binding.get("bidirectional", False)

            source_object_type = [
                object_types[object_type]
                for object_type
                in as_list(binding.get("sourceObjectType", None))]

            destination_object_type = [
                object_types[object_type]
                for object_type
                in as_list(binding.get("destinationObjectType", None))]

            if not("destinationObjectType" in binding or
                   "sourceObjectType" in binding):
                raise act.base.ArgumentError(
                    "Must specify either sourceObjectType, destinationObjectType or both in bindings for fact type {}".format(name))

            relevant_object_bindings += [
                RelevantObjectBindings(*bindings)
                for bindings
                in itertools.product(
                    *[as_list(source_object_type),
                      as_list(destination_object_type),
                      [bidirectional]])]

        if name in existing_fact_types:
            warning("Fact type %s already exists" % name)
            fact_type = existing_fact_types[name]
            fact_type.add_object_bindings(relevant_object_bindings)
        else:
            fact_type = self.fact_type(
                name=name, validator_parameter=validator,
                relevant_object_bindings=relevant_object_bindings).add()

        return fact_type

    def create_fact_type_all_bindings(
            self, name, validator_parameter=act.DEFAULT_VALIDATOR):
        """Create a fact type that can be connected to all object types"""

        existing_fact_types = {fact_type.name: fact_type
                               for fact_type in self.get_fact_types()}

        object_types = {
            object_type.name: object_type
            for object_type in self.get_object_types()}

        # Create list of all combiations of object types / bidirectional
        bindings = [
            RelevantObjectBindings(
                source_object_type,
                destination_object_type,
                bidirectional)
            for source_object_type, destination_object_type, bidirectional
            in itertools.product(*[
                object_types.values(),
                object_types.values(),
                [True, False]])]

        if name in existing_fact_types:
            # Do not create fact, but update bindings
            warning("Fact type %s already exists" % name)
            fact_type = existing_fact_types[name]
            fact_type.add_object_bindings(bindings)
        else:
            # Create fact with bindings
            fact_type = self.fact_type(
                name=name, validator_parameter=validator_parameter,
                relevant_object_bindings=bindings).add()

        return fact_type

    def create_meta_fact_type(
            self,
            name,
            fact_bindings,
            validator=act.DEFAULT_VALIDATOR):
        """Create meta fact type with given fact bindings
Args:
    name (str):                  Fact type name
    validator (str):             Regular expression valdiator. Default = %s
    fact_bindings ([]):          List of fact bindings (name)

Returns created fact type, or exisiting fact type if it already exists.
""" % act.DEFAULT_VALIDATOR

        existing_fact_types = {fact_type.name: fact_type
                               for fact_type in self.get_fact_types()}

        # Verify that all fact types exists
        for fact_type in fact_bindings:
            if fact_type not in existing_fact_types:
                raise act.base.ArgumentError("Fact type does not exist: {}".format(fact_type))

        # Create list of Fact Bindings
        relevant_fact_bindings = [
            RelevantFactBindings(name=fact_type, id=existing_fact_types[fact_type].id)
            for fact_type in fact_bindings
        ]

        if name not in existing_fact_types:
            # New meta fact type
            fact_type = self.fact_type(
                name=name, validator_parameter=validator,
                relevant_fact_bindings=relevant_fact_bindings).add()
        else:
            # Fact type already exists. Do not create, but update bindings
            warning("Fact type %s already exists" % name)
            fact_type = existing_fact_types[name]
            fact_type.add_fact_bindings(relevant_fact_bindings)

        return fact_type

    def create_meta_fact_type_all_bindings(self, name, validator_parameter=act.DEFAULT_VALIDATOR):
        """Create a meta fact type that can be connected to all (non-meta) fact types
Args:
    name (str):                  Fact type name
    validator (str):             Regular expression valdiator. Default = %s

Returns created fact type, or exisiting fact type if it already exists.
""" % act.DEFAULT_VALIDATOR

        # Get all existing fact types
        existing_fact_types = {fact_type.name: fact_type
                               for fact_type in self.get_fact_types()}

        # Create list bindings for this meta fact type
        # We exclude facts that have fact bindings (meta facts)
        bindings = [RelevantFactBindings(name=fact.name, id=fact.id)
                    for fact in existing_fact_types.values()
                    if not fact.relevant_fact_bindings]

        if name not in existing_fact_types:
            # New meta fact - create fact with bindings to all existing (non meta) fact types
            fact_type = self.fact_type(name=name,
                                       validator_parameter=validator_parameter,
                                       relevant_fact_bindings=bindings).add()

        else:
            # Fact already exists. Do not create fact, but update bindings
            warning("Meta Fact type %s already exists" % name)
            fact_type = existing_fact_types[name]

            # Add bindings
            fact_type.add_fact_bindings(bindings)
        return fact_type
