"""
Deliverable 3.1 — Consolidated Validation Summary

Standardizes validation results from the integrated questionnaires.

This module does not determine regulatory compliance,
classification, approval, or authorization.
"""


def build_validation_summary(validation_results):
    """
    Combine questionnaire validation results into a consistent structure.

    Parameters
    ----------
    validation_results : dict
        Dictionary mapping questionnaire names to lists of issues.

    Returns
    -------
    dict
        Consolidated validation summary.
    """

    summary = {
        "questionnaires": {},
        "overall": {},
    }

    total_issues = 0

    total_missing = 0
    total_conditional = 0
    total_uncertain = 0
    total_review = 0

    for questionnaire_name, issues in validation_results.items():

        missing = sum(
            issue.get("type") == "missing"
            for issue in issues
        )

        conditional = sum(
            issue.get("type") == "conditional"
            for issue in issues
        )

        uncertain = sum(
            issue.get("type") == "uncertain"
            for issue in issues
        )

        review = sum(
            issue.get("type") == "review"
            for issue in issues
        )

        issue_count = len(issues)

        total_issues += issue_count
        total_missing += missing
        total_conditional += conditional
        total_uncertain += uncertain
        total_review += review

        summary["questionnaires"][questionnaire_name] = {
            "total_issues": issue_count,
            "missing": missing,
            "conditional": conditional,
            "uncertain": uncertain,
            "explicit_review_flags": review,
            "information_gaps_present": issue_count > 0,
            "issues": issues,
        }

    summary["overall"] = {
        "total_issues": total_issues,
        "missing": total_missing,
        "conditional": total_conditional,
        "uncertain": total_uncertain,
        "explicit_review_flags": total_review,
        "information_gaps_present": total_issues > 0,
        "explicit_manual_review_required": total_review > 0,
    }

    return summary