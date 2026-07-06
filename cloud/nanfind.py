"""Egitim-modu per-ornek NaN bulucu — gercek egitim sayisalini (train mode + grad-checkpoint
+ LoRA + forward+backward) tekrarlayip ILK nan ureten ornegi yakalar. Eval-artefakti degil.
Kosul: /workspace/octopus-v7'de `python cloud/nanfind.py`."""
import sys
sys.path.insert(0, ".")
import torch
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from data.sft.normalize import flatten_tool_messages

B = "ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"
tok = AutoTokenizer.from_pretrained(B)
m = AutoModelForCausalLM.from_pretrained(
    B, torch_dtype=torch.bfloat16, device_map="cuda", attn_implementation="eager")
m.config.use_cache = False
m.gradient_checkpointing_enable()
m.enable_input_require_grads()
m = get_peft_model(m, LoraConfig(
    r=32, lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.0, bias="none", task_type="CAUSAL_LM"))
m.train()

rows = [json.loads(l) for l in open("data/sft/train.jsonl", encoding="utf-8")]
print(f"EGITIM-MODU nan taramasi: {len(rows)} ornek", flush=True)


def _user(o):
    for x in o["messages"]:
        if x["role"] == "user":
            return x["content"][:70]
    return "?"


found = False
for i, o in enumerate(rows):
    ids = tok.apply_chat_template(flatten_tool_messages(o["messages"]),
                                  tokenize=True, return_tensors="pt").to("cuda")
    m.zero_grad()
    out = m(ids, labels=ids)
    loss = out.loss
    lf = loss.item()
    roles = [x["role"] for x in o["messages"]]
    if lf != lf or lf == float("inf") or lf > 50:
        print(f"!!! FORWARD-NAN index {i} loss={lf} roller={roles} user={_user(o)!r}", flush=True)
        found = True
        break
    loss.backward()
    bad = False
    for p in m.parameters():
        if p.grad is not None:
            g = p.grad.detach()
            if torch.isnan(g).any() or torch.isinf(g).any():
                bad = True
                break
    if bad:
        print(f"!!! BACKWARD-NAN-GRAD index {i} loss={lf:.3f} roller={roles} user={_user(o)!r}", flush=True)
        found = True
        break
    if i % 100 == 0:
        print(f"{i} temiz (loss={lf:.3f})", flush=True)

if not found:
    print("TUM ORNEKLER TEMIZ (tekil forward+backward) -> sorun batch-etkilesimi/optimizer/scheduler", flush=True)
print("NANFIND_DONE", flush=True)
