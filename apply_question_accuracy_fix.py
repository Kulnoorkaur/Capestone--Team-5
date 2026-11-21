"""Safely ground Chat Buddy questions in the team's canonical questionnaire wording.
Run from repository root: python apply_question_accuracy_fix.py
Only edits app/chatbot/chat_llm.py; creates a .pre_question_accuracy.bak copy.
"""
from pathlib import Path
import ast
import shutil

path = Path('app/chatbot/chat_llm.py')
if not path.exists():
    raise SystemExit(f'Missing {path}; run from the repository root.')
source = path.read_text(encoding='utf-8')
tree = ast.parse(source)
func = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'generate_questionnaire_question'), None)
if func is None:
    raise SystemExit('Cannot find generate_questionnaire_question; no changes made.')

replacement = '''def generate_questionnaire_question(
    field_id,
    field_label,
    field_type,
    field_options=None,
    confirmed_answers=None,
):
    """Ask the team's original questionnaire question without semantic drift.

    The question wording is intentionally deterministic. Gemini still handles
    answer evaluation, extraction and suggestions elsewhere in this module.
    """
    if not isinstance(field_id, str) or not field_id.strip():
        raise ValueError("A valid questionnaire field ID is required.")
    if not isinstance(field_label, str) or not field_label.strip():
        raise ValueError("A valid questionnaire field label is required.")
    if not isinstance(field_type, str) or not field_type.strip():
        raise ValueError("A valid questionnaire field type is required.")
    if field_options is not None and not isinstance(field_options, list):
        raise ValueError("field_options must be a list.")
    if confirmed_answers is not None and not isinstance(confirmed_answers, dict):
        raise ValueError("confirmed_answers must be a dictionary.")

    # Exact prompts from app/deliverable_2/questionnaires/ai_function.py.
    canonical_d22 = {
        "AIF-001": "What input information does the software use?",
        "AIF-002": "What technical input requirements or limitations apply?",
        "AIF-003": "Where do inputs come from, and how are they received?",
        "AIF-004": "How does the AI process the input information to perform its function?",
        "AIF-005": "Does the AI alter an image or create a new image for clinical interpretation?",
        "AIF-006": "What does the software output?",
        "AIF-007": "How is the output displayed or delivered?",
        "AIF-008": "What clinical information or finding does the output represent?",
        "AIF-009": "What information helps users interpret the output?",
        "AIF-010": "Is the output intended to inform, prioritize, support, or determine a clinical action? Explain.",
        "AIF-011": "Who receives the AI output, and who is responsible for the clinical decision?",
        "AIF-012": "What clinical action or decision may follow the output?",
        "AIF-013": "What could happen if the AI output is incorrect, delayed, or missing?",
        "AIF-014": "Does the AI output require additional clinical confirmation before a decision?",
        "AIF-015": "Which tasks run automatically without user initiation?",
        "AIF-016": "Is the AI output reviewed by a healthcare professional before clinical action?",
        "AIF-017": "Can healthcare professionals independently assess information supporting the AI output?",
        "AIF-018": "What control does the intended user have over the AI output or action?",
        "AIF-019": "Can the AI initiate a clinical or workflow action without human approval?",
        "AIF-020": "How does the system respond to inadequate input quality or uncertain results?",
    }
    canonical_followups = {
        "TRAINING-DETAILS": "Describe the specialized training required for intended human users of the product.",
        "AIF-005-DETAILS": "Describe the modification or generated image, and whether the original is retained.",
        "AIF-014-DETAILS": "Describe what confirmation is required and when it occurs.",
        "AIF-016-DETAILS": "Describe the review and action sequence.",
        "AIF-017-DETAILS": "Describe the source information or evidence available for independent assessment.",
        "AIF-019-DETAILS": "Describe the actions, triggers, and safeguards.",
    }

    if field_id in canonical_d22:
        question = canonical_d22[field_id]
    elif field_id in canonical_followups:
        question = canonical_followups[field_id]
    elif field_id.endswith("-OTHER"):
        question = f"You selected Other for {field_id.removesuffix('-OTHER')}. Please specify."
    else:
        # D2.1 questionnaire uses its field labels as the original input labels.
        # Never ask Gemini to reinterpret a short regulatory label.
        question = f"Please provide the following product information: {field_label}."

    if field_options:
        question += "\\n\\nAvailable options: " + ", ".join(field_options) + "."
    return question
'''

lines = source.splitlines(keepends=True)
start, end = func.lineno - 1, func.end_lineno
updated = ''.join(lines[:start]) + replacement + ''.join(lines[end:])
ast.parse(updated)
backup = path.with_suffix(path.suffix + '.pre_question_accuracy.bak')
if backup.exists():
    raise SystemExit(f'Backup already exists: {backup}; no changes made.')
shutil.copy2(path, backup)
path.write_text(updated, encoding='utf-8')
print(f'Updated {path} (backup: {backup})')
print('Original D2.2 wording preserved; AIF-017 is now grounded correctly.')
