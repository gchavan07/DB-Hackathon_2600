import os
from .config import INPUT_DOCS_DIR


def _read_docx(file_path: str) -> str:
    """Extract text from a .docx file (requires python-docx)."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return "[python-docx not installed — run: pip install python-docx]"
    except Exception as e:
        return f"[Error reading .docx: {e}]"


def load_input_documents() -> dict:
    """Scans the input_docs directory and returns all file contents.
    Supports: .txt, .md, .text, .json, .py, .yaml, .yml, .docx
    """
    docs = {}
    if not os.path.exists(INPUT_DOCS_DIR):
        os.makedirs(INPUT_DOCS_DIR)
        return docs

    TEXT_EXTENSIONS = {".txt", ".md", ".text", ".json", ".py", ".yaml", ".yml"}

    for filename in sorted(os.listdir(INPUT_DOCS_DIR)):
        file_path = os.path.join(INPUT_DOCS_DIR, filename)
        if not os.path.isfile(file_path):
            continue
        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext == ".docx":
                docs[filename] = _read_docx(file_path)
            elif ext in TEXT_EXTENSIONS:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    docs[filename] = f.read()
            else:
                # Skip unsupported types silently
                continue
        except Exception as e:
            docs[filename] = f"[Error reading file: {e}]"

    return docs