import uuid

# This is a static uuid used as seed for generating reproducible uuids based on
# text This is a temporary solution until we can get sources (uuids) from the
# ACT backend
ACT_UUID_NAMESPACE = uuid.UUID("6b159598-b585-11e7-a8e7-e83935122d71")
FACT_IS_SOURCE = "FactIsSource"
FACT_IS_DESTINATION = "FactIsDestination"
ACCESS_MODES_PUBLIC = "Public"
ACCESS_MODES_ROLEBASED = "RoleBased"
ACCESS_MODES_EXPLICIT = "Explicit"
ACCESS_MODES = [ACCESS_MODES_PUBLIC, ACCESS_MODES_ROLEBASED, ACCESS_MODES_EXPLICIT]
DEFAULT_ACCESS_MODE = ACCESS_MODES_ROLEBASED
BIDIRECTIONAL_FACT = "BiDirectional"
DEFAULT_OBJECT_VALIDATOR = r"(.|\n)*"
DEFAULT_FACT_VALIDATOR = None
DEFAULT_METAFACT_VALIDATOR = r"(.|\n)*"
ACT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

from act.api import utils
from act.api import schema
from act.api import base
from act.api import obj
from act.api import fact
from act.api import helpers

from .helpers import Act
