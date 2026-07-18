# D1 — Reasoning (```dusunce```) Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Octópus'a araç/cevap öncesi kısa, göreve-özgü bir ```dusunce``` muhakeme bloğu üretmeyi öğreten KÜÇÜK pilot SFT verisi + bu bloğu kullanıcıdan gizleyen harness strip'i + format testleri.

**Architecture:** `dusunce` bloğu `arac` ile simetrik fenced ASCII bloktur; assistant metninin en başında gelir. Veri tarafında build_sft değişmez (blok sadece assistant içeriğidir; çok-turlu Tip B zaten `to_messages`+`flatten_tool_messages` ile desteklenir). Tek harness değişikliği: `dusunce` bloğunu kullanıcıya giden nihai cevaptan (`ToolLoopResult.final`) söken bir regex-strip. Pilot ölçek küçük (~40 örnek) — amaç "reasoning'i tam öğret" değil, retrain sonrası **araç güvenilirliği bozuluyor mu ölç**.

**Tech Stack:** Python 3.14, uv, pytest, plain regex (yeni bağımlılık YOK). Mevcut `agent/toolcall.py`, `agent/loop.py`, `data/sft/build_sft.py` pipeline.

## Global Constraints

- Blok adı ASCII **`dusunce`** (`düşünce` DEĞİL) — `arac` precedent'i (tokenizer sürüklenmesini önle). Marka `ó` yalnız modelin konuşmasında.
- Blok formatı: `` ```dusunce\n<metin>\n``` `` (fenced, `arac` ile aynı şekil), assistant turunun EN BAŞINDA, `arac`/cevaptan ÖNCE.
- Düşünce KISA: 2-5 cümle, ~40-90 kelime. Deneme yazısı YASAK (signal-balance).
- Natural CoT: göreve-özgü gerçek muhakeme; "Önce X, sonra Y" şablonu YASAK.
- Her reasoning örneği bir KARARLA biter (arac bloğu veya net cevap) — düşünce aracın YERİNE değil ÖNÜNE gelir.
- Veri kaydı: `{"messages":[...]}`, `ensure_ascii=False`, tek satır JSONL, `data/sft/distilled/` altına append.
- Türkçe içerik; teknik token'lar (arac blok JSON, IP/port/CVE/araç adı) BİREBİR.
- Doğrulama komutu: `uv run python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 3` → geçerli sayısı artmalı, 0 yeni dup; `uv run pytest -q` yeşil.
- ⚠️ Bu plan PARA HARCAMAZ. Ölçüm kapısı (retrain) ayrı para-checkpoint — plan sonunda dokümante, çalıştırılMAZ.

---

### Task 1: Harness — `strip_dusunce` + `_DUSUNCE_RE` (toolcall.py)

**Files:**
- Modify: `agent/toolcall.py` (mevcut `_ARAC_RE` yanına kardeş regex + fonksiyon)
- Test: `tests/agent/test_dusunce_strip.py` (yeni)

**Interfaces:**
- Consumes: yok (izole)
- Produces: `strip_dusunce(text: str) -> str` — metindeki tüm `` ```dusunce ... ``` `` bloklarını (ve bıraktığı fazla boş satırları) söker; blok yoksa metni aynen döndürür. `parse_arac_calls` gibi asla çökmez.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_dusunce_strip.py
from agent.toolcall import strip_dusunce


def test_dusunce_blogu_sokulur():
    t = "```dusunce\nSMB surumu lazim.\n```\nSonuc: port 445 acik."
    assert strip_dusunce(t) == "Sonuc: port 445 acik."


def test_blok_yoksa_ayni_metin():
    t = "Duz cevap, dusunce yok."
    assert strip_dusunce(t) == t


def test_arac_blogu_korunur():
    # dusunce sokulur AMA arac blogu dokunulmaz (harness onu ayri parse eder)
    t = "```dusunce\nAraci sec.\n```\n```arac\n{\"arac\": \"nmap\"}\n```"
    out = strip_dusunce(t)
    assert "dusunce" not in out
    assert "```arac" in out and "nmap" in out


