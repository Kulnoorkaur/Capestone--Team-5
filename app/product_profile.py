import json
from pathlib import Path


def load_profile_fields():
    """Load the product profile questionnaire definitions."""

    file_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "product_profile_fields.json"
    )

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def collect_product_profile(fields):
    """Collect responses for each product profile field."""

    profile = {}

    for field in fields:
        field_id = field["id"]
        question = field["question"]

        print(f"\n{field_id}: {question}")

        response = input("Your answer: ").strip()

        profile[field_id] = response

    return profile


def validate_profile(fields, profile):
    """Identify missing required product information."""

    missing_fields = []

    for field in fields:
        if field.get("required", False):
            field_id = field["id"]

            if not profile.get(field_id):
                missing_fields.append(field_id)

    return missing_fields


def main():
    fields = load_profile_fields()

    print("AI Regulatory Readiness Platform")
    print("Deliverable 2.1: Product and Intended-Use Profile")

    profile = collect_product_profile(fields)

    missing = validate_profile(fields, profile)

    if missing:
        print("\nManual regulatory review required.")
        print("Missing required fields:", ", ".join(missing))
    else:
        print("\nProduct profile completed.")

    output_file = Path("product_profile_output.json")

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(profile, file, indent=4)

    print(f"\nProfile saved to {output_file}")


if __name__ == "__main__":
    main()
