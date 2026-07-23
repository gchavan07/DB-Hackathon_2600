import os
from .config import INPUT_DOCS_DIR

def load_input_documents():
    """Scans the input_docs directory and aggregates all relevant file contents."""
    docs = {}
    if not os.path.exists(INPUT_DOCS_DIR):
        os.makedirs(INPUT_DOCS_DIR)
        return docs

    for filename in os.listdir(INPUT_DOCS_DIR):
        file_path = os.path.join(INPUT_DOCS_DIR, filename)
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    docs[filename] = f.read()
            except Exception as e:
                docs[filename] = f"[Error reading file: {e}]"
                
    return docs