def test_bos_string_cokmez():
    assert strip_dusunce("") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_dusunce_strip.py -q`
Expected: FAIL — `ImportError: cannot import name 'strip_dusunce'`

- [ ] **Step 3: Write minimal implementation**

`agent/toolcall.py` içinde `_ARAC_RE` satırının hemen altına ekle:

```python
_DUSUNCE_RE = re.compile(r"```dusunce\s*.*?```", re.S)


def strip_dusunce(text: str) -> str:
    """Kullaniciya giden metinden ```dusunce``` bloklarini sok (ic muhakeme gizli).

    Blok yoksa metni aynen dondurur; asla cokmez. arac blogu KORUNUR (ayri parse edilir).
    """
    out = _DUSUNCE_RE.sub("", text or "")
    return out.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_dusunce_strip.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/toolcall.py tests/agent/test_dusunce_strip.py
git commit -m "feat(d1): harness strip_dusunce — ic muhakeme blogunu kullanicidan gizle"
```

---

### Task 2: Harness — nihai cevaptan dusunce'yi strip et (loop.py)

**Files:**
- Modify: `agent/loop.py` (iki return noktası: satır ~34 ve ~41 — `ToolLoopResult(final=...)`)
- Test: `tests/agent/test_loop_dusunce.py` (yeni)

**Interfaces:**
- Consumes: `strip_dusunce` (Task 1)
- Produces: `ToolLoopResult.final` artık `dusunce` bloğu İÇERMEZ (kullanıcıya temiz cevap). `messages` geçmişi ise ham reply'ı (dusunce dahil) tutmaya devam eder — model kendi muhakemesini bağlamda görür.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_loop_dusunce.py
from agent.loop import run_tool_loop
from agent.messages import Message


def test_final_dusunce_icermez():
    # arac cagirmayan, dusunce+cevap ureten bir sahte model
    def fake_generate(messages):
        return "```dusunce\nBasit soru, arac gerekmez.\n```\nCevap: 42."

    res = run_tool_loop([Message("user", "kac?")], fake_generate, executor=None, max_steps=1)
    assert res.final == "Cevap: 42."
    assert "dusunce" not in res.final
```

Not: `run_tool_loop`'un gerçek imzasını Step 2'den önce `agent/loop.py`'den doğrula (parametre adları: generate fonksiyonu, executor, max_steps). Test çağrısını gerçek imzaya uyarla — imza farklıysa testi imzaya göre düzelt, davranış aynı kalır (final'da dusunce yok).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_loop_dusunce.py -q`
Expected: FAIL — `assert '...dusunce...' == 'Cevap: 42.'` (strip henüz uygulanmadı)

- [ ] **Step 3: Write minimal implementation**

`agent/loop.py` başına import ekle:

```python
from agent.toolcall import ToolCall, parse_arac_calls, strip_dusunce
```

Her iki `ToolLoopResult(final=...)` noktasında `final`'ı strip'le. Terminal (arac'sız) reply döndüren satır:

```python
        if not calls:
            return ToolLoopResult(final=strip_dusunce(reply), steps=step + 1, calls=executed)
```

ve max_steps sonrası son üretim:

```python
    final = generate(messages)
    messages.append(Message("assistant", final))
    return ToolLoopResult(final=strip_dusunce(final), steps=max_steps, calls=executed)
```

Not: `messages.append(Message("assistant", reply/final))` HAM metni saklar (strip'siz) — model geçmişte kendi muhakemesini görsün. Yalnız `final=` alanı strip'lenir.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_loop_dusunce.py -q`
Expected: PASS

- [ ] **Step 5: Run full harness suite (regresyon yok)**

Run: `uv run pytest tests/agent -q`
Expected: PASS (mevcut harness testleri + 2 yeni dosya)

- [ ] **Step 6: Commit**

```bash
git add agent/loop.py tests/agent/test_loop_dusunce.py
git commit -m "feat(d1): loop final'inda dusunce strip — gecmiste ham, kullaniciya temiz"
```

