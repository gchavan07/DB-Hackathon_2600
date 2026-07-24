"""
BMAD Agent Orchestrator – Browser-Based Web Application
Run with:  python app.py
Then open: http://localhost:5000
"""

import os
import markdown2
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from src.engine import run_workflow_web
from src.ingester import load_input_documents
from src.llm import generate_architecture_diagram, load_settings, save_settings
from src.config import INPUT_DOCS_DIR, OUTPUT_DIR

# Store latest diagram in memory (simple single-user cache)
_diagram_cache: dict = {"mermaid": None}

app = Flask(__name__)
app.secret_key = "bmad-secret-key-2026"

ALLOWED_EXTENSIONS = {"txt", "md", "json", "text", "py", "yaml", "yml"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_input_docs():
    if not os.path.exists(INPUT_DOCS_DIR):
        return []
    return sorted(os.listdir(INPUT_DOCS_DIR))


def get_reports():
    if not os.path.exists(OUTPUT_DIR):
        return []
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")]
    return sorted(files, reverse=True)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        input_docs=get_input_docs(),
        reports=get_reports(),
    )


@app.route("/run", methods=["POST"])
def run():
    instruction = request.form.get("instruction", "").strip()
    if not instruction:
        flash("Please enter an instruction before running.", "error")
        return redirect(url_for("index"))

    try:
        output_path = run_workflow_web(instruction)
        report_filename = os.path.basename(output_path)
        flash(f"Report generated successfully: {report_filename}", "success")
        return redirect(url_for("view_report", filename=report_filename))
    except Exception as e:
        flash(f"Error during execution: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/report/<filename>")
def view_report(filename):
    safe_filename = secure_filename(filename)
    report_path = os.path.join(OUTPUT_DIR, safe_filename)
    if not os.path.exists(report_path):
        flash("Report not found.", "error")
        return redirect(url_for("index"))

    with open(report_path, "r", encoding="utf-8") as f:
        raw_md = f.read()

    html_content = markdown2.markdown(
        raw_md,
        extras=["tables", "fenced-code-blocks", "header-ids", "strike", "task_list"],
    )
    return render_template(
        "report.html",
        filename=safe_filename,
        html_content=html_content,
        reports=get_reports(),
    )


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(INPUT_DOCS_DIR, exist_ok=True)
        file.save(os.path.join(INPUT_DOCS_DIR, filename))
        flash(f"File '{filename}' uploaded successfully.", "success")
    else:
        flash("File type not allowed. Supported: txt, md, json, text, py, yaml, yml", "error")

    return redirect(url_for("index"))


@app.route("/delete-doc/<filename>", methods=["POST"])
def delete_doc(filename):
    safe_filename = secure_filename(filename)
    file_path = os.path.join(INPUT_DOCS_DIR, safe_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f"Document '{safe_filename}' deleted.", "success")
    else:
        flash("File not found.", "error")
    return redirect(url_for("index"))


@app.route("/diagram", methods=["GET", "POST"])
def diagram():
    if request.method == "POST":
        try:
            ingested = load_input_documents()
            if not ingested:
                flash("No input documents found. Upload documents first.", "error")
                return redirect(url_for("diagram"))
            mermaid_code = generate_architecture_diagram(ingested)
            _diagram_cache["mermaid"] = mermaid_code
            flash("Architecture diagram generated successfully!", "success")
        except EnvironmentError as e:
            flash(f"ADC config error: {str(e)}", "error")
        except Exception as e:
            flash(f"LLM error: {str(e)}", "error")
    settings = load_settings()
    return render_template(
        "diagram.html",
        diagram=_diagram_cache.get("mermaid"),
        gcp_project=settings.get("gcp_project", ""),
        vertex_location=settings.get("vertex_location", "us-central1"),
    )


@app.route("/save-settings", methods=["POST"])
def save_settings_route():
    gcp_project      = request.form.get("gcp_project", "").strip()
    vertex_location  = request.form.get("vertex_location", "us-central1").strip()
    if not gcp_project:
        flash("Project ID cannot be empty.", "error")
        return redirect(url_for("diagram"))
    save_settings({"gcp_project": gcp_project, "vertex_location": vertex_location})
    flash(f"Settings saved. Project set to: {gcp_project}", "success")
    return redirect(url_for("diagram"))


@app.route("/api/reports")
def api_reports():
    """JSON endpoint listing all reports."""
    return jsonify(get_reports())


if __name__ == "__main__":
    os.makedirs(INPUT_DOCS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("🚀  BMAD Web App running at http://localhost:5000")
    app.run(debug=True, port=5000)
