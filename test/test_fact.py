import re
import responses
import act
from act import RE_UUID_MATCH, RE_TIMESTAMP_MATCH, RE_UUID, RE_TIMESTAMP
from act.fact import Fact
from act.obj import Object
from act_test import get_mock_data

# pylint: disable=no-member


@responses.activate
def test_add_fact():
    mock = get_mock_data("data/post_v1_fact_127.0.0.1_201.json")
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
    assert f.source_object is not None
    assert f.destination_object is not None
    assert f.bidirectional_binding is not None

    # Add fact
    f.add()

    fact_repr = repr(f)
    repr_f = eval(fact_repr)

    assert f == repr_f
    assert f.value == repr_f.value
    assert f.type.name == repr_f.type.name
    assert f.source_object == repr_f.source_object
    assert f.source_object.value == repr_f.source_object.value
    assert f.destination_object.type == repr_f.destination_object.type
    assert f.destination_object.value == repr_f.destination_object.value

    assert str(f) == str(repr_f)

    assert str(f) == \
        "(ipv4/127.0.0.1) -[seenIn/report]-> (report/87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7)"

    # id, timestamp and organization should now be fetched from API
    assert re.search(RE_UUID_MATCH, f.id)
    assert re.search(RE_TIMESTAMP_MATCH, f.timestamp)
    assert re.search(RE_UUID_MATCH, f.organization.id)
    # Not implemented/stable in backend API yet
    # self.assertRegex(f.origin.id, RE_UUID_MATCH)

@responses.activate
def test_add_meta_fact():
    mock = get_mock_data("data/post_v1_fact_uuid_meta_201.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.Act("http://localhost:8080", 1)

    uuid = re.search(RE_UUID, mock["url"]).group("uuid")

    f = c.fact(id=uuid)

    value = mock["params"]["json"]["value"]

    meta = f.meta("observationTime", value).add()

    assert meta.type.name == "observationTime"
    assert meta.value == value



@responses.activate
def test_create_fact_type():
    mock = get_mock_data("data/post_v1_factType_threatActorAlias_201.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    mock_data = mock["json"]["data"]
    threat_actor_id = mock_data["relevantObjectBindings"][0][
        "destinationObjectType"]["id"]

    c = act.Act("http://localhost:8080", 1)
    fact_type = c.fact_type(
        name="threatActorAlias",
        validator=".+",
        relevant_object_bindings=[
            act.fact.RelevantObjectBindings(
                act.obj.Object(id=threat_actor_id),
                act.obj.Object(id=threat_actor_id),
                True)]).add()

    assert fact_type.name == "threatActorAlias"
    assert re.search(RE_UUID_MATCH, fact_type.id)


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
        limit=1)

    assert not facts.complete
    assert facts.size == 1
    assert facts.count > 1

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