---

### Task 3: Pilot veri — Tip A (reasoning→cevap, bilgi) + format testi

**Files:**
- Create: `data/sft/distilled/octopus_distill_d1_reasoning.jsonl` (append hedefi)
- Create (scratchpad): `<scratchpad>/gen_d1_reasoning_a.py` (generator — repoya GİRMEZ)
- Create: `tests/data/test_dusunce_format.py` (yeni — d1 dosyasını doğrular)

**Interfaces:**
- Consumes: yok
- Produces: `data/sft/distilled/octopus_distill_d1_reasoning.jsonl` — her kayıt `{"messages":[user, assistant]}`; assistant içeriği `` ```dusunce\n...\n``` `` ile BAŞLAR, sonra nihai cevap gelir.

- [ ] **Step 1: Format testini yaz (henüz dosya yok → fail)**

```python
# tests/data/test_dusunce_format.py
import json, re
from pathlib import Path

P = Path("data/sft/distilled/octopus_distill_d1_reasoning.jsonl")
DUSUNCE = re.compile(r"```dusunce\s*(.*?)```", re.S)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 15


def test_her_assistant_dusunce_ile_baslar():
    # ilk assistant turu ```dusunce``` ile baslamali (bloklardan once)
    for o in _rows():
        first_asst = next(m["content"] for m in o["messages"] if m["role"] == "assistant")
        assert first_asst.lstrip().startswith("```dusunce"), first_asst[:60]


def test_dusunce_kisa():
    # signal-balance: dusunce govdesi <= 90 kelime
    for o in _rows():
        for m in o["messages"]:
            if m["role"] != "assistant":
                continue
            for body in DUSUNCE.findall(m["content"]):
                n = len(body.split())
                assert n <= 90, f"dusunce cok uzun ({n} kelime): {body[:60]}"


def test_dusunce_asci_ad():
    # marka disi kontrol token'i ASCII olmali: govde disinda 'düşünce' fence adi YOK
    for o in _rows():
        blob = " ".join(m["content"] for m in o["messages"])
        assert "```düşünce" not in blob and "```dusunce" in blob
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_dusunce_format.py -q`
Expected: FAIL — `FileNotFoundError` / dosya yok

- [ ] **Step 3: Generator'ı yaz ve çalıştır (Tip A, ~15 örnek)**

Scratchpad'e `gen_d1_reasoning_a.py` yaz (Faz C deseni: PAIRS listesi → append). Her `assistant` içeriği `` ```dusunce\n<kısa muhakeme>\n``` `` + nihai cevap. Örnek 3 kayıt (gerisi aynı şekil, göreve-özgü natural CoT — teknik doğru, şablon YASAK):

```python
# <scratchpad>/gen_d1_reasoning_a.py
import json
from pathlib import Path

