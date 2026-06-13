"""
qlora.py — QLoRA fine-tuning of Qwen2.5-7B on your RTX 4070 (12GB) (Phase 8).

This is the deep lever: it changes the WEIGHTS (the one gap a harness can't close).
4-bit QLoRA fits a 7B in 12GB. It does NOT run until you install the training deps
and commit ~1-3 GPU-hours — it's gated with a clear message so nothing breaks before
then.

Setup (when ready):
  pip install torch transformers peft trl bitsandbytes accelerate datasets
  python -m forge.factory.generate --n 200     # build data
  python -m forge.train.prepare                 # -> data/train/*.jsonl
  python -m forge.train.qlora                   # train -> adapters/

Promotion is EVAL-GATED elsewhere: a new adapter only becomes the default if it beats
the current model on the held-out HumanEval split. Keep the base as fallback.
"""
from __future__ import annotations

import argparse
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "train" / "train.jsonl"
OUT = Path(__file__).resolve().parent.parent.parent / "adapters"

# 12GB-friendly defaults for a 7B at 4-bit.
DEFAULTS = dict(
    base_model="Qwen/Qwen2.5-7B-Instruct",
    lora_r=16, lora_alpha=32, lora_dropout=0.05,
    lr=2e-4, epochs=2, batch_size=1, grad_accum=8,
    max_seq_len=1024, warmup_ratio=0.03,
)


def _check_deps() -> str | None:
    missing = []
    for mod in ("torch", "transformers", "peft", "trl", "bitsandbytes", "datasets"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    return None if not missing else (
        "Training deps not installed: " + ", ".join(missing) +
        "\nInstall: pip install torch transformers peft trl bitsandbytes accelerate datasets")


def train(cfg: dict):
    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)
    from trl import SFTConfig, SFTTrainer

    if not DATA.exists():
        raise SystemExit(f"No training data at {DATA}. Run: python -m forge.train.prepare")

    tok = AutoTokenizer.from_pretrained(cfg["base_model"])
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_use_double_quant=True)
    # pin everything to GPU 0 — don't silently offload to CPU (bnb-4bit can't),
    # and fail loudly if it doesn't fit instead of crashing deep in the loader.
    model = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"], quantization_config=bnb, device_map={"": 0},
        dtype=torch.bfloat16)
    peft_cfg = LoraConfig(
        r=cfg["lora_r"], lora_alpha=cfg["lora_alpha"], lora_dropout=cfg["lora_dropout"],
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])

    ds = load_dataset("json", data_files=str(DATA), split="train")

    def fmt(row):
        return {"text": tok.apply_chat_template(row["messages"], tokenize=False)}
    ds = ds.map(fmt, remove_columns=ds.column_names)

    OUT.mkdir(parents=True, exist_ok=True)
    args = SFTConfig(
        output_dir=str(OUT), num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=cfg["batch_size"],
        gradient_accumulation_steps=cfg["grad_accum"],
        learning_rate=cfg["lr"], warmup_ratio=cfg["warmup_ratio"],
        max_length=cfg["max_seq_len"], logging_steps=5,
        save_strategy="epoch", bf16=True, optim="paged_adamw_8bit",
        report_to="none")
    trainer = SFTTrainer(model=model, args=args, train_dataset=ds,
                         peft_config=peft_cfg, processing_class=tok)
    trainer.train()
    trainer.save_model(str(OUT))
    print(f"\nDone. Adapter -> {OUT}")
    print("Next: merge + export to GGUF, then `ollama create` to serve your own model.")
    print("Then re-run: python cli.py humaneval --limit 164  (eval-gated promotion)")


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=v)
    a = vars(ap.parse_args())

    problem = _check_deps()
    if problem:
        print(problem)
        print("\n(Scaffold is ready; this is the only step that needs the extra deps + GPU time.)")
        return
    train(a)


if __name__ == "__main__":
    main()
