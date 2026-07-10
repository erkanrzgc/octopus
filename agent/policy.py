"""Lab-only yetki + risk kapisi. Varsayilan: dis hedef yok, high-risk onay ister.
Hedef IP/CIDR kapsam allow-list'iyle karsilastirilir; kapsam disi -> reddet (modelin
kendi reddiyle cift kilit)."""
from __future__ import annotations
from dataclasses import dataclass, field
import ipaddress
from agent.catalog import ToolSpec, TARGET_KEYS, target_value


@dataclass(frozen=True)
class Decision:
    allowed: bool
    requires_approval: bool
    reason: str


@dataclass
class LabPolicy:
    scope: list[str] = field(default_factory=list)  # izinli IP/CIDR (bos = dis hedef yok)
    allow_high: bool = False
    workspace_root: str | None = None  # asistan dosya araclari icin hapishane koku (None = fs reddi)

    @classmethod
    def default(cls) -> "LabPolicy":
        return cls(scope=[], allow_high=False)

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
        if spec.domain == "asistan":
            return self._decide_assistant(spec, params)
        target = target_value(params)
        # FAIL-CLOSED: arac hedef-alan bir param bildiriyorsa ama cagri degerlendirilebilir
        # hedef vermediyse REDDET — yoksa hedef gizlenerek scope kilidi atlanabilir.
        spec_has_target = any(k in spec.params for k in TARGET_KEYS)
        if spec_has_target and target is None:
            return Decision(False, False, f"'{spec.name}' icin hedef parametresi eksik (fail-closed)")
        if target is not None and not self._in_scope(target):
            return Decision(False, False, f"hedef '{target}' izinli kapsam disinda (lab-only)")
        if spec.risk == "high" and not self.allow_high:
            return Decision(False, True, f"'{spec.name}' yuksek riskli, acik onay gerekir")
        return Decision(True, False, "izinli")

    def _decide_assistant(self, spec: ToolSpec, params: dict) -> Decision:
        """Asistan-domain araclarini domaine gore fs/cmd/web guard'ina yonlendir (fail-closed)."""
        from agent.guards import cmd, fs, web
        name = spec.name
        if name in ("read_file", "write_file", "edit_file", "list_dir", "grep"):
            return fs.guard(params, self.workspace_root)
        if name in ("web_fetch", "web_search"):
            return web.guard(params)
        if name == "run_cmd":
            d = cmd.guard(params)
            if not d.allowed:
                return d
            if spec.risk == "high" and not self.allow_high:
                return Decision(False, True, f"'{spec.name}' yuksek riskli, acik onay gerekir")
            return d
        return Decision(False, False, f"bilinmeyen asistan araci '{name}' (fail-closed)")
