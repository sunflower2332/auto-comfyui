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
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system",
             "content": (
               "You are an expert prompt engineer for ComfyUI/Stable Diffusion. "
               "Combine the raw prompt into a single, clean prompt, Danbooru/tag based propmt. Example: woman, large breasts, narow waist, tall. Return the prompt only."
             )},
            {"role": "user", "content": raw},
        ],
        temperature=0.7,
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"✅ Wrote updated workflow to {path}")

def update_and_inject(input_path, output_path, prompt, realism, detail, seed=None):
    flow = load_json(input_path)

    # Debug print to confirm titles
    titles = [n.get("_meta",{}).get("title") for n in flow.values()]
    print("DEBUG node titles:", titles)

    # 1) Inject into the POS node
    for node in flow.values():
        if node.get("_meta",{}).get("title","").strip() == "POS":
            node["inputs"]["text"] = prompt
            break
    else:
        raise ValueError(f"No POS node found; found titles {titles}")

    # 2) Inject LoRA strengths
    for which, strength in (("Realism_LORA", realism),
                            ("Detail_LORA",  detail)):
        for node in flow.values():
            if node.get("_meta",{}).get("title","").strip() == which:
                node["inputs"]["strength"] = strength
                break
        else:
            raise ValueError(f"No node titled {which!r}; found titles {titles}")   
    
    # 3) Determine and inject seed into every KSampler
    #    Use provided seed or pick a new random one
    seed_value = seed if seed is not None else random.randint(0, 2**53 - 1)
    for node in flow.values():
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = seed_value

   # 4) Save _only_ the node map
    save_json(flow, output_path)
    return flow  # return the raw workflow dict

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
