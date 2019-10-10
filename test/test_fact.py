import re

import pytest
import responses

import act
from act.api import RE_TIMESTAMP, RE_TIMESTAMP_MATCH, RE_UUID, RE_UUID_MATCH
from act.api.fact import Fact
from act.api.obj import Object

# Organization is required by eval of repr(fact)
from act.api.base import Organization, Origin
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

    c = act.api.Act("http://localhost:8080", 1)

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


def test_add_fact_origin():
    """ Tests for origin specified in config and directly on fact """

    default_origin_name = "test-origin"
    default_origin_id = "00000000-0000-0000-0000-000000000001"

    with pytest.raises(act.api.base.ArgumentError):
        act.api.Act("", 1, origin_id="not-valid-uuid")

    # ACT client with origin name in config
    c_origin_name = act.api.Act("", 1, origin_name=default_origin_name)

    # ACT client with origin id in config
    c_origin_id = act.api.Act("", 1, origin_id=default_origin_id)

    # ACT client with not origin in config
    c_no_origin = act.api.Act("", 1)

    # Fact using origin name from config
    fact_origin_name_from_config = c_origin_name.fact("seenIn", "report") \
        .source("ipv4", "127.0.0.1") \
        .destination("report", "xyz")

    # Using origin name specified in fact
    fact_explicit_origin_name = c_no_origin.fact(
        "seenIn", "report", origin=Origin(name=default_origin_name)) \
        .source("ipv4", "127.0.0.1") \
        .destination("report", "xyz")

    # Fact using origin id from config
    fact_origin_id_from_config = c_origin_id.fact("seenIn", "report") \
        .source("ipv4", "127.0.0.1") \
        .destination("report", "xyz")

    # Using origin id specified in fact
    fact_explicit_origin_id = c_no_origin.fact(
        "seenIn", "report", origin=Origin(id=default_origin_id)) \
        .source("ipv4", "127.0.0.1") \
        .destination("report", "xyz")

    # No origin in config or in fact definition
    fact_no_origin = c_no_origin.fact("seenIn", "report") \
        .source("ipv4", "127.0.0.1") \
        .destination("report", "xyz")

    # Facts with origin name from config and explicitly defined
    # should have the same origin
    assert fact_origin_name_from_config.origin == fact_explicit_origin_name.origin

    # Facts with origin id from config and explicitly defined
    # should have the same origin
    assert fact_origin_id_from_config.origin == fact_explicit_origin_id.origin

    assert fact_no_origin.origin is None


@responses.activate
def test_add_fact_validation_error():
    """ Test adding fact that fails on validation """
    mock = get_mock_data("data/post_v1_fact_127.0.0.x_412.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8888", 1)

    f = c.fact("mentions", "report") \
        .source("report", "xyz") \
        .destination("ipv4", "127.0.0.x")

    # Add fact -> should fail on ipv4 validation
    with pytest.raises(act.api.base.ValidationError):
        f.add()

    try:
        f.add()
    except act.api.base.ValidationError as err:
        assert(str(err) == "Object did not pass validation against ObjectType. " +
                           "(objectValue=127.0.0.x)")



