""" Test for act helpers """

import pytest
import act.api


def test_add_uri_fqdn() -> None:  # type: ignore
    """ Test for extraction of facts from uri with fqdn """
    api = act.api.Act("", None, "error")

    uri = "http://www.mnemonic.no/home"

    facts = act.api.helpers.uri_facts(api, uri)

    assert len(facts) == 4
    assert api.fact("componentOf").source("fqdn", "www.mnemonic.no").destination("uri", uri) \
        in facts
    assert api.fact("componentOf").source("path", "/home").destination("uri", uri) in facts
    assert api.fact("scheme", "http").source("uri", uri) in facts
    assert api.fact("basename", "home").source("path", "/home") in facts


def test_uri_should_fail() -> None:  # type: ignore
    """ Test for extraction of facts from uri with ipv4 """
    api = act.api.Act("", None, "error")

    with pytest.raises(act.api.base.ValidationError):
        act.api.helpers.uri_facts(api, "http://")

    with pytest.raises(act.api.base.ValidationError):
        act.api.helpers.uri_facts(api, "www.mnemonic.no")

    with pytest.raises(act.api.base.ValidationError):
        act.api.helpers.uri_facts(api, "127.0.0.1")

    with pytest.raises(act.api.base.ValidationError):
        act.api.helpers.uri_facts(api, "http://localhost:test")


def test_add_uri_ipv4() -> None:  # type: ignore
    """ Test for extraction of facts from uri with ipv4 """
    api = act.api.Act("", None, "error")

    uri = "http://127.0.0.1:8080/home"

    facts = act.api.helpers.uri_facts(api, uri)

    assert len(facts) == 5
    assert api.fact("componentOf").source("ipv4", "127.0.0.1").destination("uri", uri) in facts
    assert api.fact("componentOf").source("path", "/home").destination("uri", uri) in facts
    assert api.fact("scheme", "http").source("uri", uri) in facts
    assert api.fact("basename", "home").source("path", "/home") in facts
    assert api.fact("port", "8080").source("uri", uri) in facts


def test_add_uri_ipv6() -> None:  # type: ignore
    """ Test for extraction of facts from uri with ipv4 """
    api = act.api.Act("", None, "error")

    uri = "http://[2001:67c:21e0::16]"

    facts = act.api.helpers.uri_facts(api, uri)

    assert len(facts) == 2
    assert api.fact("scheme", "http").source("uri", uri) in facts
    assert api.fact("componentOf").source("ipv6", "2001:067c:21e0:0000:0000:0000:0000:0016").destination("uri", uri) \
        in facts


def test_add_uri_ipv6_with_port_path_query() -> None:  # type: ignore
    """ Test for extraction of facts from uri with ipv6, path and query """
    api = act.api.Act("", None, "error")

    uri = "http://[2001:67c:21e0::16]:8080/path?q=a"

    facts = act.api.helpers.uri_facts(api, uri)

    assert len(facts) == 6
    assert api.fact("scheme", "http").source("uri", uri) in facts
    assert api.fact("componentOf").source("ipv6", "2001:067c:21e0:0000:0000:0000:0000:0016").destination("uri", uri) \
        in facts
    assert api.fact("port", "8080").source("uri", uri) in facts
    assert api.fact("componentOf").source("path", "/path").destination("uri", uri) in facts
    assert api.fact("basename", "path").source("path", "/path") in facts
    assert api.fact("componentOf").source("query", "q=a").destination("uri", uri) in facts


def test_ip_obj() -> None:
    """ Test ip handling """

    api = act.api.Act("", None, "error")

    assert act.api.helpers.ip_obj("2001:67c:21e0::16") == ("ipv6", "2001:067c:21e0:0000:0000:0000:0000:0016")
    assert act.api.helpers.ip_obj("::1") == ("ipv6", "0000:0000:0000:0000:0000:0000:0000:0001")
    assert act.api.helpers.ip_obj("127.0.0.1") == ("ipv4", "127.0.0.1")

    assert act.api.helpers.ip_obj("127.000.00.01") == ("ipv4", "127.0.0.1")

    with pytest.raises(ValueError):
        assert act.api.helpers.ip_obj("x.y.z") == ("ipv4", "x.y.x")

    with pytest.raises(ValueError):
        assert act.api.helpers.ip_obj("300.300.300.300") == ("ipv4", "x.y.x")

    assert api.fact("resolvesTo") \
            .source("fqdn", "localhost") \
            .destination("ipv4", "127.0.0.1") \
        == api.fact("resolvesTo") \
            .source("fqdn", "localhost") \
            .destination(*act.api.helpers.ip_obj("127.0.0.1"))
