# Octópus — Skill & Subagent Rehberi

> "Skill olayını subagent olayını netleştirelim" — bu doküman ikisini açıklar ve Octópus fine-tune
> workflow'una eşler. Proje skill'leri: `.claude/skills/`. Global agent'lar: `~/.claude/agents/` (ECC paketi).

## Fark (özet)
- **🧩 Skill = TARİF / bilgi.** Bir `.md` reçetesi; tetiklenince **mevcut oturumun context'ine** yüklenir,
  yeni biri doğmaz. "Şu işi HER ZAMAN şöyle yap." Ucuz, deterministik, senin konvansiyonun. → `.claude/skills/`.
- **🤖 Subagent = İŞÇİ / izolasyon.** Temiz context'le doğan taze bir Claude; dar görev alır, tool koşar,
  **sadece özet** döner. Değer: context izolasyonu + paralellik + uzmanlık. Maliyet: soğuk başlar (pahalı).
- **Kural:** Skill = *nasıl* (in-context, ucuz). Subagent = *git yap & rapor et* (izole, pahalı). Bir skill,
  "şu subagent'ı çağır" diyebilir → birlikte çalışırlar.

## Octópus proje skill'leri (kurulu)
| Skill | Ne zaman | Ne yapar |
|---|---|---|
| `octopus-data` | SFT veri lazım | Türkçe+siber kaynakları `messages`'a normalize + persona + dedup + split |
| `octopus-finetune` | modeli eğit | QLoRA (Qwen3-8B, Unsloth) veri→train→eval→merge→GGUF + para-checkpoint |
| `octopus-eval` | eğitim bitti | ppl + safety/balance + brittleness red-team |

## Subagent haritası (mevcut global agent'ları kullan — yeni icat etme)
| Durum | Agent | Neden |
|---|---|---|
| Eğitim çöktü (CUDA/tensor/OOM/DataLoader) | `pytorch-build-resolver` | izole context'te düzeltir, ana kafayı kirletmez |
| Python kod kalitesi | `python-reviewer` | pipeline kodu review |
| Güvenlik / persona guardrail şüphesi | `security-reviewer` | red+blue guardrail, secret sızıntısı |
| Geniş keşif / kod arama / araştırma | `Explore` veya `general-purpose` | fan-out arama context izolasyonu için |
| Build/bağımlılık hatası (torch/unsloth) | `build-error-resolver` | hızlı yeşile getir |

> **Paralellik:** bağımsız işleri aynı mesajda paralel dispatch et (ör. veri hazırlanırken kod review).
> **Özel agent SADECE gerçek boşlukta** yazılır (ör. Octópus'a özgü otomatik değerlendirici) — şu an YOK, gerekmiyor.

## Ne zaman hangisi? (pratik)
- Tekrarlanan, konvansiyon-taşıyan iş (eğitim reçetesi, veri şekli) → **skill**.
- Bağlamı kirletecek ağır/izole/paralel iş (hata ayıklama, geniş arama) → **subagent**.
- İkisi birlikte: `octopus-finetune` skill'i eğitim çökmesinde `pytorch-build-resolver` subagent'ını önerir.
