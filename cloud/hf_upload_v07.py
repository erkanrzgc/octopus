"""v0.7 adapter'i HF'ye yukle (sağlam, loglu, tekrar-denemeli).
Yerel dizin -> erkanrzgcc/octopus-gemma-v0.7 (private). upload_folder atomic + retry'li."""
import sys, time, traceback
from huggingface_hub import HfApi

REPO = "erkanrzgcc/octopus-gemma-v0.7"
LOCAL = "checkpoints_sft/octopus-gemma-v7-adapter"

api = HfApi()
print(f"[{time.strftime('%H:%M:%S')}] START upload {LOCAL} -> {REPO}", flush=True)
for attempt in range(1, 6):
    try:
        api.upload_folder(
            folder_path=LOCAL,
            repo_id=REPO,
            repo_type="model",
            commit_message=f"v0.7 LoRA adapter (bf16, r=32) - attempt {attempt}",
        )
        print(f"[{time.strftime('%H:%M:%S')}] UPLOAD_OK attempt={attempt}", flush=True)
        break
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ATTEMPT {attempt} FAIL: {e!r}", flush=True)
        traceback.print_exc()
        if attempt == 5:
            print("UPLOAD_GIVEUP", flush=True)
            sys.exit(1)
        time.sleep(15)

# dogrula
info = api.model_info(REPO, files_metadata=True)
print("=== REPO FILES ===", flush=True)
ok = False
for s in info.siblings:
    print(f"  {s.rfilename}  {getattr(s,'size',None)}", flush=True)
    if s.rfilename == "adapter_model.safetensors" and getattr(s, "size", 0) == 432223744:
        ok = True
print("VERIFY_OK" if ok else "VERIFY_FAIL", flush=True)
sys.exit(0 if ok else 2)
