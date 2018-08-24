import re
import responses
import act
from act import RE_UUID_MATCH, RE_TIMESTAMP_MATCH, RE_UUID, RE_TIMESTAMP
from act_test import get_mock_data

# pylint: disable=no-member

@responses.activate
def test_add_fact():
    mock = get_mock_data("data/post_v1_fact_201.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.Act("http://localhost:8080", 1)

    f = c.fact("seenIn", "report") \
        .source("ipv4", "127.0.0.1") \
        .destination("report", "xyz")

    assert f.type.name == "seenIn"
    assert f.value == "report"

    # We do not have id or timestamp yet
    assert f.id is None
    assert f.timestamp is None
    assert len(f.objects) == 2

    # Add fact
    f.add()

    # id, timestamp and organization should now be fetched from API
    assert re.search(RE_UUID_MATCH, f.id)
    assert re.search(RE_TIMESTAMP_MATCH, f.timestamp)
    assert re.search(RE_UUID_MATCH, f.organization.id)
    # Not implemented/stable in backend API yet
    # self.assertRegex(f.origin.id, RE_UUID_MATCH)
    assert len(f.objects) == 2


@responses.activate
def test_get_fact_types():
    mock = get_mock_data("data/get_v1_factType_200.json")
    responses.add(
        responses.GET,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.Act("http://localhost:8080", 1)
    fact_types = c.get_fact_types()

    assert fact_types.size == len(fact_types)


@responses.activate
def test_fact_search():
    mock = get_mock_data("data/post_v1_fact_search_200.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.Act("http://localhost:8080", 1)

    facts = c.fact_search(
        fact_type=["seenIn"],
        fact_value=["report"],
        limit=25)

    assert not facts.complete
    assert facts.size == 25
    assert facts.count > 1000

    # All facts should have an UUID
    assert all([re.search(RE_UUID_MATCH, fact.id) for fact in facts])


@responses.activate
def test_fact_acl():
    mock = get_mock_data("data/get_v1_fact_uuid_access_200.json")
    responses.add(
        responses.GET,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.Act("http://localhost:8080", 1)
    uuid = re.search(RE_UUID, mock["url"]).group("uuid")
    acl = c.fact(id=uuid).get_acl()
    assert acl == []


@responses.activate
def test_fact_get_comments():
    mock = get_mock_data("data/get_v1_fact_uuid_comments_200.json")
    responses.add(
        responses.GET,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.Act("http://localhost:8080", 1)

    # Get comments
    uuid = re.search(RE_UUID, mock["url"]).group("uuid")
    comments = c.fact(id=uuid).get_comments()
    assert comments  # Should be non empty
    assert comments[0].comment == "Test comment"
    assert re.search(RE_TIMESTAMP, comments[0].timestamp)
    assert all([isinstance(comment, act.base.Comment) for comment in comments])


@responses.activate
def test_fact_add_comment():
    mock = get_mock_data("data/post_v1_fact_uuid_comments_201.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.Act("http://localhost:8080", 1)

    # Get comments
    uuid = re.search(RE_UUID, mock["url"]).group("uuid")

    c.fact(id=uuid).add_comment("Test comment")
