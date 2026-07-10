from data.sft.tools.build_tools import target_audit


def _row(hedef):
    return {"messages": [
        {"role": "system", "content": "s"},
        {"role": "user", "content": f"{hedef} tara"},
        {"role": "assistant", "content": f"```arac\n{{\"arac\":\"nmap\",\"parametreler\":{{\"hedef\":\"{hedef}\"}}}}\n```"},
    ]}


def test_audit_flags_over_concentration():
    rows = [_row("10.10.10.5") for _ in range(90)] + [_row(f"10.0.0.{i}") for i in range(10)]
    ok, report = target_audit(rows)
    assert ok is False
    assert "10.10.10.5" in report


def test_audit_passes_balanced_with_hostnames():
    rows = [_row(f"10.{i}.{i}.{i}") for i in range(1, 40)]
    rows += [_row(h) for h in ("web01.lab.local", "dc01.corp.local", "api-gw.internal",
                               "portal.kurum.local", "fileserver.internal",
                               "app-staging.internal", "octopus-target", "mail.corp.local",
                               "gitlab.lab.local", "vpn-gw.corp.local", "ad01.corp.local")]
    ok, report = target_audit(rows)
    assert ok is True
