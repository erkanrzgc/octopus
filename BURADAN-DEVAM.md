# ▶️ BURADAN DEVAM — Octópus

Yeni oturum, hoş geldin. Bu klasör (`C:\Users\erkanrzgc\Desktop\Octopus`, ASCII) **tek çalışma yeri**.
Önce şunlar yüklenir/okunur: `CLAUDE.md` (otomatik) · `OCTOPUS.md` (vizyon) ·
`docs/decisions/0002-pivot-to-finetuning.md` (güncel strateji) · `~/.claude/plans/atomic-jumping-swan.md` (plan).

## 🤖 OTONOM PLAYBOOK — v0.6 (loop için; ÖNCE BUNU OKU)

> Kullanıcı uzakta, /loop ile otonom çalışıyorsun. Amaç: **v0.6 = Türkçe-uzman taban** (dil #1 önceliği,
> "Namık Kemal gibi Türkçe"). Her turda bir adım ilerlet, durumu buraya işle.

**✅ v0.6 GERÇEK KÖK SEBEP BULUNDU (2026-07-05): unsloth 4bit (NF4) KUANTİZASYONU.**
Çift-BOS teşhisi (aşağıda arşiv) fix'lendi AMA çöp gitmedi (smoke yine RED, loss 23→11, çok-dilli çöp).
**Kesin kanıt (pod'da `scratchpad/bf16_test.py`, düz transformers):** Turkish-Gemma-9b-v0.1 `bf16`'da
**KUSURSUZ** Türkçe üretiyor ("Merhaba! Ben Google tarafından eğitilmiş bir dil modeliyim…" + hatasız SQL
injection anlatımı). Çöp **tamamen** unsloth'un **4bit NF4** kuantizasyonundan geliyordu.
**Neden bu model:** Turkish-Gemma continual-pt + SFT + DPO + **merge** geçmiş; NF4 bu merge'li ağırlıkları
bozuyor. Qwen temiz kuantalanıyor, bu Gemma kuantalanmıyor. (Bug taban-özel, unsloth-genel değil.)
**ÇÖZÜM = 4bit'i bırak, `bf16 LoRA` eğit.** Turkish-Gemma bf16 ≈18GB, RTX 4090 24GB'a LoRA ile sığar
(model bf16 + gradient-checkpointing + seq 1024 + batch1/accum8 ≈ 21GB). Dil #1 için doğru taban BU.
**Yol:** düz transformers + peft `LoraConfig` + TRL SFTTrainer, `torch_dtype=bfloat16`, `load_in_4bit=False`
(bf16 testinin çalışan deseni). Yeni script `train/sft_bf16.py`.
**✅✅ bf16 SMOKE GEÇTİ (2026-07-05, ~$0.40, pod silindi):** Turkish-Gemma bf16 LoRA, 40 adım →
**loss 2.72→0.51** (sağlıklı, Qwen-benzeri; çift-BOS turunun ~random 23→11'inin tam zıttı) · zirve VRAM
**23.13/23.6 GB** (sığdı ama SINIRDA — tam turda dikkat) · **üretim AKICI TÜRKÇE:** persona "Octópus'um"
(doğru ó, v0.2 "Octópüs" pürüzü YOK) + SQL injection somut `id=1 OR 1=1-- -`/parametreli sorgu + komşu-WiFi
**reddi+savunma alternatifi** (ret kalibrasyonu tam). **KÖK SEBEP TEZİ KANITLANDI: 4bit çöpü gitti.**
**Tam tur için 2 küçük düzeltme kod'a işlendi** (`sft_bf16.py`): (a) gen'de grad-ckpt+require_grads hook kapat
(dynamo `requires_grad_` çökmesi), (b) `eos_token_id`'ye `<end_of_turn>`(107) ekle (sahte çok-turlu diyalog
uydurmasın). Ayrıca sürüm pini: **transformers 4.49 / trl 0.15.2 / peft 0.14 / accelerate 1.4** (torch 2.4 uyumu;
en yeni TRL DTensor ister → pod torch 2.4'te patlıyor). Bakiye smoke sonrası ~$6.

**🎉 v0.6 TAM TUR BİTTİ (2026-07-06, ~$1.7, pod silindi) — BAŞARILI, v0.2'yi GEÇTİ:**
Turkish-Gemma bf16 LoRA, **Türkçe-only** (918 distill + seed×10 = 2306 örnek), 900 adım (~3 epoch) →
**son loss 0.22**, token doğruluğu %97, zirve VRAM 23.01GB. **5 üretim testi (ayrı taze process, base+adapter):**
kimlik "Ben Octópus" ✓ · SSH sertleştirme somut `sshd_config` bloğu ✓ · SQLi parametreli sorgu ✓ ·
komşu-WiFi **reddi+savunma** ✓ · yetkili Metasploit **tam derinlik** (msfvenom/nc/lateral) ✓. Akıcı/edebî
Türkçe — v0.2'nin Qwen pürüzleri YOK. Ufak sampling kayması ("Octómus"/"güvenlek") kozmetik → v0.7 greedy/veri.
**Adapter yerelde:** `checkpoints_sft/octopus-gemma-v6-adapter/` (safetensors sha256 doğrulandı, chunked indirildi).
**HF:** `erkanrzgcc/octopus-gemma-v0.6` (private) — ✅ YÜKLENDİ (466.6 MB commit'li: adapter 432 + tokenizer 34).

**▶️ v0.7 = SİBER DERİNLİK (2026-07-06 araştırma yapıldı):** dil kilitlendi, sıradaki siber veri.
Kataloglar: **`docs/v0.7-data-catalog.md`** (küratörlü + akademik + Türkçe) · **`docs/v0.7-hf-cyber-datasets-full.md`**
(831 gerçek siber HF seti, 338 temiz lisans, boyuta göre). Strateji: **kaliteli siber veri İngilizce →
Türkçeye DAMIT** (918-deseni). Akademik (UNB CIC/York/gfek) çoğu NetFlow/PCAP/ML → çevirme, **Türkçe Q&A/RAG'e
DÖNÜŞTÜR** (istisna: UNB SBAN NL-katmanı + York SQLInj çevrilebilir). Devler: Trendyol All-CVE-Chat-MultiTurn,
jason-oneal MITRE+CVE+ExploitDB (chatml, 1M+), rezaduty QA-v2, AlicanKiraz All-CVE, WhitzardAgent CyberSecurity-100B.
Türkçe özgün: yusufarbc Siber-Guvenlik-Rehberi (CC-BY→RAG), fuysaal TryHackMe-CTF, AltaySec/red-team-el-kitabi (Türkçe komut ref), berenkg/Kutu-Cozumleri, brkyagl network-CTF, coderserdar PDF'ler.
**Araç kataloğu:** `docs/v0.7-tools-catalog.md` (~90 araç, 10 alan).
**🛠️ TOOL-USE SFT BAŞLADI (teacher = ben, oturum-içi, bedava):** `data/sft/tools/*.jsonl` — 54 örnek, 47 araç,
5 ret, 6 çok-adımlı zincir. Format: system(persona+```arac``` blok) → user(TR görev) → assistant(akıl+araç çağrısı)
→ tool(çıktı) → assistant(yorum+savunma+yetki-kapısı). Alanlar: ağ/web/exploit/AD/parola/kablosuz/forensic/
trafik/OSINT/C2/MITM/bulut/privesc/RE/zincirler. **KALAN: hedef ~300-500'e ölçekle** (AltaySec red-team-el-kitabi
+ araç başına 3-10 senaryo), sunucu/blue-team dalgası, sonra runtime harness (`agentic-model`'den port) →
v0.7 eğitimi (Turkish-Gemma + bilgi + tool-use, RunPod, 💰 checkpoint). **Damıtma teacher = ben (bedava) / API (ölçek 💰).**

**⏳ KALAN TEK ADIM = GGUF (yerel RTX 5060 8GB çalıştırma için):** pod'da merge+GGUF env-çakışması yaşadı
(llama.cpp requirements.txt merge deps'ini bozdu → BloomPreTrainedModel/torchvision::nms). **Çözüm yazıldı:**
`cloud/pod_gguf_clean.sh` — DOĞRU SIRA: önce merge (pinli env sağlam), SONRA llama.cpp deps + cmake.
Tekrar denemek için: yeni pod aç → `v6-adapter`'ı scp'le → `pod_gguf_clean.sh` koştur → Q4_K_M indir (~5.5GB).
Bilinen tuzaklar çözülü: cmake yok (`pip install cmake`), tokenizer.model gerekir (hub'dan çekiliyor),
generation_config do_sample=True. **v0.6 bf16'da çalışıyor; GGUF sadece yerel-çalıştırma paketlemesi.**

<details><summary>ARŞİV — çift-BOS teşhisi (fix uygulandı ama asıl sebep değildi)</summary>
Gemma chat template metne literal `<bos>` basar; TRL SFTTrainer add_special_tokens=True ile yeniden tokenize
edip 2. `<bos>` ekler → `<bos><bos>`. Fix (`sft_smoke.py` `_to_text`: baştaki bos'u sıyır) uygulandı, Qwen no-op.
Bu gerçek bir kusurdu ama tek başına çöpü çözmedi → asıl sebep 4bit kuantizasyonuymuş (yukarıda).
</details>

**💰 PARA GÜVENLİK TAVANLARI (MUTLAK — çiğneme):**
- **Bakiye < $2.50 ise YENİ POD AÇMA** → dur, kullanıcıyı bekle. (`runpodctl user` ile kontrol et.)
- Aynı anda **TEK pod**. Pod'u her zaman `--terminate-after` (+3sa) ile aç.
- Adapter'ı **sha256 doğrula**, doğrulanınca HEMEN indir + pod'u SİL. Silmeden başka iş yapma.
- Her turda `runpodctl pod list` boş mu + `currentSpendPerHr` 0 mı kontrol et (kaçak pod yok).

**v0.6 ADIMLARI (sırayla — bf16 YOLU):**
1. **`train/sft_bf16.py` yaz** (ücretsiz, yerel): düz transformers + peft LoraConfig + TRL SFTTrainer,
   `AutoModelForCausalLM.from_pretrained(..., torch_dtype=bfloat16)`, `load_in_4bit=False`,
   `gradient_checkpointing_enable()`. r=32, target 7 modül, seq 1024, batch1/accum8, lr 2e-4.
   Çift-BOS sıyırma fix'i KALIR (Gemma template literal <bos> basar; TRL yine ekler). NO unsloth 4bit.
2. **`cloud/pod_run_smoke_bf16.sh` yaz:** yerel veri (distill 918 + seed ×20), taban
   `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`, `--max-steps 40 --max-train 2000`. Bağımlılık: transformers
   peft trl datasets accelerate bitsandbytes (unsloth YOK). Model bf16 indir (~18GB pod'da, HF hızlı).
3. **bf16 SMOKE pod** (~$0.30): loss düşüyor mu (bu sefer <2 beklenir) + üretim akıcı Türkçe mi?
   Yeşilse → tam tur (2000 adım, Fenrir+distill+seed karışım). Kırmızıysa → interaktif debug (para-disiplini).
4. **Bundle + pod + monitor + verify + sil** — v5 deseni. SSH key: `C:\Users\erkanrzgc\.runpod\ssh\runpodctl-ssh-key`.
5. **Değerlendir + ship:** v0.6 Türkçe akıcılık v0.2'yi net geçiyor mu? İyiyse → LoRA merge → GGUF Q4 →
   HF (`erkanrzgcc/octopus-gemma-v0.6`) + yerel RTX 5060 8GB'de çalıştır. Değilse → veri oranı/gen ayarla, not düş.

**HAZIR ELDE:** 918 distilled Türkçe cyber (`data/sft/distilled/octopus_distill_tr.jsonl`) · seed 87
(`build_seed`+`build_cyber_seed`) · RAG (784 parça, `rag/build_rag.py`) · serve script (`serve/octopus_chat.py`).
**Yerel eğitim OLMAZ** (venv 3.14) → RunPod. Yerel İNFERENCE için cyberm4fia venv (3.12+unsloth).
**Kullanıcı dönünce:** özet çıkar (kaç tur, bakiye, v0.6 sonuç, kalan). Para biterse durdur.

---

## 🎯 STRATEJİ (2026-07-03) — FINE-TUNING

From-scratch pretraining **bırakıldı** (maliyet: RunPod $60-150+, milyarlarca token). **QLoRA fine-tuning**e
dönüldü (~$3-15, birkaç saat, çok daha yüksek yetenek tavanı). Karar + gerekçe + kanıt: **ADR 0002**.

- **Taban:** `Qwen3-8B` (Türkçe-native + Apache 2.0 + yerel-önce). Yükseltme: `Qwen3-14B`.
- **Kural:** DİL tabanda, BİLGİ sonradan. Türkçe akıcılığı LoRA'yla enjekte edilemez → Qwen3; siber bilgi
  QLoRA'yla eklenir (kanıt: `DexopT/Qwen3-4B-Cybersecurity`, `CyberSecQwen-4B`, ve atamız cyberm4fia).
- **Motor:** Unsloth QLoRA (r=32 başlangıç, seq 1024→2048, lr 2e-4, AdamW8bit).

## ✅ SFT VERİ HAZIR (2026-07-03) — hibrit karışım

`data/sft/` builder yazıldı + koştu. **`data/sft/{train,val,test}.jsonl`** üretildi (gitignore'lu):
- **train 105,192 / val 2,191 / test 2,191**; her örnekte system = Octópus persona/guardrail (%100).
- Karışım (kullanıcı kararı "az Türkçe + karışık"): **fenrir 99,866** (İngilizce cyber çekirdek, Apache-2.0)
  + **instructurca 9,682** (Türkçe akıcılık, Apache-2.0, unutma-önleyici) + **seed_tr 26** (elle-yazılmış
  Türkçe sunucu/red-blue/persona/guardrail).
- Kod: `data/sft/persona.py` · `normalize.py` (13 birim testi geçti) · `build_sft.py` · `seed_tr/build_seed.py`.
- Kaynak system'i atılıp Octópus personası konur (`apply_octopus_system`). Yeniden üret:
  `uv run python data/sft/seed_tr/build_seed.py && uv run python -m data.sft.build_sft`.

**Skill'ler** (`.claude/skills/`): `octopus-data` (veri), `octopus-finetune` (QLoRA), `octopus-eval` (kalite+safety).

## ✅ YEREL DUMAN TURU GEÇTİ (2026-07-03)

`train/sft_smoke.py` (cyberm4fia'nın Python 3.12+unsloth venv'iyle koşuldu; Octópus .venv 3.14 torch desteklemez).
Qwen3-4B-Instruct-2507 (4-bit) QLoRA, 2000 örnek altküme, 40 adım:
- **Loss 2.97 → 1.01** (ort. 1.57) — sağlıklı düşüş. **OOM crash yok.**
- **Zirve VRAM 9.67 GB** → 4B bile 8GB'yi aşıp Windows paylaşımlı belleğe taştı (çalıştı ama yavaş).
  **KANIT: gerçek 8B turu YEREL DEĞİL, RunPod şart.**
- Üretim testi: "Kimsin sen?" → **"Ben Octópus…" (Türkçe, persona bağlandı)** ✓; nginx TLS → Türkçe konuya girdi;
  komşu-WiFi → saldırı adımı VERMEDİ (yetki dili). Pipeline uçtan uca kanıtlandı.
- **Undertraining artefaktları (40 adım/26 persona örneği normali):** system prompt'u birebir tekrarlıyor,
  "asistansın" (2. şahıs sızması), nginx cevabı somut config vermiyor. → tam eğitim + seed_tr büyütünce oturur.

## ✅ RUNPOD v0.1 BİTTİ (2026-07-04) + v0.2 HAZIR

**v0.1 — Qwen3-8B QLoRA, RunPod RTX 4090, 2000 adım, tam 105k veri:**
- **Son loss 0.81** (cyberm4fia 0.77'ye yakın), zirve VRAM 8.5GB, maliyet ~$0.80. Pod silindi.
- Adapter HF'de: **`erkanrzgcc/octopus-8b-qlora`** (private). Yerel yedek: `checkpoints_sft/octopus-8b-adapter/`
  (adapter_config.json elle yeniden oluşturuldu — scp trailer'ı kesikti ama safetensors 504 tensör TAM).
- **Ders:** pod silmeden ÖNCE transferi doğrula (scp "failed 255"i kozmetik sanmıştım; ağırlıklar neyse ki tam çıktı).
- Üretim testi karışık: ret ✅, ama **kimlik tekrar-döngüsü** + sunucu sığ + Qwen3-8B thinking `<think>` üretti.

**v0.2 HAZIR (3 kök-neden düzeltmesi — kullanıcı onaylı kalibrasyon):**
1. **Seed 61'e genişledi** (`build_seed.py`): persona 12 + **authz_offensive 14 (YENİ: yetkili saldırı→tam yardım)**
   + server 15 + ret 4 (rızasız-3.-tarafa daraltıldı). Kalibrasyon: yetki dahilinde HER ŞEY, aşırı-ret yok.
2. **Upsampling** (`build_sft.py --seed-repeat 20`): Türkçe seed'i train'de 20× tekrarla → kimlik "iğne" olmaktan çıksın.
3. **thinking-kapalı + generation fix** (`sft_smoke.py`): `enable_thinking=False` + attention_mask + `no_repeat_ngram_size=4`
   → tekrar döngüsünü kes.

## ✅ RUNPOD v0.2 BİTTİ (2026-07-04) — düzeltmeler TUTTU

Qwen3-8B QLoRA, RTX 4090, 2000 adım, seed×20 upsample, thinking-kapalı → **son loss 0.80**, ~$0.73, bakiye $11.55.
Adapter **sha256 doğrulandı** (transfer tam) → indirildi → pod silindi. HF: `erkanrzgcc/octopus-8b-qlora` (v0.2 commit).

**Üretim testi — v0.1'e göre gece-gündüz:**
- Kimlik: **"Ben Octópus… kırmızı+mavi ekip, lab/CTF/izinli sistemlerde geniş yardım…"** — tutarlı ✓ (v0.1 tekrar-döngüsü KIRILDI)
- nginx: artık ` ```nginx ` somut config veriyor ✓ (v0.1 muğlaktı)
- Ret KALİBRE ✓: komşu-WiFi'yi reddediyor + savunma öneriyor + **"yetkili lab/CTF olsaydı araçları adım adım verirdim"** (tam kapasite, yetki kapısıyla — sahibin istediği davranış)

**Kalan ufak kusurlar (v0.3 için):** dil pürüzleri ("Octópüs" yazımı, "Sevimsel"/"Bilgilerinizde" tuhaf kelimeler),
Türkçe cyber derinliği hâlâ orta. → v0.3: seed'i biraz daha büyüt + Türkçe kalite/distillation + belki daha çok adım.

## ✅ RAG GROUNDING KURULDU (2026-07-04)

cyberm4fia'dan port edildi (Türkçe bilgi, doğru ID'ler). `rag/knowledge/` (18 dosya) + `rag/build_rag.py`
(chunk→MiniLM→Chroma). Index kuruldu: **784 parça** `octopus_kb` (`rag/chroma/`, gitignore'lu).
Test: "Kerberoasting MITRE ID" → doğru **T1558.003** getirdi. Skill: `octopus-rag`.
Build torch ister → cyberm4fia venv ile koşulur. `retrieve()` serving'e hazır (model çalışırken bağlam ekle).

## ⚠️ v0.3 DENENDİ (2026-07-04) — hand-seed TAVANA ULAŞTI

87 Türkçe seed (61 + 26 bilgi-tabanlı cyber, ×20) ile retrain → son loss 0.80, ~$0.77. Adapter sha256
doğrulandı, `checkpoints_sft/octopus-8b-v3-adapter.tar.gz` (HF'ye YÜKLENMEDİ — v0.2 hâlâ en iyi).
**Sonuç: v0.2'den NET İYİ DEĞİL** — kimlik tutarlı ama "ó" pürüzü (Octórus), WiFi reddi daha dağınık +
v0.2'deki "yetkili olsaydı yardım ederdim" kalibrasyonunu kaybetti. **KANIT: el-yazımı seed + upsampling
Türkçe akıcılık/tutarlılık tavanına geldi.** Kök sebep değişmedi: %91 İngilizce Fenrir baskın.

**EN İYİ MODEL HÂLÂ v0.2** (`erkanrzgcc/octopus-8b-qlora`). v0.3 = deney/karşılaştırma checkpoint'i.

**▶️ GERÇEK sıradaki kaldıraçlar (kanıta dayalı):**
1. **Veri ÖLÇEĞİ** — binlerce Türkçe cyber Q&A (gerçek teacher-model distillation, el-yazımı değil).
   agentic-model `scripts/distill_teacher_tr.py` deseni + bir teacher (Qwen3-32B/235B ya da API).
2. **Oran dengesi** — Fenrir baskınlığını kır: ya Fenrir'i azalt ya bir kısmını Türkçeye çevir/damıt.
3. **Generation tuning** — serving'de düşük sıcaklık + iyi decoding (dağınıklığın bir kısmı sampling).
4. **GGUF → yerel çalıştır (v0.2) + RAG** — modeli KULLAN, faktüel doğruluğu RAG ver, gerçek zayıflığı gör.

Öneri: körlemesine 4. retrain yerine → (4) v0.2'yi RAG'la çalıştır/tune ET, ya da (1) gerçek distillation'a yatır.

## ⚠️ v0.4 REBALANCE DENENDİ (2026-07-04) — VERİ-MİX TAVANI KANITLANDI

Fenrir 99k→50k + InstrucTurca 10k→30k (Türkçe %9→%38) + seed×20 → son loss 0.92 (yükseldi=daha zor/çeşitli
veri). **Sonuç: Türkçe daha AKICI ama GUARDRAIL BOZULDU** — komşu-WiFi'de "yetkinizi anladım için evet"e
kaydı (güvenlik gerilemesi, kabul edilemez). Fenrir'i kısınca ret eğitimi + 4 ret-seed InstrucTurca'da eridi.
Pod silindi (indirilmedi — gerileme). Bakiye $10.06.

**4 TURUN SONUCU (v0.1→v0.4): EN İYİ HÂLÂ v0.2.** Her mix varyasyonu bir şeyi iyileştirip başkasını bozuyor:
v0.3 (cyber seed) ret'i dağıttı, v0.4 (rebalance) akıcılık verdi ama guardrail'i bozdu. **KANIT: Qwen3-8B QLoRA
+ bu veri havuzunda VERİ-MİX AYARININ TAVANINA geldik. Körlemesine 5. mix-retrain = para yakmak.**

**Gerçek untried kaldıraç (tek):** `data/sft/distill_tr.py` HAZIR — teacher (Qwen3-14B) RAG bilgi
tabanından BİNLERCE ÇEŞİTLİ Türkçe cyber Q&A üretir (upsample'lı 87 kopya değil, gerçek çeşitlilik).
Ya bu (v0.5, ~1.5-2sa pod) ya da **v0.2'yi SHIP et** (GGUF+RAG, yerelde kullan). "ó" pürüzü tüm sürümlerde
var → tokenizer-seviyesi (Qwen ó'yu böler); marka'da düz "Octopus" kabul en pragmatik çözüm olabilir.

**Referans çalışan pipeline:** `Desktop\cyberm4fiaModel` (Qwen2.5-3B QLoRA + Fenrir → loss 0.77/ppl 2.39 +
RAG + safety eval + 15-araç agent + Türkçe guardrail). Desen buradan alınır (kopya değil, uyarlama).

---

## ✅ HAZIR ALTYAPI (fine-tune'da da geçerli)

### RunPod (2026-06-20)
- `runpodctl` v2.5.0 kuruldu (WindowsApps, PATH'te), `runpodctl doctor` auth'lu. SSH `~/.ssh/id_ed25519`
  (octopus-runpod) hesaba ekli. **Asistan pod'u `runpodctl`+SSH ile sürebiliyor.**
- Pipeline uçtan uca kanıtlandı ($0.17): A4000 16GB SECURE, pod aç→SSH→kod→veri→eğit→checkpoint→sil.
  Runbook + dersler: **`cloud/RUNPOD.md`**. **Ders:** cache'li template `runpod-torch-v240` kullan (cold-pull
  takılır); Community boş→SECURE; `--terminate-after` = kaçak fatura koruması.
- **Bakiye ~$4.86.** Fine-tune QLoRA turu from-scratch'ten çok daha ucuz (~$3-15) → büyük yükleme şart değil.
  > ⚠️ 3 network volume $0.015/sa eritiyor — kullan ya da sil.

### HF (2026-06-20)
- **HF CLI** hazır (`uv run hf`, huggingface_hub 1.20.1), auth'lu (`erkanrzgcc`, write). Adaptör/model yüklenebilir.

---

## 📦 ARŞİV — from-scratch denemesi (aktif yolda DEĞİL, korunuyor)

> Bu bölüm tarihsel kayıt. From-scratch artefaktları silinmedi; gerekirse referans/deney. Strateji ADR 0002.

- **Faz 1 Tokenizer** ✅ `tokenizer/octopus-tr.model` — SentencePiece Unigram 32k, fertility **1.798 vs Qwen
  2.674 (-%33)**, diakritik/newline kayıpsız. (Not: fine-tune Qwen tokenizer'ını miras alır → bu kazanç aktif
  yolda kullanılmıyor.)
- **Faz 2 Veri** ✅ `data/clean.py` + `data/tokenize_corpus.py`; `data/bin/train.bin` (34.2M tok) + FineWeb-2-tr
  1B batch `data/bin/fineweb2_tr/` (10 shard). `data/build_corpus_mix.py` + reçeteler `data/recipes/octopus-v*.json`.
- **Faz 3 Model** ✅ `model/config.py` + `model/transformer.py` (nanoGPT-tarzı Llama, 100.1M param, overfit→0).
- **Faz 4 Eğitim** ✅ `train/pretrain.py` (bf16, cosine+warmup, grad-accum/ckpt, resume). `checkpoints_web/`
  = 100M web turu (loss 10.5→3.88'de durmuş, step ~2900). Yerel smoke ~23k tok/s (RTX 5060).

---

## Hatırlatma (değişmez kurallar)
- **Para harcayan her adımdan (RunPod tam tur) ÖNCE kullanıcıyla checkpoint.**
- API key/token = SIR: sohbete/`!` komutuna yapıştırma; auth'u kullanıcı kendi terminalinde koşar.
- Paket **uv**. Yetkili-kullanım guardrail (red+blue yalnızca lab/CTF/sahip-izinli); "Ben Octópus" persona.
- ó yalnızca markada/konuşmada; dosya yolları düz ASCII `octopus`.
