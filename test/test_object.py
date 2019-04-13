import re
import responses
import pytest
import act
from act.api import RE_UUID_MATCH, RE_UUID
from act_test import get_mock_data


# pylint: disable=no-member
@responses.activate
def test_get_object_types():
    mock = get_mock_data("data/get_v1_objectType_200.json")
    responses.add(
        responses.GET,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8080", 1)
    object_types = c.get_object_types()

    # We should have a ipv4 object type
    assert "ipv4" in [object_t.name for object_t in object_types]

    # All object types should have a valid uuid
    assert all([re.search(RE_UUID_MATCH, object_t.id)
                for object_t in object_types])

@responses.activate
def test_create_object_type():
    mock = get_mock_data("data/post_v1_objectType_threatActor_201.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8080", 1)
    object_type = c.object_type(
        name="threatActor",
        validator=".+").add()

    assert object_type.name == "threatActor"
    assert re.search(RE_UUID_MATCH, object_type.id)


@responses.activate
def test_get_object_by_uuid():
    mock = get_mock_data("data/post_v1_object_uuid_facts_200.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    uuid = re.search(RE_UUID, mock["url"]).group("uuid")

    c = act.api.Act("http://localhost:8080", 1)

    obj = c.object(id=uuid)

    facts = obj.facts()

    assert all([re.search(RE_UUID_MATCH, fact.id) for fact in facts])


@responses.activate
def test_get_object_by_type_value():
    mock = get_mock_data("data/post_v1_object_facts_200.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8080", 1)

    obj = c.object(type="ipv4", value="127.0.0.1")

    facts = obj.facts()

    assert facts.complete
    assert len(facts) == facts.size

    # We should have at least one fact
    assert len(facts) >= 1

    # All facts should be of type Fact
    assert all([isinstance(fact, act.api.fact.Fact) for fact in facts])

    # All facts should have an UUID
    assert all([re.search(RE_UUID_MATCH, fact.id) for fact in facts])


@responses.activate
def test_object_search():
    mock = get_mock_data("data/post_v1_object_search_200.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8080", 1)

    objects = c.object_search(
        fact_type=["seenIn"],
        fact_value=["report"],
        limit=1)

    assert not objects.complete
    assert objects.size == 1
    assert objects.count > 1

    obj = objects[0]

    # Objects should not have "object_type", since that property is stored in
    # "type"
    with pytest.raises(AttributeError):
        # pylint: disable=pointless-statement
        obj.object_type

    # Objects should not have "object_value", since that property is stored in
    # "value"
    with pytest.raises(AttributeError):
        # pylint: disable=pointless-statement
        obj.object_value

    # All facts should have an UUID
    assert all([re.search(RE_UUID_MATCH, obj.id) for obj in objects])


@responses.activate
def test_get_object_search():
    mock = get_mock_data("data/post_v1_object_traverse_200.json")
    responses.add(
        responses.POST,
        mock["url"],
        json=mock["json"],
        status=mock["status_code"])

    c = act.api.Act("http://localhost:8080", 1)

    obj = c.object(type="ipv4", value="127.0.0.1")

    path = obj.traverse('g.bothE("seenIn").bothV().path().unfold()')

    # Should contain both objects and facts
    assert any([isinstance(elem, act.api.obj.Object) for elem in path])
    assert any([isinstance(elem, act.api.fact.Fact) for elem in path])
