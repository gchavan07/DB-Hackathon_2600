import os
import glob
from .config import AGENT_DIR

def find_matching_skills(instruction: str):
    """Parses the .agent folder, reads skill definitions, and matches based on keywords."""
    matched_skills = []
    
    if not os.path.exists(AGENT_DIR):
        os.makedirs(AGENT_DIR)
        return [{"name": "default-bmad-agent", "path": "", "content": "Default BMAD execution skill."}]

    skill_files = glob.glob(os.path.join(AGENT_DIR, "*.md"))
    instruction_words = set(instruction.lower().split())

    for file_path in skill_files:
        skill_name = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Simple keyword overlap scoring
            skill_tokens = set(content.lower().split())
            overlap = instruction_words.intersection(skill_tokens)
            
            if len(overlap) > 0 or not instruction_words:
                matched_skills.append({
                    "name": skill_name,
                    "path": file_path,
                    "content": content,
                    "score": len(overlap)
                })
        except Exception:
            continue

    # Sort by relevance match score
    matched_skills.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    if not matched_skills:
        # Fallback if no specific file matches
        matched_skills.append({
            "name": "general-bmad-workflow",
            "path": "",
            "content": "Standard BMAD Agile Agent behavior.",
            "score": 0
        })

    return matched_skills