PAIRS = [
 ("Bir hedefte 445/tcp açık görünüyor ama servis sürümü yok. EternalBlue riski var mı, nasıl karar veririm?",
  "```dusunce\n445 SMB demek ama EternalBlue (MS17-010) yalnız SMBv1'de ve yamasız Windows'ta geçerli; sürüm ve imza olmadan risk kararı veremem. Önce SMB diyalektini ve yama durumunu tespit etmeliyim.\n```\n"
  "445/tcp tek başına EternalBlue kanıtı değildir. Karar için: (1) SMB sürümünü/diyaletini tespit et — SMBv1 aktif mi (nmap `smb-protocols` betiği veya `--script smb-security-mode`); yalnız SMBv1 varsa risk yükselir. (2) MS17-010 özel kontrolü: `nmap --script smb-vuln-ms17-010 -p445 <hedef>` doğrudan yama durumunu söyler. (3) İşletim sistemi/yama seviyesi. Savunma tarafı: SMBv1'i tamamen kapat, MS17-010 yamasını uygula, 445'i internete kapat, ağ segmentasyonu. Sürüm bilinmeden 'açık = savunmasız' demek yanlış pozitiftir."),
 ("Log4Shell (CVE-2021-44228) için bir web uygulamasını nasıl önceliklendirip test ederim?",
  "```dusunce\nLog4Shell JNDI lookup'lı savunmasız log4j2 sürümlerinde; risk = savunmasız sürüm + saldırgan-kontrollü girdinin loglanması. Önce nerede log4j2 var ve girdi loga düşüyor mu, onu haritalamalıyım.\n```\n"
  "Önceliklendirme: (1) Envanter — hangi uygulamalar log4j2 (2.0-2.14.1) kullanıyor; bağımlılık taramasıyla (SCA) çıkar. (2) Ulaşılabilirlik — kullanıcı girdisi (User-Agent, başlık, form) loglanıyor mu; internete açık olanlar en yüksek öncelik. Test (yetkili): kontrollü bir `${jndi:ldap://<senin-collab>/x}` payload'ını başlıklara koyup KENDİ dinleyicine (OOB/DNS callback) çağrı gelip gelmediğini gözle — gerçek exploit değil, ulaşılabilirlik kanıtı. Savunma: log4j2'yi 2.17.1+'a yükselt (asıl çözüm), geçici olarak `log4j2.formatMsgNoLookups=true` / JndiLookup sınıfını kaldır, WAF imzası (kalıcı değil), giden trafiği kısıtla."),
 ("Bir kullanıcı 'parolam güvenli mi' diye soruyor ama parolayı mesajda paylaştı. Ne yaparım?",
  "```dusunce\nKullanıcı parolasını ifşa etti — bunu analiz etmek yerine güvenlik riskini işaret etmeli, parolayı tekrar etmemeli ve hiçbir yerde saklamamalıyım. Asıl yardım: parolayı değiştir + genel güç ilkeleri.\n```\n"
  "Parolanı burada paylaşmaman gerekirdi — paylaşılan bir kanaldaki parola artık ifşa olmuş sayılır. Onu tekrar yazmıyorum ve saklamıyorum. Öneri: (1) Bu parolayı kullandığın her yerde HEMEN değiştir, özellikle e-posta ve tekrar kullandıysan diğer hesaplar (parola tekrarı en büyük risk). (2) Yeni parola uzun ve benzersiz olsun; parola yöneticisi kullan. (3) Mümkün olan her yerde MFA aç (parola sızsa bile hesabı korur). Güç değerlendirmesini parolayı görmeden ilkelerle yapabilirim: uzunluk (>16), benzersizlik ve MFA, karmaşıklık kurallarından daha önemlidir."),
]

def main():
    out = Path("data/sft/distilled/octopus_distill_d1_reasoning.jsonl")
    n = 0
    with open(out, "a", encoding="utf-8") as w:
        for u, a in PAIRS:
            w.write(json.dumps({"messages": [
                {"role": "user", "content": u},
                {"role": "assistant", "content": a},
            ]}, ensure_ascii=False) + "\n")
            n += 1
    print(f"[OK] D1 Tip A: +{n} -> {out}")

if __name__ == "__main__":
    main()
