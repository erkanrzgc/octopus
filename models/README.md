# models/ — local Octópus v0.7 GGUF (git-ignored artifacts)

The Q4 GGUF and the tokenizer dir are produced by `cloud/pod_gguf_v7.sh` on RunPod and are **not**
committed (too large). Only `Modelfile` and this README are tracked.

## One-off local setup (after downloading the pod outputs into this folder)

    models/
      octopus-v7-Q4_K_M.gguf      # ~5.5 GB, from the pod
      octopus-v7-tokenizer/       # tokenizer_config.json + tokenizer.model + special_tokens_map.json
      Modelfile                   # tracked

    ollama create octopus-v7 -f models/Modelfile
    python -m agent.cli --gguf     # real Octópus drives the loop (mock nmap hands)

The backend applies the training chat template itself and calls Ollama in raw mode, so the Modelfile
carries no TEMPLATE/SYSTEM directive.
