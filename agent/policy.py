"""Lab-only yetki + risk kapisi. Varsayilan: dis hedef yok, high-risk onay ister.
Hedef IP/CIDR kapsam allow-list'iyle karsilastirilir; kapsam disi -> reddet (modelin
kendi reddiyle cift kilit)."""
from __future__ import annotations
from dataclasses import dataclass, field
import ipaddress
from agent.catalog import ToolSpec

# Hedef tasiyan parametre anahtarlari (egitim verisinden).
_TARGET_KEYS = ("hedef", "url", "hedef_url", "domain")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    requires_approval: bool
    reason: str


@dataclass
class LabPolicy:
    scope: list[str] = field(default_factory=list)  # izinli IP/CIDR (bos = dis hedef yok)
    allow_high: bool = False

    @classmethod
    def default(cls) -> "LabPolicy":
        return cls(scope=[], allow_high=False)

    def _target(self, params: dict) -> str | None:
        for k in _TARGET_KEYS:
            if k in params and params[k]:
                return str(params[k])
        return None

    def _in_scope(self, target: str) -> bool:
        # IP/CIDR ise kapsamla karsilastir; degilse (domain vs) kapsam bos degilse ret.
        for cidr in self.scope:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                host = target.split(":")[0].split("/")[0]
                if ipaddress.ip_address(host) in net:
                    return True
            except ValueError:
                if target == cidr:
                    return True
        return False

    def decide(self, spec: ToolSpec, params: dict) -> Decision:
        target = self._target(params)
        if target is not None and not self._in_scope(target):
            return Decision(False, False, f"hedef '{target}' izinli kapsam disinda (lab-only)")
        if spec.risk == "high" and not self.allow_high:
            return Decision(False, True, f"'{spec.name}' yuksek riskli, acik onay gerekir")
        return Decision(True, False, "izinli")
