# DATA_MODEL.md

## Tablas principales

### `cases`
- id UUID
- canonical_case_number
- jurisdiction
- subject_matter
- opened_at
- closed_at
- status
- data_confidence

### `case_identifiers`
Permite múltiples números para un mismo ciclo procesal.
- id
- case_id
- identifier
- court_id
- identifier_type

### `courts`
- id
- canonical_name
- court_type
- chamber
- department
- municipality
- valid_from
- valid_to

### `judicial_officers`
- id
- canonical_name
- role
- valid_from
- valid_to

### `court_assignments`
- judicial_officer_id
- court_id
- role
- start_date
- end_date
- source_document_id

### `documents`
- id
- source_id
- source_url
- retrieved_at
- sha256
- mime_type
- local_path
- text_path
- parser_version
- publication_status

### `decisions`
- id
- case_id
- document_id
- court_id
- decision_date
- decision_type
- literal_outcome
- normalized_effect
- lower_decision_id
- filing_date
- data_confidence

### `decision_officers`
- decision_id
- judicial_officer_id
- role: signer/ponente/member/dissent

### `parties`
- id
- canonical_name
- party_type

### `case_parties`
- case_id
- party_id
- procedural_role

### `offenses`
- id
- canonical_name
- legal_basis
- taxonomy_group

### `case_offenses`
- case_id
- offense_id
- status

### `events`
- id
- case_id
- event_type
- event_date
- court_id
- decision_id
- source_document_id

### `appeal_links`
- id
- source_decision_id
- target_decision_id
- relation_type
- confidence
- validation_status

### `citations`
- citing_decision_id
- cited_case_number
- cited_decision_id nullable
- citation_text
- confidence

### `evidence_spans`
- id
- entity_type
- entity_id
- field_name
- document_id
- page
- char_start
- char_end
- evidence_text
- extraction_confidence

### `classifications`
Para etiquetas analíticas separadas de hechos jurídicos.
- id
- case_id/decision_id
- taxonomy
- label
- method
- confidence
- reviewer

## Regla fundamental
Nunca sobrescribir el valor original extraído. Las correcciones generan una nueva versión o registro de auditoría.
