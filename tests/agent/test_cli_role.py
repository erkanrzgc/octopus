"""CLI --rol: rol verilince demo registry rol-scoped (containment); yoksa tam katalog (bugunku)."""
from agent.cli import _demo_registry
from agent.executor import MockExecutor
from agent.roles import role_tools


def test_demo_registry_unscoped_by_default():
    reg = _demo_registry(["10.0.0.0/24"], MockExecutor(), None)
    assert reg.allowed is None                       # rol yok -> tam katalog (bugunku davranis)


def test_demo_registry_scoped_when_role_given():
    reg = _demo_registry([], MockExecutor(), "recon-scan")
    assert reg.allowed == role_tools("recon-scan")   # rol -> yapisal containment
