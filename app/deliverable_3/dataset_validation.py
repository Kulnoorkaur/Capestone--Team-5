"""Reusable D2.4 validation logic. No Streamlit interface."""

REQUIRED_DATASET_FIELDS = ['DEP-002', 'DEP-003', 'DEP-004', 'DEP-005', 'DEP-006', 'DEP-007', 'DEP-008', 'DEP-009', 'DEP-010', 'DEP-011', 'DEP-013', 'DEP-014', 'DEP-014-details', 'DEP-015', 'DEP-016', 'DEP-017', 'DEP-018']


REQUIRED_AI_FIELDS = ['DEP-019-versions', 'DEP-019-release', 'DEP-020-metrics', 'DEP-020-thresholds', 'DEP-020-criteria', 'DEP-020-prespecified', 'DEP-020-justification', 'DEP-021-overall', 'DEP-021-subgroups', 'DEP-021-prespecified', 'DEP-021-report', 'DEP-023', 'DEP-024', 'DEP-026-records', 'DEP-026-standard', 'DEP-026-fda-level', 'DEP-027', 'DEP-028', 'DEP-032']


REQUIRED_DOCUMENT_FIELDS = ['title', 'document_id', 'version', 'date', 'page_section', 'supported_fields']


FIELD_LABELS = {'DEP-001': 'Dataset Inventory', 'DEP-002': 'Sources, Sites and Collection Period', 'DEP-003': 'Collection Design', 'DEP-004': 'Ethics, Consent, Data-Use and Privacy', 'DEP-005': 'Sample Sizes', 'DEP-006': 'Inclusion and Exclusion Criteria', 'DEP-007': 'Population Composition', 'DEP-008': 'Acquisition Characteristics', 'DEP-009': 'Preprocessing and Quality Control', 'DEP-010': 'Data Management and Traceability', 'DEP-011': 'Reference Standard', 'DEP-012': 'Expert Selection and Agreement', 'DEP-013': 'Reference Standard Limitations', 'DEP-014': 'Partitioning and Independence', 'DEP-015': 'External or Independent Test Data', 'DEP-016': 'Dataset Representativeness', 'DEP-017': 'Bias Assessment and Mitigation', 'DEP-018': 'Known Data Gaps', 'DEP-019': 'Evaluated Software and Model Versions', 'DEP-020': 'Metrics and Acceptance Criteria', 'DEP-021': 'Overall and Subgroup Results', 'DEP-022': 'Repeatability and Reproducibility', 'DEP-023': 'Robustness and Failure Testing', 'DEP-024': 'Output Uncertainty', 'DEP-025': 'Generated or Modified Outputs', 'DEP-026': 'Software Verification and Validation', 'DEP-027': 'Valid Clinical Association', 'DEP-028': 'Clinical Performance Evidence Type', 'DEP-029': 'Clinical Study Population and Independence', 'DEP-030': 'Clinical Performance Measures and Results', 'DEP-031': 'Human-AI Team Evaluation', 'DEP-032': 'Evidence-to-Claim Alignment', 'DEP-033': 'Rationale Without Device-Specific Clinical Data', 'DEP-034': 'Planned Human Studies', 'DEP-035': 'Evidence Document Register', 'DEP-036': 'GMLP Implementation'}


GATE_MAPPING = {}


def is_missing(value):
    """Check whether a response is missing."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip() == 'Select an option'
    if isinstance(value, list):
        return len(value) == 0
    return False


def has_option(record, field_id, option):
    """Check whether an option was selected."""
    value = record.get(field_id)
    if isinstance(value, list):
        return option in value
    return value == option


def selected_options(value):
    """Convert a response into a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def base_field_id(field_id):
    """Find the main DEP identifier in a field key."""
    for part in field_id.split('-'):
        if part.startswith('DEP'):
            continue
    parts = field_id.split('-')
    if len(parts) >= 2 and parts[0] == 'DEP':
        return '-'.join(parts[:2])
    return field_id


