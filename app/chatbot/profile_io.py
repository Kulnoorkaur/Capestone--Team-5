"""Read and write Chat Buddy confirmed profiles without Streamlit UI state."""

from dataclasses import dataclass
import json

from app.chatbot.d23_adapter import D23AnswerAdapter, FIELDS_BY_ID
from app.chatbot.d24_adapter import D24AnswerAdapter
from app.chatbot.d24_metadata import D24CompatibilityError
from app.chatbot.questionnaire_bridge import (
    CONDITIONAL_FIELDS,
    QUESTIONNAIRE_FIELDS,
    QuestionnaireBridge,
)

COMBINED_SCHEMA = "chat-buddy-confirmed-profile"
COMBINED_VERSION = 1
COMBINED_D24_VERSION = 2
_D24_COLLECTIONS = {"datasets": "dataset", "ai_function_versions": "function", "evidence_documents": "document"}


class ProfileImportError(ValueError):
    """The supplied JSON cannot be imported as a confirmed Chat Buddy profile."""


@dataclass(frozen=True)
class CombinedProfile:
    """Validated stores ready to replace the current confirmed answers."""

    bridge: QuestionnaireBridge
    algorithms: D23AnswerAdapter
    dataset_evidence: D24AnswerAdapter | None = None


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


def dump_combined_profile(
    bridge: QuestionnaireBridge,
    algorithms: D23AnswerAdapter | None = None,
    *,
    dataset_evidence: D24AnswerAdapter | None = None,
) -> str:
    """Write v1 by default, or v2 with a D2.4 adapter (which may be empty)."""
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
    profile = {
        "schema": COMBINED_SCHEMA,
        "version": COMBINED_VERSION,
        "product": bridge.get_questionnaire_answers("D2.1"),
        "ai_function": bridge.get_questionnaire_answers("D2.2"),
        "algorithms": records,
    }
    if dataset_evidence is not None:
        dataset_evidence.check_compatibility()
        profile["version"] = COMBINED_D24_VERSION
        profile["dataset_evidence"] = _dump_d24(dataset_evidence)
    return json.dumps(profile, indent=2, ensure_ascii=False, sort_keys=True)


def load_combined_profile(raw: str | bytes, *, allow_d24: bool = False) -> CombinedProfile:
    """Validate fresh stores. Chat Buddy opts into v2; v1-only consumers stay unchanged."""
    profile = _read_json(raw)
    if not isinstance(profile, dict) or profile.get("schema") != COMBINED_SCHEMA:
        raise ProfileImportError("Expected a Chat Buddy combined profile.")
    version = profile.get("version")
    versions = (COMBINED_VERSION, COMBINED_D24_VERSION) if allow_d24 else (COMBINED_VERSION,)
    if type(version) is not int or version not in versions:
        raise ProfileImportError(f"Unsupported combined profile version: {version!r}.")
    keys = {"schema", "version", "product", "ai_function", "algorithms"}
    if version == COMBINED_D24_VERSION:
        keys.add("dataset_evidence")
    if profile.keys() != keys:
        raise ProfileImportError(f"Expected exactly these version {version} sections: {', '.join(sorted(keys))}.")
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
    dataset_evidence = _load_d24(profile["dataset_evidence"]) if version == COMBINED_D24_VERSION else None
    return CombinedProfile(bridge, algorithms, dataset_evidence)


def _dump_d24(adapter):
    section = {"questionnaire_sha256": adapter.questionnaire_fingerprint, "gmlp": adapter.get_answers(adapter.GMLP)}
    for collection, kind in _D24_COLLECTIONS.items():
        records = []
        for record_id in adapter.record_ids(kind):
            answers = adapter.get_answers(record_id)
            inventory = {
                field_id.removeprefix("DEP-001."): answers.pop(field_id)
                for field_id in tuple(answers) if field_id.startswith("DEP-001.")
            }
            if inventory:
                answers["DEP-001"] = inventory
            records.append({"record_id": record_id, "answers": answers})
        section[collection] = records
    return section


def _load_d24(section):
    if not isinstance(section, dict) or section.keys() != {"questionnaire_sha256", "gmlp", *_D24_COLLECTIONS}:
        raise ProfileImportError("D2.4 requires dataset, evaluation and document lists, GMLP and a questionnaire fingerprint.")
    try:
        adapter = D24AnswerAdapter()
    except D24CompatibilityError as error:
        raise ProfileImportError(str(error)) from None
    if section["questionnaire_sha256"] != adapter.questionnaire_fingerprint:
        raise ProfileImportError(
            "D2.4 compatibility manifest requires review. This backup uses a different questionnaire fingerprint."
        )
    for collection, kind in _D24_COLLECTIONS.items():
        if not isinstance(section[collection], list):
            raise ProfileImportError(f"D2.4 {collection} must be a list.")
        for index, record in enumerate(section[collection], start=1):
            try:
                if not isinstance(record, dict) or record.keys() != {"record_id", "answers"}:
                    raise ValueError("Expected record_id and answers.")
                if record["record_id"] is None:
                    raise ValueError("A record ID is required.")
                record_id = adapter.create_record(kind, record_id=record["record_id"])
                _load_d24_answers(adapter, record_id, record["answers"], dataset=kind == "dataset")
            except ValueError as error:
                raise ProfileImportError(f"D2.4 {collection} record {index}: {error}") from error
    try:
        _load_d24_answers(adapter, adapter.GMLP, section["gmlp"])
    except ValueError as error:
        raise ProfileImportError(f"D2.4 GMLP: {error}") from error
    return adapter


def _load_d24_answers(adapter, record_id, answers, *, dataset=False):
    if not isinstance(answers, dict):
        raise ValueError("Expected a confirmed answers object.")
    answers = answers.copy()
    if dataset:
        if any(field_id.startswith("DEP-001.") for field_id in answers):
            raise ValueError("DEP-001 inventory answers must be nested under DEP-001.")
        if "DEP-001" in answers:
            inventory = answers.pop("DEP-001")
            if not isinstance(inventory, dict):
                raise ValueError("DEP-001 inventory must be an object.")
            answers.update({f"DEP-001.{key}": value for key, value in inventory.items()})
    fields = adapter.field_ids(record_id)
    unknown = answers.keys() - set(fields)
    if unknown:
        raise ValueError(f"Unknown field IDs: {', '.join(sorted(unknown))}.")
    for field_id in fields:
        if field_id in answers:
            adapter.save_answer(record_id, field_id, answers[field_id])
    if adapter.get_answers(record_id) != answers:
        raise ValueError("The recorded answers contain an inactive conditional field.")


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
