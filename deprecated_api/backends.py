"""Original greedy backends and retry behavior, loaded only when requested."""

import os

from .annotation import CHAT_INSTRUCTION
from .config import IS_KAGGLE

DEEPSEEK_MODEL = "deepseek-ai/deepseek-coder-1.3b-instruct"
MAX_NEW_TOKENS = 50
GEMINI_PACING_SECS = 1.0
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_THINKING_LEVEL = "minimal"


def load_deepseek():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = DEEPSEEK_MODEL
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"loading {model_id} on {device} ({dtype})...")
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=dtype, trust_remote_code=True
    )
    model.to(device).eval()
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    return model, tok, device


def deepseek_generate(model, tok, device, prompt, mode, max_new_tokens=None, instruction=None):
    import time as _t

    import torch

    max_new_tokens = max_new_tokens or MAX_NEW_TOKENS
    instruction = instruction or CHAT_INSTRUCTION
    if mode == "raw":
        enc = tok(prompt, return_tensors="pt", add_special_tokens=True)
    else:
        msgs = [{"role": "user", "content": instruction.format(code=prompt)}]
        enc = tok.apply_chat_template(
            msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True
        )
    ids = enc["input_ids"].to(device)
    attn = enc["attention_mask"].to(device)
    started = _t.time()
    with torch.inference_mode():
        out = model.generate(
            input_ids=ids,
            attention_mask=attn,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            num_beams=1,
            pad_token_id=tok.pad_token_id,
            eos_token_id=tok.eos_token_id,
        )
    latency_ms = (_t.time() - started) * 1000
    new_tokens = out[0, ids.shape[1] :]
    text = tok.decode(new_tokens, skip_special_tokens=True)
    finish_reason = (
        "STOP"
        if (new_tokens.numel() > 0 and new_tokens[-1].item() == tok.eos_token_id)
        else "MAX_TOKENS"
    )
    return {
        "text": text,
        "finish_reason": finish_reason,
        "tok_in": int(ids.shape[1]),
        "tok_out": int(new_tokens.numel()),
        "tok_think": 0,
        "latency_ms": latency_ms,
    }


def load_gemini():
    from google import genai

    key = os.environ.get("GEMINI_API_KEY")
    if not key and IS_KAGGLE:
        from kaggle_secrets import UserSecretsClient

        key = UserSecretsClient().get_secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=key)


def gemini_generate(client, prompt, mode, max_new_tokens=None, instruction=None):
    import time as _t

    from google.genai import errors, types

    assert mode == "chat", "gemini supports mode='chat' only"
    max_new_tokens = max_new_tokens or MAX_NEW_TOKENS
    instruction = instruction or CHAT_INSTRUCTION
    model_id = os.environ.get("GEMINI_MODEL", GEMINI_MODEL)
    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=max_new_tokens,
        thinking_config=types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVEL),
    )
    content = instruction.format(code=prompt)
    for attempt in range(5):
        try:
            started = _t.time()
            resp = client.models.generate_content(model=model_id, contents=content, config=config)
            latency_ms = (_t.time() - started) * 1000
            cand = resp.candidates[0] if resp.candidates else None
            u = resp.usage_metadata
            result = {
                "text": resp.text or "",
                "finish_reason": str(cand.finish_reason) if cand else None,
                "tok_in": u.prompt_token_count if u else None,
                "tok_out": u.candidates_token_count if u else None,
                "tok_think": getattr(u, "thoughts_token_count", 0) if u else 0,
                "latency_ms": latency_ms,
            }
            if GEMINI_PACING_SECS:
                _t.sleep(GEMINI_PACING_SECS)
            return result
        except errors.APIError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            _t.sleep(2 * 2**attempt)
    raise RuntimeError("unreachable")


_loaded = {}


def get_generate_fn(model_name):
    if model_name not in _loaded:
        if model_name == "deepseek":
            m, t, d = load_deepseek()
            _loaded[model_name] = lambda prompt, mode, max_new_tokens=None, instruction=None: (
                deepseek_generate(m, t, d, prompt, mode, max_new_tokens, instruction)
            )
        elif model_name == "gemini":
            client = load_gemini()
            _loaded[model_name] = lambda prompt, mode, max_new_tokens=None, instruction=None: (
                gemini_generate(client, prompt, mode, max_new_tokens, instruction)
            )
        else:
            raise ValueError(f"unknown model {model_name!r}")
    return _loaded[model_name]