def validate_dataset_evidence(profile):
    """
    Check completeness and consistency of questionnaire responses.

    Checks each dataset, AI function/version and evidence document
    separately.

    These checks do not determine regulatory readiness.
    """
    issues = []

    def add(field_id, message, issue_type, record_name):
        identifier = base_field_id(field_id)
        issues.append({'field_id': field_id, 'field': FIELD_LABELS.get(identifier, identifier), 'issue': message, 'type': issue_type, 'record': record_name, 'relevant_gates': GATE_MAPPING.get(identifier, [])})

    def check_required(record, field_ids, record_name):
        for field_id in field_ids:
            if is_missing(record.get(field_id)):
                add(field_id, 'Required information has not been provided.', 'missing', record_name)
    datasets = profile.get('datasets', [])
    if not datasets:
        add('DEP-001', 'At least one dataset record is needed.', 'missing', 'Datasets')
    for index, dataset in enumerate(datasets, start=1):
        name = f'Dataset {index}'
        inventory = dataset.get('DEP-001', {})
        if is_missing(inventory.get('dataset_name_version')):
            add('DEP-001', 'Dataset name and version have not been provided.', 'missing', name)
        if is_missing(inventory.get('role')):
            add('DEP-001', "The dataset's role has not been identified.", 'missing', name)
        if is_missing(inventory.get('source_documentation')):
            add('DEP-001', 'The source documentation for this dataset has not been provided.', 'missing', name)
        check_required(dataset, REQUIRED_DATASET_FIELDS, name)
        if has_option(inventory, 'role', 'Other') and is_missing(inventory.get('role_other')):
            add('DEP-001', 'Describe the other dataset role.', 'conditional', name)
        if has_option(dataset, 'DEP-004', 'Other'):
            if is_missing(dataset.get('DEP-004-other')):
                add('DEP-004', 'Describe the other ethics or privacy basis.', 'conditional', name)
        if dataset.get('DEP-004') and dataset.get('DEP-004') != ['Unknown'] and is_missing(dataset.get('DEP-004-details')):
            add('DEP-004', 'Describe the applicable ethics, consent, data-use and privacy details.', 'conditional', name)
        preprocessing = selected_options(dataset.get('DEP-009'))
        if preprocessing and (not set(preprocessing).issubset({'None', 'Unknown'})) and is_missing(dataset.get('DEP-009-details')):
            add('DEP-009', 'Describe the preprocessing and quality-control methods.', 'conditional', name)
        if has_option(dataset, 'DEP-011', 'Other'):
            if is_missing(dataset.get('DEP-011-other')):
                add('DEP-011', 'Describe the other reference standard.', 'conditional', name)
        reference = selected_options(dataset.get('DEP-011'))
        if reference and reference != ['Unknown'] and is_missing(dataset.get('DEP-011-details')):
            add('DEP-011', 'Describe the reference standard and why it is appropriate.', 'conditional', name)
        if dataset.get('DEP-012-trigger') == 'Yes' or has_option(dataset, 'DEP-011', 'Expert read'):
            if is_missing(dataset.get('DEP-012')):
                add('DEP-012', 'Describe the expert readers, qualifications and disagreement-handling process.', 'conditional', name)
        if dataset.get('DEP-014') == 'Other' and is_missing(dataset.get('DEP-014-other')):
            add('DEP-014', 'Describe the other unit used to split the data.', 'conditional', name)
        if dataset.get('DEP-015') == 'Yes' and is_missing(dataset.get('DEP-015-details')):
            add('DEP-015', 'Describe the external or independent test data.', 'conditional', name)
        if dataset.get('DEP-016') in ('Yes', 'Partly', 'No') and is_missing(dataset.get('DEP-016-details')):
            add('DEP-016', 'Explain dataset representativeness.', 'conditional', name)
        for field_id, value in dataset.items():
            if value == 'Unknown' or (isinstance(value, list) and 'Unknown' in value):
                add(field_id, 'The response is unknown and may need additional evidence or clarification.', 'uncertain', name)
    ai_versions = profile.get('ai_function_versions', [])
    if not ai_versions:
        add('DEP-019', 'At least one AI function/version record is needed.', 'missing', 'AI function/version records')
    for index, function in enumerate(ai_versions, start=1):
        name = f'AI Function / Version {index}'
        check_required(function, REQUIRED_AI_FIELDS, name)
        if function.get('DEP-019-release') == 'No' and is_missing(function.get('DEP-019-differences')):
            add('DEP-019', 'Describe the differences from the intended release version.', 'conditional', name)
        if has_option(function, 'DEP-020-metrics', 'Other') and is_missing(function.get('DEP-020-other')):
            add('DEP-020', 'Describe the other performance metric.', 'conditional', name)
        if has_option(function, 'DEP-021-subgroups', 'Other') and is_missing(function.get('DEP-021-other')):
            add('DEP-021', 'Describe the other subgroup.', 'conditional', name)
        if function.get('DEP-022-trigger') == 'Yes':
            if is_missing(function.get('DEP-022')):
                add('DEP-022', 'Report whether repeatability and reproducibility were tested.', 'conditional', name)
            elif function.get('DEP-022') in ('Yes', 'Not applicable') and is_missing(function.get('DEP-022-details')):
                add('DEP-022', 'Describe the testing or justify non-applicability.', 'conditional', name)
        if function.get('DEP-023') in ('Yes', 'Partly') and is_missing(function.get('DEP-023-details')):
            add('DEP-023', 'Describe robustness and failure testing.', 'conditional', name)
        if function.get('DEP-024') == 'Yes' and is_missing(function.get('DEP-024-details')):
            add('DEP-024', 'Describe the uncertainty estimate and supporting evidence.', 'conditional', name)
        if function.get('DEP-025-trigger') == 'Yes':
            if is_missing(function.get('DEP-025')):
                add('DEP-025', 'Identify the methods used to assess output fidelity.', 'conditional', name)
            if has_option(function, 'DEP-025', 'Other'):
                if is_missing(function.get('DEP-025-other')):
                    add('DEP-025', 'Describe the other assessment method.', 'conditional', name)
            methods = selected_options(function.get('DEP-025'))
            if methods and (not set(methods).issubset({'None', 'Unknown'})) and is_missing(function.get('DEP-025-details')):
                add('DEP-025', 'Describe the assessment findings and limitations.', 'conditional', name)
        if function.get('DEP-026-standard') == 'Other' and is_missing(function.get('DEP-026-standard-other')):
            add('DEP-026', 'Describe the other lifecycle standard.', 'conditional', name)
        if has_option(function, 'DEP-027', 'Other') and is_missing(function.get('DEP-027-details')):
            add('DEP-027', 'Describe the other type of clinical association evidence.', 'conditional', name)
        if function.get('DEP-027') and (not set(function.get('DEP-027')).issubset({'None', 'Unknown'})) and is_missing(function.get('DEP-027-details')):
            add('DEP-027', 'Describe the evidence supporting clinical association.', 'conditional', name)
        study_types = ['Retrospective analysis', 'Reader study', 'Prospective study', 'Clinical investigation', 'Real-world data']
        selected_study = any((study in function.get('DEP-028', []) for study in study_types))
        if selected_study:
            for field_id in ['DEP-029-population', 'DEP-029-independent', 'DEP-029-relevance', 'DEP-030-measures', 'DEP-030-comparator', 'DEP-030-results', 'DEP-030-limitations']:
                if is_missing(function.get(field_id)):
                    add(field_id, 'Clinical study information has not been provided.', 'conditional', name)
            if has_option(function, 'DEP-030-measures', 'Other'):
                if is_missing(function.get('DEP-030-other')):
                    add('DEP-030', 'Describe the other clinical performance measure.', 'conditional', name)
        if function.get('DEP-031-trigger') == 'Yes':
            if is_missing(function.get('DEP-031')):
                add('DEP-031', 'Report whether combined human-AI performance was evaluated.', 'conditional', name)
            elif function.get('DEP-031') in ('Yes', 'Not applicable') and is_missing(function.get('DEP-031-details')):
                add('DEP-031', 'Describe the evaluation or justify non-applicability.', 'conditional', name)
        if function.get('DEP-032') in ('Yes', 'Partly', 'No') and is_missing(function.get('DEP-032-details')):
            add('DEP-032', 'Explain how clinical evidence supports the intended claims.', 'conditional', name)
        if 'Literature only' in function.get('DEP-028', []) or 'None yet' in function.get('DEP-028', []):
            if is_missing(function.get('DEP-033')):
                add('DEP-033', 'Provide the rationale for the available clinical evidence.', 'conditional', name)
        if function.get('DEP-034') == 'Yes':
            for field_id in ['DEP-034-location', 'DEP-034-authorization']:
                if is_missing(function.get(field_id)):
                    add('DEP-034', 'Provide the planned study location and authorization or approval status.', 'conditional', name)
        for field_id, value in function.items():
            if value == 'Unknown' or (isinstance(value, list) and 'Unknown' in value):
                add(field_id, 'The response is unknown and may need additional evidence or clarification.', 'uncertain', name)
    documents = profile.get('evidence_documents', [])
    if not documents:
        add('DEP-035', 'At least one supporting document record is expected.', 'missing', 'Evidence documents')
    for index, document in enumerate(documents, start=1):
        name = f'Supporting Document {index}'
        check_required(document, REQUIRED_DOCUMENT_FIELDS, name)
    if profile.get('DEP-036-trigger') == 'Yes':
        if is_missing(profile.get('DEP-036')):
            add('DEP-036', 'Report whether GMLP principles were considered.', 'conditional', 'GMLP')
        elif profile.get('DEP-036') in ('Yes', 'Partly') and is_missing(profile.get('DEP-036-document')):
            add('DEP-036', 'Identify the document describing GMLP implementation.', 'conditional', 'GMLP')
    return issues
