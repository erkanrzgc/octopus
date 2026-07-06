"""Egitimle BIREBIR ayni backward-testi (use_reentrant=False!). Suphesi yuksek kaynaklari
(yeni distill_v07 + seed_tr) persona-system uygulayarak tek tek forward+backward gecip
ILK nan-gradyan ureten ornegi yakalar. Kosul: /workspace/octopus-v7'de `python cloud/nanfind2.py`."""
import sys
sys.path.insert(0, ".")
import glob
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from data.sft.normalize import apply_octopus_system, flatten_tool_messages, to_messages, is_valid

B = "ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"
tok = AutoTokenizer.from_pretrained(B)
m = AutoModelForCausalLM.from_pretrained(
    B, torch_dtype=torch.bfloat16, device_map="cuda", attn_implementation="eager")
m.config.use_cache = False
# EGITIMLE AYNI: use_reentrant=False
m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
m.enable_input_require_grads()
m = get_peft_model(m, LoraConfig(
    r=32, lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.0, bias="none", task_type="CAUSAL_LM"))
m.train()


def load(path):
    out = []
    for l in open(path, encoding="utf-8"):
        l = l.strip()
        if not l:
            continue
        msgs = to_messages(json.loads(l))
        if is_valid(msgs):
            out.append(apply_octopus_system(msgs))  # persona ekle (egitimdeki gibi)
    return out


suspects = []
# once yeni v07 (prime suspect), sonra seed
for f in sorted(glob.glob("data/sft/distilled/*v07*.jsonl")) + sorted(glob.glob("data/sft/seed_tr/*.jsonl")):
    ex = load(f)
    suspects.append((f, ex))
    print(f"yuklendi: {f} -> {len(ex)} ornek", flush=True)

found = False
for fname, exs in suspects:
    for i, msgs in enumerate(exs):
        ids = tok.apply_chat_template(flatten_tool_messages(msgs), tokenize=True,
                                      return_tensors="pt").to("cuda")
        m.zero_grad()
        loss = m(ids, labels=ids).loss
        lf = loss.item()
        if lf != lf or lf == float("inf") or lf > 50:
            u = next((x["content"][:80] for x in msgs if x["role"] == "user"), "?")
            print(f"!!! FORWARD-NAN {fname}#{i} loss={lf} user={u!r}", flush=True)
            found = True
            break
        loss.backward()
        bad = any(p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any())
                  for p in m.parameters())
        if bad:
            u = next((x["content"][:80] for x in msgs if x["role"] == "user"), "?")
            print(f"!!! BACKWARD-NAN {fname}#{i} loss={lf:.3f} user={u!r}", flush=True)
            found = True
            break
    if found:
        break
    print(f"{fname}: TUM ornekler temiz", flush=True)

if not found:
    print("SUPHELILERIN HEPSI TEMIZ -> sorun baska yerde (918-distill veya batch/optimizer)", flush=True)
print("NANFIND2_DONE", flush=True)
