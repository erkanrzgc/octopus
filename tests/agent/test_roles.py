"""Rol = katalog domain'i; asistan cross-cutting (routable degil); general = tam katalog."""
from agent.catalog import CATALOG
from agent.roles import ROLES, ASISTAN, GENERAL, role_tools
import pytest


def test_asistan_not_routable():
    assert ASISTAN == "asistan"
    assert ASISTAN not in ROLES


def test_general_returns_full_catalog():
    assert role_tools(GENERAL) == frozenset(CATALOG)


def test_asistan_tools_in_every_role():
    asistan = {n for n, s in CATALOG.items() if s.domain == "asistan"}
    for r in ROLES:
        assert asistan <= role_tools(r), f"asistan not in {r}"


def test_role_slice_is_domain_plus_asistan():
    web = {n for n, s in CATALOG.items() if s.domain == "web"}
    asistan = {n for n, s in CATALOG.items() if s.domain == "asistan"}
    assert role_tools("web") == frozenset(web | asistan)


def test_union_of_roles_covers_catalog():
    union: set[str] = set()
    for r in ROLES:
        union |= role_tools(r)
    assert union == set(CATALOG)


def test_unknown_role_raises():
    with pytest.raises(ValueError):
        role_tools("nope")
