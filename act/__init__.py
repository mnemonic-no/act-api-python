import uuid

# This is a static uuid used as seed for generating reproducible uuids based on
# text This is a temporary solution until we can get sources (uuids) from the
# ACT backend
ACT_UUID_NAMESPACE = uuid.UUID('6b159598-b585-11e7-a8e7-e83935122d71')
FACT_IS_SOURCE = "FactIsSource"
FACT_IS_DESTINATION = "FactIsDestination"
BIDIRECTIONAL_FACT = "BiDirectional"
DEFAULT_VALIDATOR = r'(.|\n)*'

RE_UUID_MATCH = r'^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$'
RE_UUID = r'(?P<uuid>[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})'
RE_TIMESTAMP_MATCH = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z$'
RE_TIMESTAMP = r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z)'

from act import utils
from act import schema
from act import base
from act import obj
from act import fact
from act import helpers

from .helpers import Act
