# Konteyner & Kubernetes Guvenligi

## Konteyner Kacisi (Container Escape)
- **Privileged konteyner** (`--privileged`): host'a neredeyse tam erisim -> kacis kolay.
- **Mounted Docker socket** (`/var/run/docker.sock`): konteyner icinden host'ta yeni (privileged) konteyner baslat -> host ele gecir.
- **Tehlikeli capability'ler**: `CAP_SYS_ADMIN`, `CAP_SYS_PTRACE`, `CAP_DAC_READ_SEARCH`.
- **Host namespace paylasimi**: `--pid=host`, `--net=host`; hassas host mount'lari (`/`, `/proc`).
- Tespit ipuclari: `/.dockerenv`, `cat /proc/1/cgroup`.

## Kubernetes
- Acik **kubelet (10250)** / API server, anonim erisim.
- Asiri yetkili **RBAC** (cluster-admin), `create pods` + hostPath -> node ele gecirme.
- Sirlar env/ConfigMap'te duz metin; **NetworkPolicy** yoklugu (yanal hareket serbest).
- `runAsRoot`, eksik **Pod Security Standards/Admission**.
- Araclar: **kube-hunter** (saldiri), **kube-bench** (CIS denetimi), Trivy (imaj tarama).

## Savunma
- Non-root calistir, read-only root FS, **tum capability'leri dusur** (gerekeni ekle).
- **Pod Security Standards** (restricted), admission controller (OPA/Kyverno).
- Docker socket'i ASLA konteynere mount etme; privileged'dan kacin.
- **NetworkPolicy** ile mikro-segmentasyon; RBAC least privilege.
- Imaj tarama (Trivy/Grype), imzali imajlar, secret manager (env'de duz sir yok).
