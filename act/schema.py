import copy
import json
from .utils import snake_to_camel, camel_to_snake


def default_serializer(value):
    """Default serializer. return value without modification"""
    return value


class ValidationError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class MissingField(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class Field(object):
    """Schema fields"""

    def __init__(
            self,
            name,
            default=None,
            serializer=None,
            deserializer=default_serializer,
            serialize_target=None,
            deserialize_target=None,
            flatten=None):
        """
Args:
    name (str):                Field name
    default (str):             Default value for field if not specified
    serializer (func|False):   Function used to serialize the field. Set to
                               False if field should not be serialized.
    deserializer (func|False): Function used to deserialize data. Set to
                               False if field should not be deserialized.
    serialize_target (str):    Move data to this key(name) when erializing
    deserialize_target (str):  Move data to this key(name) when deserializing
    """
        self.name = name
        self.default = default
        self.serializer = serializer
        self.deserializer = deserializer
        self.serialize_target = serialize_target
        self.deserialize_target = deserialize_target
        self.flatten = flatten

    def deserialize(self, value):
        """Deserialize field using suplied value"""

        # If value is already a Schema object, use it as is
        if isinstance(value, Schema):
            return value

        if isinstance(value, dict):
            if self.deserializer == default_serializer:
                raise ValidationError(
                    "dict is not suppored by default serializer. field={}, value={}".format(
                        self.name, value))

            return self.deserializer(**value)

        return self.deserializer(value)

    def serialize(self, value):
        """Serialize field using suplied value"""

        # Custom serializer
        if self.serializer:
            return self.serializer(value)

        # Nested serializer
        if hasattr(value, "serialize") and callable(value.serialize):
            return value.serialize()

        return value


def schema_doc(schema):
    """Dynamic create doctstring from schema fields"""
    def dec(obj):
        docstring = obj.__doc__ or ""
        dynamic = """

The following arguments can be specified by position or keyword.
    {}
""".format(str("\n    ".join([field.name for field in schema])))

        obj.__doc__ = docstring + dynamic

        return obj
    return dec


class Schema(object):
    """Define schema and serialize/deserialize response from the platform"""

    def __init__(self, *args, **kwargs):
        """Initialize (deserialize) fields"""

        self.data = {}

        # Apply all positinal arguments based on order in SCHEMA
        for i, v in enumerate(args):
            kwargs[self.SCHEMA[i].name] = v

        self.deserialize(**kwargs)

    def json(self, exclude_empty=True, to_camel_case=True):
        return json.dumps(self.serialize(exclude_empty=exclude_empty, to_camel_case=to_camel_case))

    def serialize(self, exclude_empty=True, to_camel_case=True):
        entries = {}
        for field in self.SCHEMA:
            serialize_target = field.serialize_target or field.name

            if to_camel_case:
                serialize_target = snake_to_camel(serialize_target)

            # Entry is stored in another field internally
            value = self.data.get(field.name, None)

            # Exclude empty values
            if exclude_empty and not value:
                continue

            # Serializer disabled
            if field.serializer is False:
                continue

            if isinstance(value, (list, tuple)):
                entries[serialize_target] = [field.serialize(v) for v in value]
            else:
                entries[serialize_target] = field.serialize(value)

        return entries

    def get_field(self, name):
        for field in self.SCHEMA:
            if name == field.name:
                return field
        return None

    def get_deserialize_field(self, name):
        field = self.get_field(name)

        if not field:
            return None

        if field.deserialize_target:
            return self.get_field(field.deserialize_target)
        return field

    def get_serialize_field(self, name):
        field = self.get_field(name)

        if not field:
            return None

        if field.serialize_target:
            return self.get_field(field.serialize_target)

        return field

    def deserialize(self, **entries):
        for k, value in entries.items():
            k = camel_to_snake(k)
            field = self.get_deserialize_field(k)

            if not field:
                raise ValidationError(
                    '"{}" not defined in schema on {}'.format(
                        k, self.__class__))

            # deserializer disabled
            if field.deserializer is False:
                continue

            if field.flatten:
                self.deserialize(**value)
                continue

            if isinstance(value, (list, tuple)):
                self.data[field.name] = [field.deserialize(v) for v in value]
            else:
                self.data[field.name] = field.deserialize(value)

        if not hasattr(self, "SCHEMA"):
            raise ValidationError(
                "No SCHEMA defined in class {}".format(self.__class__))

        for field in self.SCHEMA:
            # Loop through all fields and set default value, unless any of
            # - field is deseriazlied with another key
            # - field is flattened
            # - deserializer is disabled
            if field.name not in self.data \
                    and not field.deserialize_target \
                    and not field.flatten \
                    and field.deserializer is not False:
                self.data[field.name] = copy.copy(field.default)

    def __getattr__(self, attr):
        if attr in self.data:
            return self.data[attr]
        else:
            raise AttributeError(
                # pylint: disable=too-many-format-args
                "{} object has no attribute {}".format(
                    self.__class__, attr))

    def __repr__(self):
        return repr(self.data)
