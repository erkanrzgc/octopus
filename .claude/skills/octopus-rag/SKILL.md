---
name: octopus-rag
description: Use when grounding Octópus answers with retrieval (RAG) over the Türkçe MITRE/CVE/OWASP knowledge base — building the Chroma index or wiring retrieval into serving so the model cites correct IDs instead of hallucinating. Triggers on "RAG", "bilgi tabanı", "MITRE/CVE getir", "halüsinasyon", "grounding".
---

# Octópus RAG (Türkçe bilgi grounding)

Küçük modelin uydurmasını (yanlış CVE/MITRE ID) keser: `rag/knowledge/*.md` (Türkçe, doğru ID'ler) →
chunk → embedding → Chroma. Sorguda ilgili parçalar getirilip cevaba **bağlam** olarak eklenir.
Yeniden EĞİTİM gerektirmez — serving-zamanı katman. cyberm4fia RAG deseninden port edildi.

## Bilgi tabanı (`rag/knowledge/`, 18 dosya, Türkçe)
MITRE ATT&CK, OWASP Top 10, notable CVE, AD saldırıları, Kerberoasting, privesc, reverse shells,
web attacks, cloud/container/k8s, malware, IR/SOC, threat intel, pentest tools, Log4Shell + methodologies/.
Genişletmek: `rag/knowledge/`'e yeni `.md` ekle, sonra `--build`.

## Kurulum + build (torch gerekir → cyberm4fia venv, Octópus .venv 3.14 değil)
```bash
CY=C:/Users/erkanrzgc/Desktop/cyberm4fiaModel/.venv/Scripts/python.exe
"$CY" -m pip install chromadb sentence-transformers   # bir kez (kurulu)
"$CY" rag/build_rag.py --build                         # index kur -> rag/chroma (784 parça)
"$CY" rag/build_rag.py --query "Kerberoasting MITRE ID"  # test
```
Embedding: `all-MiniLM-L6-v2` (hafif). Koleksiyon: `octopus_kb`.

## Serving entegrasyonu (model çalıştırırken)
`build_rag.retrieve(soru, k=4)` → en yakın k parçayı döndürür. Akış:
1. Kullanıcı sorusu → `retrieve()` ile ilgili bilgi parçalarını çek.
2. System/context'e ekle: "Aşağıdaki doğrulanmış bilgiye dayan (kaynak: ...): {parçalar}".
3. Modeli (v0.2 adapter, unsloth ya da GGUF) bu bağlamla çağır → doğru ID'lerle Türkçe cevap.
> Grounding'i yalnız faktüel sorularda kullan; sohbet/persona sorularında gereksiz.
```
