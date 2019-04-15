""" Test for act helpers """

import act


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
    assert api.fact("componentOf").source("ipv6", "2001:67c:21e0::16").destination("uri", uri) \
        in facts


def test_add_uri_ipv6_with_port_path_query() -> None:  # type: ignore
    """ Test for extraction of facts from uri with ipv6, path and query """
    api = act.api.Act("", None, "error")

    uri = "http://[2001:67c:21e0::16]:8080/path?q=a"

    facts = act.api.helpers.uri_facts(api, uri)

    assert len(facts) == 6
    assert api.fact("scheme", "http").source("uri", uri) in facts
    assert api.fact("componentOf").source("ipv6", "2001:67c:21e0::16").destination("uri", uri) \
        in facts
    assert api.fact("port", "8080").source("uri", uri) in facts
    assert api.fact("componentOf").source("path", "/path").destination("uri", uri) in facts
    assert api.fact("basename", "path").source("path", "/path") in facts
    assert api.fact("componentOf").source("query", "q=a").destination("uri", uri) in facts
