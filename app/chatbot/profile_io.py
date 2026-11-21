"""Load Chat Buddy's flat confirmed-answer JSON without Streamlit UI state."""

import json

from app.chatbot.questionnaire_bridge import (
    CONDITIONAL_FIELDS,
    QUESTIONNAIRE_FIELDS,
    QuestionnaireBridge,
)


class ProfileImportError(ValueError):
    """The supplied JSON cannot be imported as a confirmed Chat Buddy profile."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileImportError(f"Duplicate field ID: {key}.")
        result[key] = value
    return result


def load_confirmed_profile(raw: str | bytes) -> dict[str, dict[str, str | list[str]]]:
    """Validate JSON text or UTF-8 bytes and return D2.6's two input sections.

    D2.6 can use the returned `product` and `ai_function` dictionaries directly.
    D3 uses the same dictionaries under `product_profile` and `ai_function`.
    Partial profiles are valid, including an empty JSON object. Invalid imports
    raise ProfileImportError and return no sections.
    """
    if not isinstance(raw, (str, bytes)):
        raise ProfileImportError("Expected JSON text or UTF-8 bytes.")
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        profile = json.loads(text, object_pairs_hook=_unique_object)
    except UnicodeDecodeError as error:
        raise ProfileImportError("Profile must be encoded as UTF-8.") from error
    except json.JSONDecodeError as error:
        raise ProfileImportError(
            f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}."
        ) from error
    except RecursionError as error:
        raise ProfileImportError("Invalid JSON: the profile is nested too deeply.") from error
    except ProfileImportError:
        raise
    except ValueError as error:
        raise ProfileImportError("Invalid JSON: a value could not be decoded.") from error

    if not isinstance(profile, dict):
        raise ProfileImportError("Expected a flat JSON object mapping field IDs to answers.")

    primary_fields = {field_id for fields in QUESTIONNAIRE_FIELDS.values() for field_id in fields}
    unknown_fields = profile.keys() - primary_fields - CONDITIONAL_FIELDS.keys()
    if unknown_fields:
        raise ProfileImportError(f"Unknown field IDs: {', '.join(sorted(unknown_fields))}.")

    bridge = QuestionnaireBridge()
    # All current conditional fields depend on primary answers.
    for field_group in (primary_fields, CONDITIONAL_FIELDS.keys()):
        for field_id in sorted(profile.keys() & field_group):
            valid, error = bridge.save_answer(field_id, profile[field_id])
            if not valid:
                raise ProfileImportError(f"{field_id}: {error}")

    return {
        "product": bridge.get_questionnaire_answers("D2.1"),
        "ai_function": bridge.get_questionnaire_answers("D2.2"),
    }