```

PAIRS'i ~15 örneğe tamamla (kırmızı+mavi, göreve-özgü natural CoT, teknik doğru). Sonra:

Run: `uv run python <scratchpad>/gen_d1_reasoning_a.py`
Expected: `[OK] D1 Tip A: +15 -> data/sft/distilled/octopus_distill_d1_reasoning.jsonl`

- [ ] **Step 4: Format testini geçir + build doğrula**

Run:
```bash
uv run pytest tests/data/test_dusunce_format.py -q
uv run python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 3
```
Expected: format testi PASS; build "Gecerli" sayısı ~15 artar, "Atlanan" değişmez (0 yeni dup).

- [ ] **Step 5: Tüm suite + commit**

```bash
uv run pytest -q   # 150+ yesil
git add data/sft/distilled/octopus_distill_d1_reasoning.jsonl data/sft tests/data/test_dusunce_format.py
git commit -m "feat(d1): reasoning pilot Tip A (reasoning->cevap, ~15 ornek) + format testi"
```

---

### Task 4: Pilot veri — Tip B (reasoning→arac→tool→reasoning, agentic) + zincir doğrulama

**Files:**
- Modify: `data/sft/distilled/octopus_distill_d1_reasoning.jsonl` (Tip B kayıtları append)
- Create (scratchpad): `<scratchpad>/gen_d1_reasoning_b.py`
- Modify: `tests/data/test_dusunce_format.py` (çok-turlu zincir + arac birlikteliği testi ekle)

**Interfaces:**
- Consumes: Task 3 format testi (genişletilir)
- Produces: aynı dosyaya çok-turlu kayıtlar: `user → assistant(dusunce+arac) → tool → assistant(dusunce+cevap)`. `tool` rolü `to_messages`+`flatten_tool_messages` ile desteklenir (build_sft değişmez).

- [ ] **Step 1: Zincir testini ekle (fail)**

`tests/data/test_dusunce_format.py`'ye ekle:

```python
def test_agentic_zincirde_dusunce_ve_arac_birlikte():
    # En az bir kayit: tool rolu iceren zincir + arac blogu iceren assistant turu
    ARAC = re.compile(r"```arac\s*\{.*?\}\s*```", re.S)
    chain_hits = 0
    for o in _rows():
        roles = [m["role"] for m in o["messages"]]
        if "tool" in roles:
            chain_hits += 1
            # tool'dan onceki assistant hem dusunce hem arac icermeli
            asst_with_arac = [m for m in o["messages"]
                              if m["role"] == "assistant" and ARAC.search(m["content"])]
            assert asst_with_arac, "agentic zincirde arac blogu yok"
            for m in asst_with_arac:
                assert "```dusunce" in m["content"], "arac'li turda dusunce yok"
    assert chain_hits >= 20, f"agentic zincir az: {chain_hits}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/data/test_dusunce_format.py::test_agentic_zincirde_dusunce_ve_arac_birlikte -q`
Expected: FAIL — `agentic zincir az: 0`

- [ ] **Step 3: Generator (Tip B, ~25 örnek) yaz ve çalıştır**

Scratchpad `gen_d1_reasoning_b.py` — her kayıt çok-turlu. Örnek 1 kayıt (gerisi göreve-özgü):

```python
# <scratchpad>/gen_d1_reasoning_b.py  (iskelet — RECORDS'u ~25'e tamamla)
import json
from pathlib import Path

RECORDS = [
 [
  {"role": "user", "content": "10.10.10.5 sunucusunda hangi servisler var, riskli olan var mı?"},
  {"role": "assistant", "content":
   "```dusunce\nÖnce açık port ve servis sürümlerini görmem gerek; körlemesine risk diyemem. Bir sürüm taraması başlatıp çıktıya göre yorumlarım.\n```\n"
   "```arac\n{\"arac\": \"nmap\", \"parametreler\": {\"hedef\": \"10.10.10.5\", \"secenekler\": \"-sV\"}}\n```"},
  {"role": "tool", "content": "22/tcp open ssh OpenSSH 7.2p2\n80/tcp open http Apache 2.4.7\n445/tcp open microsoft-ds Samba 3.6.3"},
  {"role": "assistant", "content":
   "```dusunce\nSamba 3.6.3 ve Apache 2.4.7 eski; Samba 3.x'te uzaktan kod yürütme CVE'leri (ör. CVE-2015-0240) var, OpenSSH 7.2 de güncel değil. En yüksek risk Samba.\n```\n"
   "Tarama sonucu: eski ve riskli sürümler var. Öncelik sırası: (1) Samba 3.6.3 — 3.x serisinde kritik RCE geçmişi (CVE-2015-0240 vb.), 445 internete açıksa acil; yamalı sürüme çık veya SMB'yi segmentle. (2) Apache 2.4.7 (2013) — çok sayıda yamalı açık; güncelle. (3) OpenSSH 7.2p2 — güncelle, parola yerine anahtar+MFA. Savunma: gereksiz servisleri kapat, yama, ağ segmentasyonu, 445'i dışarı kapat."},
 ],
]

