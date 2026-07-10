import json
import random
from ipaddress import ip_address, ip_network

from data.sft.tools import augment_targets as aug

_CIDR_EXAMPLE = {"messages": [
    {"role": "system", "content": "Sen Octópus'sun."},
    {"role": "user", "content": "10.10.10.0/24 agini tara."},
    {"role": "assistant", "content": "```arac\n{\"arac\":\"rustscan\",\"parametreler\":{\"hedef\":\"10.10.10.0/24\"}}\n```"},
    {"role": "tool", "content": "10.10.10.5 -> [22,80]\n10.10.10.20 -> [443]"},
    {"role": "assistant", "content": "```arac\n{\"arac\":\"nmap\",\"parametreler\":{\"hedef\":\"10.10.10.20\"}}\n```"},
]}


# ---- Task 2: extract_entities ----

def test_extract_finds_cidr_and_hosts():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    assert "10.10.10.0/24" in ent.cidrs
    assert "10.10.10.5" in ent.hosts
    assert "10.10.10.20" in ent.hosts


def test_extract_does_not_list_cidr_network_as_bare_host():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    assert "10.10.10.0" not in ent.hosts  # CIDR agi bare-host sayilmaz


def test_extract_finds_hostname():
    ex = {"messages": [{"role": "user", "content": "web01.lab.local uzerinde nikto calistir"}]}
    ent = aug.extract_entities(ex)
    assert "web01.lab.local" in ent.hostnames


# ---- Task 3: build_mapping + apply_mapping ----

def test_mapping_keeps_hosts_inside_mapped_cidr():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    mapping = aug.build_mapping(ent, random.Random(4))
    new_cidr = mapping["10.10.10.0/24"]
    net = ip_network(new_cidr, strict=False)
    for old_host in ("10.10.10.5", "10.10.10.20"):
        assert ip_address(mapping[old_host]) in net  # takip-hedefi hala ag icinde


def test_apply_is_coherent_and_replaces_all():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    mapping = aug.build_mapping(ent, random.Random(4))
    out = aug.apply_mapping(_CIDR_EXAMPLE, mapping)
    blob = json.dumps(out, ensure_ascii=False)
    assert "10.10.10." not in blob                       # hicbir eski hedef kalmadi
    follow = json.loads(out["messages"][4]["content"].split("```arac\n")[1].split("\n```")[0])
    assert follow["parametreler"]["hedef"] in out["messages"][3]["content"]


def test_apply_does_not_mutate_source():
    before = json.dumps(_CIDR_EXAMPLE, ensure_ascii=False)
    aug.apply_mapping(_CIDR_EXAMPLE, {"10.10.10.0/24": "192.168.9.0/24"})
    assert json.dumps(_CIDR_EXAMPLE, ensure_ascii=False) == before


def test_boundary_safe_substitution():
    ex = {"messages": [{"role": "user", "content": "10.10.10.5 ve 10.10.10.50"}]}
    out = aug.apply_mapping(ex, {"10.10.10.5": "1.1.1.1"})
    assert out["messages"][0]["content"] == "1.1.1.1 ve 10.10.10.50"


# ---- Task 4: augment_example ----

def test_augment_example_returns_original_plus_k():
    variants = aug.augment_example(_CIDR_EXAMPLE, k=3, rng=random.Random(5))
    assert len(variants) == 4                     # 1 orijinal + 3 varyant
    assert variants[0] == _CIDR_EXAMPLE           # ilk = orijinal (aynen)
    blobs = {json.dumps(v, ensure_ascii=False) for v in variants}
    assert len(blobs) == 4                         # hepsi farkli


def test_augment_variants_stay_valid_arac():
    for v in aug.augment_example(_CIDR_EXAMPLE, k=3, rng=random.Random(6)):
        txt = " ".join(m["content"] for m in v["messages"] if m["role"] == "assistant")
        assert "```arac" in txt                    # arac blogu korundu
