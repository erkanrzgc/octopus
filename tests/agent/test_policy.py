from agent.policy import LabPolicy, Decision
from agent.catalog import ToolSpec

low = ToolSpec("nmap", "recon-scan", "low", ("hedef", "secenekler"))
high = ToolSpec("msfvenom", "exploit-ad", "high", ("secenekler",))


def test_low_risk_in_scope_allowed():
    p = LabPolicy(scope=["10.10.10.0/24"])
    d = p.decide(low, {"hedef": "10.10.10.5"})
    assert d.allowed and not d.requires_approval


def test_out_of_scope_denied():
    p = LabPolicy(scope=["10.10.10.0/24"])
    d = p.decide(low, {"hedef": "8.8.8.8"})
    assert not d.allowed and "kapsam" in d.reason.lower()


def test_high_risk_requires_approval():
    p = LabPolicy(scope=["10.10.10.0/24"], allow_high=False)
    d = p.decide(high, {})
    assert not d.allowed and d.requires_approval


def test_no_scope_means_lab_only_deny_targeted():
    p = LabPolicy.default()  # bos kapsam = hicbir dis hedef
    d = p.decide(low, {"hedef": "10.10.10.5"})
    assert not d.allowed


def test_target_tool_without_target_fail_closed():
    # GUVENLIK: hedef-alan arac (nmap) hedef vermeden cagirilirsa scope atlanamaz -> REDDET.
    p = LabPolicy(scope=["10.10.10.0/24"])
    d = p.decide(low, {"secenekler": "-sV"})  # 'hedef' YOK
    assert not d.allowed and "hedef" in d.reason.lower()


def test_targetless_tool_still_evaluated_by_risk():
    # Hedef-almayan arac (msfvenom, sadece secenekler) fail-closed'a takilmaz; risk kapisina gider.
    p = LabPolicy(scope=["10.10.10.0/24"])
    d = p.decide(high, {"secenekler": "-p x"})
    assert not d.allowed and d.requires_approval  # eksik-hedef degil, yuksek-risk onayi
