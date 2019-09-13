import re
import responses
import pytest
import act
from act.api import RE_UUID_MATCH, RE_UUID
from act_test import get_mock_data


# pylint: disable=no-member
@responses.activate
def test_get_origins():
    mock = get_mock_data("data/get_v1_origin_200.json")
    responses.add(
        responses.GET,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8888", 1)

    origins = c.get_origins()

    # We should have a ipv4 object type
    assert "my-origin" in [origin.name for origin in origins]

    # All origins should have a valid uuid
    assert all([re.search(RE_UUID_MATCH, origin.id)
                for origin in origins])

# @responses.activate
# def test_create_origin():
#     mock = get_mock_data("data/post_v1_origin_myorigin_201.json")
#     responses.add(
#         responses.POST,
#         mock["url"],
#         json=mock["json"],
#         status=mock["status_code"])
#
#     c = act.api.Act("http://localhost:8888", 1)
#
#     o = c.origin("my-origin", trust=0.8, description="My origin")
#     origin = o.add()
#
#     assert origin.name == "threatActor"
#     assert re.search(RE_UUID_MATCH, origin.id)