import copy
import functools
import ipaddress
import itertools
import logging
import os
import sys
import traceback
import urllib.parse
from logging import error, warning
from typing import List, TextIO, Optional, Text, Tuple

import act.api

from . import DEFAULT_VALIDATOR
from .base import ActBase, Config, Origin
from .fact import Fact, FactType, RelevantFactBindings, RelevantObjectBindings
from .obj import Object, ObjectType
from .schema import schema_doc

def as_list(value):
    "Encapsulate value in list if value is not already a list/tuple"

    if not isinstance(value, (list, tuple)):
        return [value]

    return value


@functools.lru_cache(maxsize=4096)
def handle_fact(fact: Fact, output_format="json", output_filehandle: Optional[TextIO] = None) -> None:
    """
    add fact if we configured act_baseurl - if not print fact
    This function has a lru cache with size 4096, so duplicates that
    occur within this cache will be ignored.

    will use print to stdout if no file handle has been passed, otherwise
    it will write to the file handle specified
    """

    # We do not set sys.stdout as default in the function signature
    # because that breaks redirection in pytest
    # https://github.com/pytest-dev/pytest/issues/2178

    # Take copy of fact, if not it will be updated when added to the platform
    # and it will create problems when added to the cace with the lru_cache decorator

    fact_copy = copy.deepcopy(fact)

    if not output_filehandle:
        output_filehandle = sys.stdout

    if fact_copy.config.act_baseurl:  # type: ignore
        fact_copy.add()
    else:
        if output_format == "json":
            output_filehandle.write('{}\n'.format(fact_copy.json()))
        elif output_format == "str":
            output_filehandle.write('{}\n'.format(str(fact_copy)))
        else:
            raise act.api.base.ArgumentError("Illegal output_format: {}".format(output_format))


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
            requests_common_kwargs=None,
            origin_name=None,
            origin_id=None,
            access_mode="RoleBased",
            organization=None):
        super(Act, self).__init__()

        self.configure(
            Config(
                act_baseurl,
                user_id,
                requests_common_kwargs,
                origin_name,
                origin_id,
                access_mode,
                organization
                )
            )

        act.api.utils.setup_logging(log_level, log_file, log_prefix)

    # pylint: disable=unused-argument,dangerous-default-value
    def fact_search(
            self,
            keywords="",
            object_type=[],
            fact_type=[],
            object_value=[],
            fact_value=[],
            organization=[],
            origin=[],
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
    origin (str[] | str):         Only return Facts coming from a specific Origin
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

        params = act.api.utils.prepare_params(
            locals(),
            ensure_list=[
                "object_type",
                "object_value",
                "fact_type",
                "fact_value",
                "organization",
                "origin"])

        res = self.api_post("v1/fact/search", **params)

        return act.api.base.ActResultSet(res, self.fact)

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

        params = act.api.utils.prepare_params(
            locals(),
            ensure_list=[
                "object_type",
                "object_value",
                "fact_type",
                "fact_value",
                "organization",
                "source"])

        res = self.api_post("v1/object/search", **params)

        return act.api.base.ActResultSet(res, self.object)

    @schema_doc(Fact.SCHEMA)
    def fact(self, *args, **kwargs):
        """Manage facts. All arguments are passed to create a Fact
object and authentication information is passed from the
act object."""

        f = Fact(*args, **kwargs).configure(self.config)
        f.set_defaults()

        return f

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

        return act.api.base.ActResultSet(
            self.api_get("v1/factType"), self.fact_type)

    def get_object_types(self):
        """Get object types"""

        return act.api.base.ActResultSet(
            self.api_get("v1/objectType"),
            self.object_type)

    @schema_doc(ObjectType.SCHEMA)
    def origin(self, *args, **kwargs):
        """Manage origins. All arguments are passed to create an origin
object and authentication information is passed from the
act object."""

        return Origin(*args, **kwargs).configure(self.config)

    def get_origins(self, include_deleted=False, limit=25):
        """Get origins"""

        params = {
            "includeDeleted": include_deleted,
            "limit": limit
        }

        return act.api.base.ActResultSet(
            self.api_get("v1/origin", params=params), self.origin)

    def create_fact_type(
            self,
            name,
            validator=DEFAULT_VALIDATOR,
            object_bindings=None,
            default_confidence=1.0):
        """Create fact type with given source, destination and bidirectional objects
Args:
    name (str):                  Fact type name
    validator (str):             Regular expression valdiator. Default = %s
    object_bindings (dict[]):    List of object_dict bindings
    default_confidence (float):  Default confidence for fact type

Returns created fact type, or exisiting fact type if it already exists.
""" % DEFAULT_VALIDATOR

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
                        raise act.api.base.ArgumentError(
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
                raise act.api.base.ArgumentError(
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
                relevant_object_bindings=relevant_object_bindings,
                default_confidence=default_confidence).add()

        return fact_type

    def create_fact_type_all_bindings(
            self, name, validator_parameter=DEFAULT_VALIDATOR, default_confidence=1.0):
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
                relevant_object_bindings=bindings,
                default_confidence=default_confidence).add()

        return fact_type

    def create_meta_fact_type(
            self,
            name,
            fact_bindings,
            validator=DEFAULT_VALIDATOR):
        """Create meta fact type with given fact bindings
Args:
    name (str):                  Fact type name
    validator (str):             Regular expression valdiator. Default = %s
    fact_bindings ([]):          List of fact bindings (name)

Returns created fact type, or exisiting fact type if it already exists.
""" % DEFAULT_VALIDATOR

        existing_fact_types = {fact_type.name: fact_type
                               for fact_type in self.get_fact_types()}

        # Verify that all fact types exists
        for fact_type in fact_bindings:
            if fact_type not in existing_fact_types:
                raise act.api.base.ArgumentError("Fact type does not exist: {}".format(fact_type))

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

    def create_meta_fact_type_all_bindings(self, name, validator_parameter=DEFAULT_VALIDATOR):
        """Create a meta fact type that can be connected to all (non-meta) fact types
Args:
    name (str):                  Fact type name
    validator (str):             Regular expression valdiator. Default = %s

Returns created fact type, or exisiting fact type if it already exists.
""" % DEFAULT_VALIDATOR

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


def handle_uri(actapi: Act, uri: str, output_format="json", output_filehandle: Optional[TextIO] = None) -> None:
    """Add all facts (componentOf, scheme, path, basename) from an URI to the platform

Raises act.api.base.ValidationError if uri does not have scheme and address component.
Make sure to catch this exception and not create other facts to an uri that fails this
validation as it will most likely fail later when uploading the fact to the platform.
    """

    # We do not set sys.stdout as default in the function signature
    # because that breaks redirection in pytest
    # https://github.com/pytest-dev/pytest/issues/2178

    if not output_filehandle:
        output_filehandle = sys.stdout

    for fact in uri_facts(actapi, uri):
        handle_fact(fact, output_format=output_format, output_filehandle=output_filehandle)


def uri_facts(actapi: Act, uri: str) -> List[Fact]:
    """Get a list of all facts (componentOf, scheme, path, basename) from an URI

Raises act.api.base.ValidationError if uri does not have scheme and address component.
Make sure to catch this exception and not create other facts to an uri that fails this
validation as it will most likely fail later when uploading the fact to the platform.

Return: List of facts
"""
    facts = []

    try:
        my_uri = urllib.parse.urlparse(uri)

        scheme = my_uri.scheme
        path = my_uri.path
        query = my_uri.query
        addr = my_uri.hostname
        port = my_uri.port
    except ValueError as e:
        raise act.api.base.ValidationError(f"Error parsing URI: {uri}: {e}")

    if not (scheme and addr):
        raise act.api.base.ValidationError("URI requires both scheme and address part")

    try:
        # Is address an ipv4 or ipv6?
        ip = ipaddress.ip_address(addr)
        addr_type = "ipv{}".format(ip.version)
        addr = ip.exploded
    except ValueError:
        addr_type = "fqdn"

    facts.append(
        actapi.fact("componentOf")
        .source(addr_type, addr)
        .destination("uri", uri))

    if port:
        facts.append(
            actapi.fact("port", str(port))
            .source("uri", uri))

    facts.append(
        actapi.fact("scheme", scheme)
        .source("uri", uri))

    if path and not path.strip() == "/":
        facts.append(
            actapi.fact("componentOf")
            .source("path", path)
            .destination("uri", uri))

        basename = os.path.basename(path)

        if basename.strip():
            facts.append(
                actapi.fact("basename", basename)
                .source("path", path))

    if query:
        facts.append(
            actapi.fact("componentOf")
            .source("query", query)
            .destination("uri", uri))

    return facts


def ip_obj(addr: Text) -> Tuple[Text, Text]:
    """Return tuple of IP type and (expanded) IP address.

Raises ValueError if addr is not valid IPv4 or IPv6 address
"""

    try:
        # Is address an ipv4 or ipv6?
        ip = ipaddress.ip_address(addr.strip())

        if ip.version not in (4, 6):
            raise ValueError('Unknown IP version: %s' % ip.version)

        return ("ipv{}".format(ip.version), ip.exploded)
    except ValueError:
        raise ValueError('Invalid IP address: %s' % addr)
