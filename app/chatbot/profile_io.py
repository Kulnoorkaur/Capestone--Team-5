"""Read and write Chat Buddy confirmed profiles without Streamlit UI state."""

from dataclasses import dataclass
import json

from app.chatbot.d23_adapter import D23AnswerAdapter, FIELDS_BY_ID
from app.chatbot.questionnaire_bridge import (
    CONDITIONAL_FIELDS,
    QUESTIONNAIRE_FIELDS,
    QuestionnaireBridge,
)

COMBINED_SCHEMA = "chat-buddy-confirmed-profile"
COMBINED_VERSION = 1


class ProfileImportError(ValueError):
    """The supplied JSON cannot be imported as a confirmed Chat Buddy profile."""


@dataclass(frozen=True)
class CombinedProfile:
    """Validated stores ready to replace the current confirmed answers."""

    bridge: QuestionnaireBridge
    algorithms: D23AnswerAdapter


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileImportError(f"Duplicate field ID: {key}.")
        result[key] = value
    return result


def _read_json(raw):
    if not isinstance(raw, (str, bytes)):
        raise ProfileImportError("Expected JSON text or UTF-8 bytes.")
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(text, object_pairs_hook=_unique_object)
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


def _load_bridge(profile):
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
    return bridge


def load_confirmed_profile(raw: str | bytes) -> dict[str, dict[str, str | list[str]]]:
    """Validate legacy flat JSON and return D2.6's two input sections.

    D2.6 can use `product` and `ai_function` directly. D3 uses the same
    dictionaries under `product_profile` and `ai_function`.
    """
    bridge = _load_bridge(_read_json(raw))
    return {
        "product": bridge.get_questionnaire_answers("D2.1"),
        "ai_function": bridge.get_questionnaire_answers("D2.2"),
    }


def dump_combined_profile(bridge: QuestionnaireBridge, algorithms: D23AnswerAdapter | None = None) -> str:
    """Serialize confirmed D2.1–D2.3 values, excluding chat provenance and drafts."""
    records = []
    if algorithms is not None:
        for algorithm_id in algorithms.algorithm_ids:
            record = algorithms.get_algorithm(algorithm_id)
            records.append({
                "algorithm_id": algorithm_id,
                "name": record["name"],
                "version": record["version"],
                "answers": record["answers"],
            })
    return json.dumps({
        "schema": COMBINED_SCHEMA,
        "version": COMBINED_VERSION,
        "product": bridge.get_questionnaire_answers("D2.1"),
        "ai_function": bridge.get_questionnaire_answers("D2.2"),
        "algorithms": records,
    }, indent=2, ensure_ascii=False, sort_keys=True)


def load_combined_profile(raw: str | bytes) -> CombinedProfile:
    """Validate a versioned profile into fresh stores, or raise ProfileImportError."""
    profile = _read_json(raw)
    if not isinstance(profile, dict) or profile.get("schema") != COMBINED_SCHEMA:
        raise ProfileImportError("Expected a Chat Buddy combined profile.")
    version = profile.get("version")
    if type(version) is not int or version != COMBINED_VERSION:
        raise ProfileImportError(f"Unsupported combined profile version: {version!r}.")
    if profile.keys() != {"schema", "version", "product", "ai_function", "algorithms"}:
        raise ProfileImportError("Expected schema, version, product, ai_function, and algorithms sections.")
    product = profile["product"]
    ai_function = profile["ai_function"]
    records = profile["algorithms"]
    if not isinstance(product, dict) or not isinstance(ai_function, dict) or not isinstance(records, list):
        raise ProfileImportError("Expected product and ai_function objects and an algorithms list.")
    if product.keys() & ai_function.keys():
        raise ProfileImportError("A field ID appears in both questionnaire sections.")
    bridge = _load_bridge({**product, **ai_function})
    if (
        product != bridge.get_questionnaire_answers("D2.1")
        or ai_function != bridge.get_questionnaire_answers("D2.2")
    ):
        raise ProfileImportError("A field ID is in the wrong questionnaire section.")

    algorithms = D23AnswerAdapter()
    for index, record in enumerate(records, start=1):
        try:
            _load_algorithm(algorithms, record)
        except ValueError as error:
            raise ProfileImportError(f"Algorithm record {index}: {error}") from error
    return CombinedProfile(bridge, algorithms)


def _load_algorithm(algorithms, record):
    if not isinstance(record, dict) or record.keys() != {"algorithm_id", "name", "version", "answers"}:
        raise ProfileImportError("Expected algorithm_id, name, version, and answers.")
    algorithm_id = record["algorithm_id"]
    if not isinstance(algorithm_id, str) or not algorithm_id.strip():
        raise ProfileImportError("Algorithm ID must be non-empty text.")
    answers = record["answers"]
    if not isinstance(answers, dict):
        raise ProfileImportError("Expected a D2.3 answers object.")
    unknown = answers.keys() - FIELDS_BY_ID.keys()
    if unknown:
        raise ProfileImportError(f"Unknown D2.3 field IDs: {', '.join(sorted(unknown))}.")

    algorithms.add_algorithm(record["name"], record["version"], algorithm_id=algorithm_id)
    # Owner schema order places all ancestors before their conditional children.
    for field_id in FIELDS_BY_ID:
        if field_id not in answers:
            continue
        answer = answers[field_id]
        if not isinstance(answer, dict) or answer.keys() != {"value", "details", "evidence"}:
            raise ProfileImportError(f"{field_id}: Expected value, details, and evidence.")
        algorithms.save_answer(algorithm_id, field_id, **answer)
