#!/usr/bin/env python3
import argparse
import json
import os
import openai

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"  # or another ChatCompletion-capable model

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Update a ComfyUI workflow with a transformed prompt + LoRA strengths"
    )
    p.add_argument(
        "--workflow_type",
        choices=["smoke", "final"],
        required=True,
        help="Which JSON workflow to update: 'smoke' for smoke_test.json or 'final' for final_image.json",
    )
    p.add_argument(
        "--subject", type=str, required=True, help="Subject text"
    )
    p.add_argument(
        "--pose", type=str, required=True, help="Pose description"
    )
    p.add_argument(
        "--setting", type=str, required=True, help="Setting description"
    )
    p.add_argument(
        "--other", type=str, required=True, help="Other details"
    )
    p.add_argument(
        "--realism_lora", type=float, required=True, help="Strength for Realism_LORA"
    )
    p.add_argument(
        "--detail_lora", type=float, required=True, help="Strength for Detail_LORA"
    )
    p.add_argument(
        "--workflow_path",
        type=str,
        default=None,
        help="Optional path override for the workflow JSON",
    )
    return p.parse_args()

# -----------------------------------------------------------------------------
# Prompt Building & Transformation
# -----------------------------------------------------------------------------
def build_raw_prompt(subject, pose, setting, other):
    """Concatenate each string with a trailing space."""
    return f"{subject} {pose} {setting} {other} "

def transform_prompt_with_openai(raw_prompt: str) -> str:
    """
    Call OpenAI to turn the concatenated prompt into one seamless
    ComfyUI-style prompt.
    """
    system_msg = (
        "You are an expert prompt engineer for ComfyUI/Stable Diffusion. "
        "Take the user's raw prompt pieces and output a single, "
        "well-formatted positive prompt string suitable for ComfyUI's CLIPTextEncode node."
    )
    user_msg = (
        "Here are the raw prompt pieces:\n\n"
        f"{raw_prompt}\n\n"
        "Please return just the combined, clean prompt."
    )

    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()

# -----------------------------------------------------------------------------
# Workflow JSON Handling
# -----------------------------------------------------------------------------
def load_workflow(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_workflow(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved updated workflow to {path}")

# -----------------------------------------------------------------------------
# Node Updates
# -----------------------------------------------------------------------------
def update_prompt_node(flow: dict, new_prompt: str):
    for node in flow.get("nodes", []):
        meta = node.get("_meta", {})
        if meta.get("title") == "POS":
            # assume the node input key is "text"
            node["inputs"]["text"] = new_prompt
            return
    raise ValueError("No node titled 'POS' found")

def update_lora_strength(flow: dict, lora_title: str, strength: float):
    for node in flow.get("nodes", []):
        meta = node.get("_meta", {})
        if meta.get("title") == lora_title:
            # assume the node input key is "strength"
            node["inputs"]["strength"] = strength
            return
    raise ValueError(f"No node titled '{lora_title}' found")

def update_workflow(path: str, prompt: str, realism: float, detail: float):
    flow = load_workflow(path)
    update_prompt_node(flow, prompt)
    update_lora_strength(flow, "Realism_LORA", realism)
    update_lora_strength(flow, "Detail_LORA", detail)
    save_workflow(flow, path)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    args = parse_args()

    # Determine which workflow file to use
    if args.workflow_path:
        workflow_file = args.workflow_path
    else:
        workflow_file = (
            "smoke_test.json" if args.workflow_type == "smoke"
            else "final_image.json"
        )

    # 1) Build raw concatenated prompt
    raw = build_raw_prompt(
        args.subject, args.pose, args.setting, args.other
    )

    # 2) Transform via OpenAI
    print("Transforming prompt via OpenAI...")
    new_prompt = transform_prompt_with_openai(raw)
    print("→ Transformed prompt:", new_prompt)

    # 3) Update workflow JSON
    update_workflow(
        workflow_file,
        new_prompt,
        args.realism_lora,
        args.detail_lora,
    )

if __name__ == "__main__":
    main()
