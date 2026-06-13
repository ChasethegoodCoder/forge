"""
hf_backend.py — run a fine-tuned model directly via transformers (Phase 8 eval-gate).

After QLoRA produces a LoRA adapter, we must answer one question honestly: did it
actually get BETTER? This backend loads the base model + the adapter and implements the
same Backend.chat interface as Ollama, so the EXACT benchmark runs on the fine-tuned
model. No GGUF conversion needed to evaluate — that comes later, only if it wins.

  from forge.hf_backend import HFBackend
  be = HFBackend(adapter="adapters")          # base + your adapter
  # then: bench/humaneval can score it like any backend

Heavy: loads a 7B in 4-bit (~5–6 GB VRAM). Only import when you actually eval/train.
"""
from __future__ import annotations

from .backend import Backend, GenConfig, Message


class HFBackend(Backend):
    def __init__(self, base_model: str = "Qwen/Qwen2.5-7B-Instruct",
                 adapter: str | None = None, load_4bit: bool = True):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.name = f"hf:{base_model}" + (f"+{adapter}" if adapter else "")
        self.tok = AutoTokenizer.from_pretrained(base_model)
        kw = dict(device_map="auto", dtype=torch.bfloat16)
        if load_4bit:
            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        self.model = AutoModelForCausalLM.from_pretrained(base_model, **kw)
        if adapter:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter)
        self.model.eval()

    def chat(self, messages: list[Message], cfg: GenConfig) -> str:
        import torch
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        inputs = self.tok.apply_chat_template(
            msgs, add_generation_prompt=True, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                inputs, max_new_tokens=cfg.max_tokens,
                temperature=max(cfg.temperature, 1e-4), top_p=cfg.top_p,
                do_sample=cfg.temperature > 0, pad_token_id=self.tok.eos_token_id)
        return self.tok.decode(out[0][inputs.shape[1]:], skip_special_tokens=True)
