# RunPod Runbook — Octópus eğitim turu

> **DOĞRULANMIŞ** (2026-06-20): A4000 16GB SECURE'da 200M model uçtan uca eğitildi, $0.17.
> Aşağıdaki komutlar gerçek bir turda çalıştı. Asistan pod'a `runpodctl` + SSH ile erişir.

## Öğrenilen kritik dersler (tekrar yaşamamak için)

1. **CACHE'Lİ image kullan** — yeni/nadir image (ör. `torch291-cu1290`) cold-pull'da takılır
   (uptime 0, SSH hiç hazır olmaz). RunPod resmi **template**'i kullan: `--template-id runpod-torch-v240`
   (torch 2.4.0, makinelerde hazır → ~40s'de SSH hazır).
2. **Community sık boş** ("no instances available") → **SECURE** cloud daha güvenilir (A4000 ~$0.25/sa).
3. **Windows SSH key izni:** OpenSSH "bad permissions" derse → `icacls <key> /grant:r "<user>:F"` + `/inheritance:r`.
4. **`--terminate-after <ISO-UTC>`** koy → unutsan bile pod kendini kapatır (kaçak fatura yok).
5. Checkpoint büyük: 200M → 2.56GB (model+optimizer). 0.5B → ~5.5GB, 1B → ~11GB. İndirme süresini planla
   (veya sadece model ağırlığını kaydet).

## 0. Önkoşullar (bir kez, yerelde)

```powershell
# runpodctl kurulu (WindowsApps'te). API key (GİZLİ — kendi terminalinde):
runpodctl doctor                      # key'i prompt'a yapıştır → ~/.runpod/config.toml
# SSH anahtarı üret + hesaba ekle:
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N '' -C octopus-runpod
runpodctl ssh add-key --key-file "$env:USERPROFILE\.ssh\id_ed25519.pub"
icacls "$env:USERPROFILE\.ssh\id_ed25519" /grant:r "$(whoami):F"; icacls "$env:USERPROFILE\.ssh\id_ed25519" /inheritance:r
runpodctl me                          # bakiye kontrol (0.5B turu için ~$60 yükle)
```

## 1. Pod aç (💰 burada başlar)

```powershell
$term = (Get-Date).ToUniversalTime().AddHours(8).ToString("yyyy-MM-ddTHH:mm:ssZ")  # güvenlik limiti
runpodctl pod create --name octopus-train --gpu-id "NVIDIA RTX A5000" --cloud-type SECURE `
  --template-id runpod-torch-v240 --terminate-after $term
# boşsa dene: "NVIDIA RTX A4500" / "NVIDIA RTX A6000" / "NVIDIA RTX A4000"
# çok-GPU (DDP): --gpu-count 4
```
Pod ID + SSH bilgisi:
```powershell
runpodctl ssh info <POD_ID> -v        # ip + port + ssh_command döner (RUNNING+hazır olunca)
```

## 2. Kod transfer + kurulum

```powershell
# tarball (sadece scriptler + tokenizer; veri pod'da üretilir)
tar -czf octopus_code.tgz --exclude=data/bin --exclude=data/corpus --exclude=*/__pycache__ model train eval data tokenizer/octopus-tr.model
$k="$env:USERPROFILE\.ssh\id_ed25519"; $H="root@<IP>"; $P=<PORT>
scp -i $k -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -P $P octopus_code.tgz "${H}:/workspace/"
ssh -i $k -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -p $P $H 'cd /workspace && tar -xzf octopus_code.tgz && pip install -q sentencepiece datasets'
```

## 3. Veri üret (pod'da, ~1M tok/s)

```powershell
# 0.5B için ~15B token (Chinchilla ~30/param). Disk: 2 byte/token → 30GB. container-disk ayarla!
ssh ... $H 'cd /workspace && python -m data.build_pretrain_data --max-tokens 15000000000 --out-dir data/bin/fineweb2_tr'
```

## 4. Eğit

```powershell
# tek GPU:
ssh ... $H 'cd /workspace && python -m train.pretrain --data-dir data/bin/fineweb2_tr --out-dir ckpt \
  --preset octopus-500m --max-steps 60000 --warmup 1000 --lr 4e-4 --min-lr 4e-5 \
  --batch-size 8 --grad-accum 8 --eval-interval 1000 --sample-interval 2000 --save-interval 2000'
# çok-GPU (N kart, Linux NCCL):
ssh ... $H 'cd /workspace && torchrun --nproc_per_node=4 -m train.pretrain --data-dir data/bin/fineweb2_tr ...'
# büyük model 24GB'a sığmazsa: --optim adamw8bit --grad-checkpoint  (önce: pip install bitsandbytes)
```
İzleme (ayrı SSH): `ssh ... $H 'tail -f /workspace/ckpt/log.jsonl'`

## 5. Checkpoint indir → POD SİL (💰 burada biter)

```powershell
scp -i $k -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -P $P "${H}:/workspace/ckpt/ckpt_best.pt" ./
runpodctl pod delete <POD_ID>         # ZORUNLU — billing'i durdurur
runpodctl pod list                    # boş olduğunu doğrula
```

## Maliyet pusulası (FLOP = 6·N·D, ~40 TFLOPS eff A5000-sınıfı)
- 200M / 4B tok ≈ $9 · **0.5B / 15B tok ≈ $110 1×A5000 / ~$57 ucuz-GPU** · 1B / 30B tok ≈ $190-440
- Çok-GPU süreyi böler, GPU-saat maliyeti ~sabit. `--cost` yok (modern create); GPU seçimi fiyatı belirler.
