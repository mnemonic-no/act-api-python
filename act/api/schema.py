import copy
import json
from .utils import snake_to_camel, camel_to_snake
from logging import info, warning

def default_deserializer(value):
    """Default serializer. return trimmed value"""

    if isinstance(value, str):
        trimmed = value.strip()

        if trimmed != value:
            info('Value was trimmed: "{}"'.format(value))
            value = trimmed

    return value


class ValidationError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class MissingField(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


# pylint: disable=useless-object-inheritance
class Field(object):
    """Schema fields"""

    def __init__(
            self,
            name,
            default=None,
            serializer=None,
            deserializer=default_deserializer,
            serialize_target=None,
            deserialize_target=None,
            flatten=False):
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
    flatten (bool):            Flatten data structure
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
            # pylint: disable=comparison-with-callable
            if self.deserializer == default_deserializer:
                raise ValidationError(
                    "dict is not supported by default serializer. field={}, value={}".format(
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


# pylint: disable=useless-object-inheritance
class Schema(object):
    """Define schema and serialize/deserialize response from the platform"""

    def __init__(self, *args, **kwargs):
        """Initialize (deserialize) fields"""

        self.data = {}

        # Apply all positinal arguments based on order in SCHEMA
        for i, v in enumerate(args):
            kwargs[self.SCHEMA[i].name] = v

        self.deserialize(**kwargs)

    def json(self, exclude_none=True, to_camel_case=True):
        return json.dumps(
            self.serialize(
                exclude_none=exclude_none,
                to_camel_case=to_camel_case))

    def serialize(self, exclude_none=True, to_camel_case=True):
        entries = {}
        for field in self.SCHEMA:
            serialize_target = field.serialize_target or field.name

            if to_camel_case:
                serialize_target = snake_to_camel(serialize_target)

            # Entry is stored in another field internally
            value = self.data.get(field.name, None)

            # Exclude empty values
            if exclude_none and value is None:
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
                warning('"{}" not defined in schema on {}'.format(k, self.__class__))
                continue

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

    def __getitem__(self, key):
        return self.data[key]

    def __getattr__(self, attr):
        """
        Get attribute from schema
        """
        if attr in self.__dict__.get("data", {}):
            return self.__dict__["data"][attr]

        raise AttributeError(
            # pylint: disable=too-many-format-args
            "{} object has no attribute {}".format(
                self.__class__, attr))

    def __setattr__(self, attr, value):
        """
        Set schema attribute
        """

        # If attribute is in schema, update schema
        if attr in self.__dict__.get("data", {}):
            self.__dict__["data"][attr] = value
        else:  # If not, set attribute on object directly
            self.__dict__[attr] = value

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False # Different types -> not equal

        for field, value in self.data.items():
            if other.data.get(field) != value:
                return False # Different field value

        # All field values are equal
        return True

    def __ne__(self, other):
        """
        Test for not equal and use the inverse of __eq__.
        This is only needed in python2, not python3.
        """
        return not self.__eq__(other)

    def __repr__(self):
        """
        Construnct repr string based on Schema values and optionally
        the serializer field atttribute
        """

        args = []

        for field in self.SCHEMA:
            if field.serializer is False:
                continue

            if self.data.get(field.name) == field.default:
                continue # Exclude default values

            value = self[field.name]

            if field.serializer:
                value = field.serializer(value)

            args.append('{}={!r}'.format(field.name, value))

        return "{}({})".format(self.__class__.__name__, ", ".join(args))
