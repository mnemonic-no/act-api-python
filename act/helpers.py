import logging
from logging import warning
import sys
import act
from .base import ActBase, Config
from .fact import Fact, FactType
from .obj import Object, ObjectType
from .schema import schema_doc


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
                                  (default 25, 0 means all)

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
            source_objects=[],
            destination_objects=[],
            bidirectional_objects=[]):
        """Created fact type with given source, destination and bidirectional objects
Args:
    name (str):                  Fact type name
    validator (str):             Regular expression valdiator. Default = %s
    source_objects (str[]):      List of source objects (by name) linked to fact
    destination_objects (str[]): List of source objects (by name) linked to fact
    bidirection_objects (str[]): List of source objects (by name) linked to fact

Returns created fact type, or exisiting fact type if it already exists.
""" % act.DEFAULT_VALIDATOR

        existing_fact_types = {fact_type.name: fact_type
                               for fact_type in self.get_fact_types()}
        object_types = {
            object_type.name: object_type.id
            for object_type in self.get_object_types()}

        if name in existing_fact_types:
            warning("Fact type %s already exists" % name)
            return existing_fact_types[name]

        for obj in bidirectional_objects + source_objects + destination_objects:
            if obj not in object_types:
                raise act.base.ArgumentError(
                    "Illegal bidiectional object type {} linked from fact type {}".format(
                        obj, name))

        bindings = []

        for object_type_name in bidirectional_objects:
            bindings.append(
                {"objectType": {"id": object_types[object_type_name]},
                 "direction": act.BIDIRECTIONAL_FACT})

        for object_type_name in source_objects:
            bindings.append(
                {"objectType": {"id": object_types[object_type_name]},
                 "direction": act.FACT_IS_DESTINATION})

        for object_type_name in destination_objects:
            bindings.append(
                {"objectType": {"id": object_types[object_type_name]},
                 "direction": act.FACT_IS_SOURCE})

        return self.fact_type(
            name=name,
            validator_parameter=validator,
            relevant_object_bindings=bindings).add()

    def create_fact_type_all_bindings(
            self, name, validator_parameter=act.DEFAULT_VALIDATOR):
        """Create a fact type that can be connected to all object types"""

        existing_fact_types = {fact_type.name: fact_type
                               for fact_type in self.get_fact_types()}

        if name in existing_fact_types:
            warning("Fact type %s already exists" % name)
            return existing_fact_types[name]

        objectBindings = []

        for direction in [
                act.FACT_IS_SOURCE,
                act.FACT_IS_DESTINATION,
                act.BIDIRECTIONAL_FACT]:
            for object_type in self.get_object_types():
                objectBindings.append({
                    "objectType": {"id": object_type.id},
                    "direction": direction
                })

        return self.fact_type(name=name,
                              validator_parameter=validator_parameter,
                              relevant_object_bindings=objectBindings).add()
