from flask import Flask, render_template, request, jsonify
import requests

# Import the pieces from main.py
from main import build_raw_prompt, transform_prompt, update_and_inject

app = Flask(__name__)

@app.route("/queue_status", methods=["GET"])
def queue_status():
    try:
        # Proxy the ComfyUI queue endpoint
        r = requests.get("http://127.0.0.1:8188/queue", timeout=5)
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate_prompt", methods=["POST"])
def generate_prompt():
    try:
        # Collect the raw pieces
        subject = request.form["subject"]
        pose    = request.form["pose"]
        setting = request.form["setting"]
        other   = request.form["other"]
          # extract seed

        # Build & transform
        raw = build_raw_prompt(subject, pose, setting, other)
        prompt = transform_prompt(raw)

        return jsonify({"prompt": prompt})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_image", methods=["POST"])
def generate_image():
    try:
        data = request.get_json()
        prompt        = data["prompt"]
        realism_lora  = data["realism_lora"]
        detail_lora   = data["detail_lora"]
        workflow_type = data["workflow_type"]
        seed    = data.get("seed", None)
        # 1) Determine master and output filenames
        master_file = (
            "smoke_test.json" if workflow_type == "smoke"
            else "final_image.json"
        )
        output_file = f"{workflow_type}_updated.json"

        # 2) update_on_disk & get node map (passing seed!)
        node_map = update_and_inject(
            master_file, output_file,
            prompt, realism_lora, detail_lora, seed
        )

        # Build the final payload just like comfy_auto.py did
        import uuid
        job_id = str(uuid.uuid4())
        payload = {
            "prompt": node_map,           # nested node map
            "client_id": job_id,
            "filename_prefix": job_id,
        }
        resp = requests.post(
            "http://127.0.0.1:8188/prompt",
            json=payload,
            timeout=5
        )
        resp.raise_for_status()

        return jsonify({"job_id": resp.text})
    except requests.RequestException as req_err:
        return jsonify({"error": f"ComfyUI request failed: {req_err}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