def main():
    out = Path("data/sft/distilled/octopus_distill_d1_reasoning.jsonl")
    n = 0
    with open(out, "a", encoding="utf-8") as w:
        for rec in RECORDS:
            w.write(json.dumps({"messages": rec}, ensure_ascii=False) + "\n")
            n += 1
    print(f"[OK] D1 Tip B: +{n} -> {out}")

if __name__ == "__main__":
    main()
```

RECORDS'u ~25 zincire tamamla (farklı araçlar: nmap/nikto/gobuster/theHarvester/CVE okuma; kırmızı+mavi; teknik doğru). Sonra:

Run: `uv run python <scratchpad>/gen_d1_reasoning_b.py`
Expected: `[OK] D1 Tip B: +25 -> ...`

- [ ] **Step 4: Testler + build doğrula**

Run:
```bash
uv run pytest tests/data/test_dusunce_format.py -q
uv run python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 3
```
Expected: tüm format testleri PASS (zincir dahil); build "Gecerli" ~25 daha artar, 0 yeni dup.

- [ ] **Step 5: Tüm suite + commit**

```bash
uv run pytest -q
git add data/sft/distilled/octopus_distill_d1_reasoning.jsonl data/sft tests/data/test_dusunce_format.py
git commit -m "feat(d1): reasoning pilot Tip B (agentic zincir, ~25 ornek) + zincir dogrulama"
```

---

### Task 5: Pilot doğrulama — teknik doğruluk taraması + signal-oran raporu + memory

**Files:**
- Create (scratchpad): `<scratchpad>/d1_signal_report.py` (oran ölçümü — repoya girmez)
- Modify: `docs/superpowers/plans/2026-07-18-d1-reasoning-pilot.md` (ölçüm-kapısı sonucu notu — retrain sonrası doldurulur)
- Modify: memory `octopus-dataset-expansion.md` + `MEMORY.md` (D1 pilot durumu)

**Interfaces:**
- Consumes: Task 3+4 verisi
- Produces: pilot kalite kanıtı; retrain öncesi hazır durum.

- [ ] **Step 1: Teknik doğruluk taraması (Faz C dersi — testler içeriği doğrulamaz)**

D1 dosyasındaki her CVE-ID, komut/flag, sürüm ve gerçek-vaka iddiasını ELLE gözden geçir (grep ile spesifikleri çek). Yanlış olanı düzelt, generator'ı yeniden çalıştırmadan önce `git checkout -- <dosya>` ile sıfırla ve düzeltilmiş generator'la yeniden üret (Faz C akışı). Örnek çekme:

Run: `uv run python -c "import json; [print(m['content'][:200]) for l in open('data/sft/distilled/octopus_distill_d1_reasoning.jsonl',encoding='utf-8') if l.strip() for m in json.loads(l)['messages'] if m['role']=='assistant']" | grep -iE "cve-|nmap|--script|[0-9]+\.[0-9]+"`

- [ ] **Step 2: Signal-oran raporu (pilot ölçek küçük kalmalı)**

`<scratchpad>/d1_signal_report.py` — train setinde reasoning örneklerinin oranını ve ortalama dusunce/arac token uzunluğunu ölç. Amaç: reasoning oranı düşük (~%2-3), dusunce ortalaması kısa (<90 kelime) olduğunu teyit.

```python
import json, glob, re
DUS = re.compile(r"```dusunce\s*(.*?)```", re.S)
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
rows = [json.loads(l) for f in glob.glob("data/sft/distilled/*.jsonl") for l in open(f,encoding="utf-8") if l.strip()]
d1 = [o for o in rows if any("```dusunce" in m["content"] for m in o["messages"])]
dl = [len(b.split()) for o in d1 for m in o["messages"] for b in DUS.findall(m["content"])]
print(f"toplam distill: {len(rows)} | reasoning kaydi: {len(d1)} ({100*len(d1)/len(rows):.1f}%)")
print(f"dusunce ort kelime: {sum(dl)/len(dl):.0f} | max: {max(dl)} | min: {min(dl)}")
```

Run: `uv run python <scratchpad>/d1_signal_report.py`
Expected: reasoning ~%2-4, dusunce ort <90 kelime. Oran yüksekse örnek çıkar.

- [ ] **Step 3: Memory güncelle**

`octopus-dataset-expansion.md`'ye D1 pilot durumu (dosya, örnek sayısı, harness strip commit'leri, ölçüm kapısı beklemede) + `MEMORY.md` index satırı. `[[octopus-finetune-state]]` bağla.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-07-18-d1-reasoning-pilot.md
git commit -m "docs(d1): pilot dogrulama — teknik tarama + signal-oran raporu tamam"
```

