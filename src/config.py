import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, ".agent")
INPUT_DOCS_DIR = os.path.join(BASE_DIR, "input_docs")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")