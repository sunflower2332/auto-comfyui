import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="ComfyUI Workflow Queue Backend")
    parser.add_argument("--subject", type=str, required=True, help="Subject description")
    parser.add_argument("--pose", type=str, required=True, help="Pose description")
    parser.add_argument("--setting", type=str, required=True, help="Setting description")
    parser.add_argument("--other", type=str, required=True, help="Other description")
    parser.add_argument("--realism_lora", type=float, required=True, help="Realism LoRA weight")
    parser.add_argument("--detail_lora", type=float, required=True, help="Detail LoRA weight")
    return parser.parse_args()


def build_prompt(subject, pose, setting, other):
    """
    Concatenate the four string inputs with a space after each.
    """
    # Adds a trailing space after all parts
    return f"{subject} {pose} {setting} {other} "


def main():
    # Parse inputs (placeholder for frontend integration)
    args = parse_args()

    # Build the prompt from string inputs
    prompt = build_prompt(args.subject, args.pose, args.setting, args.other)

    # Store the LoRA weights for later use
    realism_lora = args.realism_lora
    detail_lora = args.detail_lora

    # Output for verification
    print("Generated prompt:", prompt)
    print("Realism LoRA weight:", realism_lora)
    print("Detail LoRA weight:", detail_lora)

    # TODO: Integrate with OpenAI API for prompt translation/refinement
    # TODO: Queue workflow executions via backend service


if __name__ == "__main__":
    main()
