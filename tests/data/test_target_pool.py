import random
from ipaddress import IPv4Address, IPv4Network

from data.sft.tools import target_pool as tp


def test_sample_host_falls_inside_given_subnet():
    rng = random.Random(1)
    net = IPv4Network("192.168.7.0/24")
    for _ in range(200):
        host = tp.sample_host(rng, net)
        assert host in net.hosts()


def test_sample_subnet_is_private_or_doc():
    rng = random.Random(2)
    allowed = tp.PRIVATE_RANGES + (tp.DOC_RANGE,)
    for _ in range(200):
        sub = tp.sample_subnet(rng, prefix=24)
        assert any(sub.subnet_of(r) or sub == r for r in allowed)


def test_use_hostname_share_is_roughly_calibrated():
    rng = random.Random(3)
    hits = sum(tp.use_hostname(rng, share=0.28) for _ in range(5000))
    assert 0.24 < hits / 5000 < 0.32


def test_determinism_same_seed_same_draw():
    a = [str(tp.sample_host(random.Random(9))) for _ in range(5)]
    b = [str(tp.sample_host(random.Random(9))) for _ in range(5)]
    assert a == b


def test_public_domain_classification_keeps_osint_semantics():
    # OSINT hedefi (public) -> public; lab host (.local/.internal/bare) -> lab
    assert tp.is_public_domain("orneksirket.com") is True
    assert tp.is_public_domain("portal.kurum.com") is True
    assert tp.is_public_domain("ornek-firma.com.tr") is True
    assert tp.is_public_domain("web01.lab.local") is False
    assert tp.is_public_domain("api-gw.internal") is False
    assert tp.is_public_domain("octopus-target") is False
    assert tp.sample_public_domain(random.Random(7)) in tp.PUBLIC_DOMAINS