---

## PİLOT DURUMU (2026-07-18 — kod tamam, retrain bekliyor)

Task 1-5 tamamlandı. Veri `data/sft/distilled/octopus_distill_d1_reasoning.jsonl` = **39 kayıt**
(15 Tip A reasoning→cevap + 24 Tip B agentic zincir). Commit'ler: `84f2400` strip_dusunce · `d464d27`
loop entegrasyon · `7564cd3` Tip A · `0df5e90` Tip B. Test suite 161 yeşil (format+strip+zincir).
**Signal-oran sağlıklı:** reasoning distill'in %3.4'ü, düşünce ort **22 kelime** (max 28, cap 90) —
araç sinyalini boğmayacak ölçekte. Teknik doğruluk elle tarandı: CVE/sürüm/vaka iddiaları PASS
(CVE-2021-4034=PwnKit, -44228=Log4Shell, -41773=Apache 2.4.49, -0778=OpenSSL DoS; KRACK/Dragonblood
doğru; uydurma yok). **Ölçüm-kapısı sonucu:** _(retrain sonrası doldurulacak)_.

## ÖLÇÜM KAPISI (retrain SONRASI — 💰 PARA-CHECKPOINT, bu planın DIŞI)

Bu plan biter bitmez pilot verisi hazırdır AMA reasoning'in araçları bozup bozmadığı ancak
retrain'le ölçülür. **DUR — kullanıcı onayı olmadan retrain yapma.** Retrain sonrası:

1. Mevcut agent harness (`parse_arac_calls` + 39 test) ile v0.7 vs v0.8-pilot **araç-çağrı
   güvenilirliği** kıyasla: arac bloğu üretme oranı, JSON geçerliliği, doğru araç seçimi.
2. **Eşik:** araç güvenilirliğinde >~5 puan düşüş YOKSA → D1'i ölçekle + D2 (hafıza) + D3 (skill).
   VARSA → düşünceyi kısalt / oranı düşür / loss-masking pilotu; olmuyorsa reasoning'i v0.9'a
   ertele, v0.8'i D2+D3 ile gönder.
3. Sonucu bu belgenin "ölçüm-kapısı sonucu" notuna yaz.

## Self-review (yazım sonrası)
- **Spec kapsamı:** D1 format (Task 1-2 harness), Natural CoT + kısa (Task 3-4 veri + testler),
  signal-balance (Task 5 oran raporu + kısa-test), ölçüm kapısı (plan sonu) — hepsi karşılandı.
  D2/D3 bu planın DIŞI (spec'te eskiz, ayrı plan alacak) — kapsam doğru.
- **Placeholder:** generator PAIRS/RECORDS "~15/~25'e tamamla" — bu şablon değil, örnek+net hedef
  sayı + net kalite kuralı (Global Constraints) veriyor; her adımda çalışan kod var.
- **Tip tutarlılığı:** `strip_dusunce(text:str)->str` Task 1'de tanımlı, Task 2'de aynı imzayla
  tüketiliyor. `_DUSUNCE_RE`/`DUSUNCE` regex adları test/impl'de tutarlı.
