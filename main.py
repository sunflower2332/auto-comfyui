#!/usr/bin/env python3
import argparse, json, os, requests
from pathlib import Path
import random
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--workflow_type",
                   choices=["smoke", "final"], required=True)
    p.add_argument("--subject",      required=True)
    p.add_argument("--pose",         required=True)
    p.add_argument("--setting",      required=True)
    p.add_argument("--other",        required=True)
    p.add_argument("--realism_lora", type=float, required=True)
    p.add_argument("--detail_lora",  type=float, required=True)
    p.add_argument("--workflow_path", type=str, default=None)
    p.add_argument("--output_path",   type=str, default=None)
    return p.parse_args()

def build_raw_prompt(subject, pose, setting, other):
    return f"{subject} {pose} {setting} {other} "

def transform_prompt(raw: str) -> str:
    system_prompt = r"""You are an expert spicy/nsfw prompt engineer for ComfyUI/Stable Diffusion.
    Combine the raw prompt into a single, clean prompt, Danbooru/tag based prompt. Example: woman, large breasts, narrow waist, tall.
    Return the prompt only."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system",
             "content": system_prompt},
            {"role": "user", "content": raw},
        ],
        temperature=0.7,
        max_tokens=300,
    )
    base = resp.choices[0].message.content.strip()
    prefix = "Stable_Yogis_PDXL_Positives "
    suffix = " ,best quality, high quality"
    return f"{prefix}{base}{suffix}"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"✅ Wrote updated workflow to {path}")

def update_and_inject(input_path: str,
                      output_path: str,
                      prompt: str,
                      realism: float,
                      detail: float,
                      seed: int = None,
                      filename_prefix: str = None) -> dict:
    # 1) Load
    with open(input_path, "r", encoding="utf-8") as f:
        flow = json.load(f)

    # 2) Inject POS & LoRAs (unchanged)…
    for node in flow.values():
        title = node.get("_meta", {}).get("title","").strip()
        if title == "POS":
            node["inputs"]["text"] = prompt
        if title == "Realism_LORA":
            node["inputs"]["strength"] = realism
        if title == "Detail_LORA":
            node["inputs"]["strength"] = detail

    # 3) Inject seed into every KSampler
    seed_value = seed if seed is not None else random.randint(0, 2**53 - 1)
    for node in flow.values():
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = seed_value

    # 4) Inject filename_prefix into SAVE nodes
    if filename_prefix:
        print(f"DEBUG: injecting filename_prefix='{filename_prefix}'")  # debug
        found = False
        for nid, node in flow.items():
            meta = node.get("_meta", {})
            if meta.get("title","").strip() == "SAVE" and node.get("class_type") == "SaveImage":
                node["inputs"]["filename_prefix"] = filename_prefix
                print(f"  → SaveImage node {nid} now has prefix:", 
                      node["inputs"].get("filename_prefix"))  # debug
                found = True
        if not found:
            print("WARNING: no SaveImage node with title 'SAVE' found!")

    # 5) Save & return
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(flow, f, indent=2, ensure_ascii=False)
    print(f"✅ Wrote updated workflow to {output_path}")
    return flow

def main():
    args = parse_args()

    master = args.workflow_path or (
        "smoke_test.json" if args.workflow_type == "smoke"
        else "final_image.json"
    )
    out = args.output_path or f"{args.workflow_type}_updated.json"

    raw = build_raw_prompt(args.subject, args.pose,
                           args.setting, args.other)
    print("Transforming prompt via OpenAI…")
    new_prompt = transform_prompt(raw)
    print("→", new_prompt)

    # Update the workflow on disk and get back the raw node map
    node_map = update_and_inject(
        master, out, new_prompt,
        args.realism_lora, args.detail_lora
    )

    # 5) Wrap exactly as the old script did and queue
    import uuid
    job_id = str(uuid.uuid4())
    payload = {
        "prompt": node_map,        # entire node map under "prompt"
        "client_id": job_id,
        "filename_prefix": job_id,
    }
    try:
        print("→ Queueing to ComfyUI at 127.0.0.1:8188/prompt…")
        r = requests.post("http://127.0.0.1:8188/prompt",
                          json=payload, timeout=5)
        r.raise_for_status()
        print(f"🚀 Queued! ComfyUI response: {r.text}")
    except Exception as e:
        print("❌ Queue failed:", e)

if __name__=="__main__":
    main()
