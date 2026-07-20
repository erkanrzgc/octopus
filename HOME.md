# 🐙 Octópus — Vault HOME

> Türkçe-öncelikli siber güvenlik LLM'i. Bu not, Obsidian vault'unun **haritası** (MOC).
> Graph view + backlinks ile gezinin. Wikilink'ler dosya-adıyla çözülür.

## Vizyon & sözleşme
- [[OCTOPUS]] — ürün vizyonu
- [[CLAUDE]] — proje notları (her oturum otomatik yüklenir)
- [[README]]

## Kararlar (ADR)
- [[0001-from-scratch-turkish-first]]
- [[0002-pivot-to-finetuning]]
- [[0003-pivot-to-turkish-gemma-bf16]]

## Aktif faz — "büyük hamle" veri genişletme (tek retrain → v0.8)
Tek kaynak sıra: [[v0.7-loop-queue]]

| Faz | Konu | Durum |
|---|---|---|
| A | hedef dengeleme | ✅ |
| B / B1–B3 | araç + asistan + deep-research grounding | ✅ |
| C | domain derinliği | ✅ |
| D1 | reasoning (```dusunce```) | ✅ (ölçüm kapısı retrain'de) |
| D2 | hafıza (save/recall) | ✅ |
| **D3** | **skill/metodoloji** | ⏳ spec ✅ · veri sürüyor |
| 💰 v0.8 | tek retrain | DUR (para-checkpoint) |

## Faz tasarımları (spec)
- [[2026-07-18-phase-d-reasoning-memory-skill-design]] — Faz D decomposition
- [[2026-07-19-d2-memory-tools-design]]
- [[2026-07-20-d3-skill-methodology-design]] — **yeni araç YOK; iskeleti içselleştir, gövdeyi çek**

## Referans kataloglar
- [[v0.7-data-catalog]] · [[v0.7-tools-catalog]] · [[v0.7-hf-cyber-datasets-full]]
- [[skills-and-subagents]]

## Beceri (skill) & metodoloji hazinesi
- `.claude/skills/` — octopus-data · octopus-finetune · octopus-eval · octopus-rag
- `rag/knowledge/methodologies/` — 55+ metodoloji playbook (D3 kaynağı)