@responses.activate
def test_add_meta_fact():
    mock = get_mock_data("data/post_v1_fact_uuid_meta_201.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8080", 1)

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

    c = act.api.Act("http://localhost:8080", 1)
    fact_type = c.fact_type(
        name="threatActorAlias",
        validator=".+",
        relevant_object_bindings=[
            act.api.fact.RelevantObjectBindings(
                act.api.obj.Object(id=threat_actor_id),
                act.api.obj.Object(id=threat_actor_id),
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

    c = act.api.Act("http://localhost:8080", 1)
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

    c = act.api.Act("http://localhost:8080", 1)

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

    c = act.api.Act("http://localhost:8080", 1)
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

    c = act.api.Act("http://localhost:8080", 1)

    # Get comments
    uuid = re.search(RE_UUID, mock["url"]).group("uuid")
    comments = c.fact(id=uuid).get_comments()
    assert comments  # Should be non empty
    assert comments[0].comment == "Test comment"
    assert re.search(RE_TIMESTAMP, comments[0].timestamp)
    assert all([isinstance(comment, act.api.base.Comment) for comment in comments])


@responses.activate
def test_fact_add_comment():
    mock = get_mock_data("data/post_v1_fact_uuid_comments_201.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8080", 1)

    # Get comments
    uuid = re.search(RE_UUID, mock["url"]).group("uuid")

    c.fact(id=uuid).add_comment("Test comment")


def test_fact_chain_incident_organization():
    c = act.api.Act("", 1)

    facts = (
        c.fact("observedIn").source("uri", "http://uri.no").destination("incident", "*"),
        c.fact("targets").source("incident", "*").destination("organization", "*"),
        c.fact("memberOf").source("organization", "*").destination("sector", "energy"),
    )

    for fact in facts:
        assert any([fact.source_object.value == "*", fact.destination_object.value == "*"])

    seed = act.api.fact.fact_chain_seed(*facts)

    assert seed == "(incident/*) -[targets]-> (organization/*)\n" + \
                   "(organization/*) -[memberOf]-> (sector/energy)\n" + \
                   "(uri/http://uri.no) -[observedIn]-> (incident/*)"

    # Create fact chain
    chain = act.api.fact.fact_chain(*facts)

    assert len(chain) == 3

    # There should not be any placeholders any more, since these values are replaced with
    # hashes
    for fact in chain:
        assert not any([fact.source_object.value == "*", fact.destination_object.value == "*"])


def test_fact_chain_ta_incident():
    c = act.api.Act("", 1)

    facts = (
        c.fact("observedIn").source("uri", "http://uri.no").destination("incident", "*"),
        c.fact("attributedTo").source("incident", "*").destination("threatActor", "APT99"),
    )

    # Ensure we have placeholder objects (objects with value "*")
    for fact in facts:
        assert any([fact.source_object.value == "*", fact.destination_object.value == "*"])

    incident_seed = act.api.fact.fact_chain_seed(*facts)

    assert incident_seed == "(incident/*) -[attributedTo]-> (threatActor/APT99)\n" + \
                            "(uri/http://uri.no) -[observedIn]-> (incident/*)"

    # Create fact chain
    chain = act.api.fact.fact_chain(*facts)

    assert len(chain) == 2

    # There should not be any placeholder objects in the chain
    for fact in chain:
        assert not any([fact.source_object.value == "*", fact.destination_object.value == "*"])


def test_fact_chain_incident_tool():
    """Example with multiple incoming links (which should be grouped)"""
    c = act.api.Act("", 1)

    facts = (
        c.fact("observedIn").source("uri", "http://uri.no").destination("incident", "*"),
        c.fact("observedIn").source("tool", "mimikatz").destination("incident", "*"),
    )

    for fact in facts:
        assert any([fact.source_object.value == "*", fact.destination_object.value == "*"])

    incident_seed = act.api.fact.fact_chain_seed(*facts)

    assert incident_seed == "(tool/mimikatz) -[observedIn]-> (incident/*)\n" + \
                            "(uri/http://uri.no) -[observedIn]-> (incident/*)"



def test_fact_chain_tool_ta():
    """Example with multiple incoming links (which should be grouped)"""
    c = act.api.Act("", 1)

    facts_windshield = (
        c.fact("attributedTo").source("incident", "*").destination("threatActor", "APT32"),
        c.fact("observedIn", "incident").source("content", "*").destination("incident", "*"),
        c.fact("classifiedAs").source("content", "*").destination("tool", "windshield"),
    )

    facts_mimikatz = (
        c.fact("attributedTo").source("incident", "*").destination("threatActor", "APT32"),
        c.fact("observedIn", "incident").source("content", "*").destination("incident", "*"),
        c.fact("classifiedAs").source("content", "*").destination("tool", "mimikatz"),
    )

    windshield_seed = act.api.fact.fact_chain_seed(*facts_windshield)
    mimikatz_seed = act.api.fact.fact_chain_seed(*facts_mimikatz)

    assert windshield_seed == "(content/*) -[classifiedAs]-> (tool/windshield)\n" + \
                              "(content/*) -[observedIn/incident]-> (incident/*)\n" + \
                              "(incident/*) -[attributedTo]-> (threatActor/APT32)"

    assert windshield_seed != mimikatz_seed


def test_fact_chain_illegal_tool():
    """Example with multiple incoming links (which should be grouped)"""
    c = act.api.Act("", 1)

    facts = (
        c.fact("observedIn").source("uri", "http://uri.no").destination("incident", "my-incident"),
        c.fact("observedIn").source("tool", "mimikatz").destination("incident", "*"),
    )

    # Create fact chain
    with pytest.raises(act.api.fact.IllegalFactChain):
        act.api.fact.fact_chain(*facts)
