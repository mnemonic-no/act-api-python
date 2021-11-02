import pytest

from act.api.base import ActBase, Comment, NameSpace, Organization, Origin


class Child(ActBase):
    pass


def test_equailty():

    with pytest.raises(NotImplementedError):
        assert Child() == Child()

    ns_mnemonic = NameSpace("mnemonic")
    ns_google = NameSpace("google")
    org_mnemonic = Organization("mnemonic")
    org_google = Organization("google")
    origin_mnemonic = Origin(
        "mnemonic", namespace=ns_mnemonic, organization=org_mnemonic
    )
    origin_google = Origin("google", namespace=ns_google, organization=org_google)

    assert ns_mnemonic == NameSpace("mnemonic", "dummy-id")
    assert ns_mnemonic != ns_google
    assert org_mnemonic == Organization("mnemonic", "dummy-id")
    assert org_mnemonic != org_google

    assert origin_mnemonic == Origin(
        "mnemonic", "dummy-id", namespace=ns_mnemonic, organization=org_mnemonic
    )

    assert origin_mnemonic != origin_google

    assert Comment("a") == Comment("a")
