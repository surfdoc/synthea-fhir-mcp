# FHIR Database Schema Guide

## Database Structure

All FHIR resources are stored in PostgreSQL tables with a JSONB `resource` column containing the full FHIR resource.

### Table Structure
```sql
-- Each FHIR resource type has its own table
fhir.patient           -- Patient demographics
fhir.observation       -- Vital signs, lab results
fhir.condition         -- Diagnoses/conditions
fhir.procedure         -- Medical procedures
fhir.medication_request -- Prescriptions
fhir.encounter         -- Clinical visits
fhir.immunization      -- Vaccinations
fhir.allergy_intolerance -- Allergies

-- Common columns in each table:
id           TEXT PRIMARY KEY  -- FHIR resource ID
resource     JSONB             -- Complete FHIR resource as JSON
patient_id   TEXT              -- Reference to patient (except patient table)
```

## Querying JSONB Data

### Basic JSONB Operators
- `->` : Get JSON object field (returns JSON)
- `->>` : Get JSON object field as text
- `#>` : Get JSON at specified path (returns JSON)
- `#>>` : Get JSON at specified path as text
- `@>` : Contains operator for matching

## Resource-Specific Query Patterns

### Immunizations (Vaccinations)

```sql
-- Get all immunizations for a patient
SELECT
    resource->>'id' as immunization_id,
    resource->'vaccineCode'->'coding'->0->>'display' as vaccine_name,
    resource->'vaccineCode'->'coding'->0->>'code' as cvx_code,
    resource->>'occurrenceDateTime' as date_given,
    resource->>'status' as status
FROM fhir.immunization
WHERE patient_id = 'PATIENT_ID';

-- Find all flu vaccinations
SELECT
    patient_id,
    resource->'vaccineCode'->'coding'->0->>'display' as vaccine_name,
    resource->>'occurrenceDateTime' as date_given
FROM fhir.immunization
WHERE resource->'vaccineCode'->'text' ? 'Influenza'
   OR resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%flu%'
   OR resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%influenza%';

-- Find COVID-19 vaccinations
SELECT
    patient_id,
    resource->'vaccineCode'->'coding'->0->>'display' as vaccine_name,
    resource->>'occurrenceDateTime' as date_given
FROM fhir.immunization
WHERE resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%COVID%'
   OR resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%SARS-CoV-2%';

-- Count vaccinations by type
SELECT
    resource->'vaccineCode'->'coding'->0->>'display' as vaccine_type,
    COUNT(*) as count
FROM fhir.immunization
GROUP BY vaccine_type
ORDER BY count DESC;
```

### Conditions (Diagnoses)

```sql
-- Get patient conditions
SELECT
    resource->>'id' as condition_id,
    resource->'code'->'coding'->0->>'display' as condition_name,
    resource->'code'->'coding'->0->>'code' as snomed_code,
    resource->>'onsetDateTime' as onset_date,
    resource->'clinicalStatus'->'coding'->0->>'code' as status
FROM fhir.condition
WHERE patient_id = 'PATIENT_ID';

-- Find patients with diabetes
SELECT DISTINCT patient_id
FROM fhir.condition
WHERE resource->'code'->'coding'->0->>'display' ILIKE '%diabetes%'
   OR resource->'code'->'coding'->0->>'code' IN ('44054006', '73211009'); -- SNOMED codes for diabetes
```

### Observations (Vitals & Labs)

```sql
-- Get blood pressure readings
SELECT
    patient_id,
    resource->>'effectiveDateTime' as reading_date,
    resource->'component'->0->'valueQuantity'->>'value' as systolic,
    resource->'component'->1->'valueQuantity'->>'value' as diastolic
FROM fhir.observation
WHERE resource->'code'->'coding'->0->>'code' = '85354-9'; -- LOINC code for BP

-- Get BMI values
SELECT
    patient_id,
    resource->>'effectiveDateTime' as date,
    resource->'valueQuantity'->>'value' as bmi_value
FROM fhir.observation
WHERE resource->'code'->'coding'->0->>'code' = '39156-5'; -- LOINC code for BMI

-- Get lab results (e.g., glucose)
SELECT
    patient_id,
    resource->>'effectiveDateTime' as date,
    resource->'valueQuantity'->>'value' as glucose_value,
    resource->'valueQuantity'->>'unit' as unit
FROM fhir.observation
WHERE resource->'code'->'coding'->0->>'code' = '2339-0'; -- LOINC code for glucose
```

### Medications

```sql
-- Get active medications
SELECT
    patient_id,
    resource->'medicationCodeableConcept'->'text' as medication_name,
    resource->'medicationCodeableConcept'->'coding'->0->>'code' as rxnorm_code,
    resource->>'authoredOn' as prescribed_date,
    resource->>'status' as status
FROM fhir.medication_request
WHERE patient_id = 'PATIENT_ID'
  AND resource->>'status' = 'active';

-- Find patients on specific medication
SELECT DISTINCT patient_id
FROM fhir.medication_request
WHERE resource->'medicationCodeableConcept'->'text' ILIKE '%metformin%';
```

### Patient Demographics

```sql
-- Get patient details
SELECT
    id as patient_id,
    resource->>'birthDate' as birth_date,
    resource->'name'->0->'given'->0 as first_name,
    resource->'name'->0->>'family' as last_name,
    resource->>'gender' as gender,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, (resource->>'birthDate')::date)) as age
FROM fhir.patient
WHERE id = 'PATIENT_ID';
```

## Common Query Patterns

### 1. Search by Text in JSONB
```sql
-- Search for any resource containing specific text
SELECT * FROM fhir.immunization
WHERE resource::text ILIKE '%influenza%';
```

### 2. Array Access in JSONB
```sql
-- First element of array: ->0
-- All elements: Use jsonb_array_elements()
SELECT
    resource->'coding'->0->>'display' as first_coding,
    jsonb_array_elements(resource->'coding')->>'display' as all_codings
FROM fhir.condition;
```

### 3. Nested Path Access
```sql
-- Use #> for deep paths
SELECT resource #> '{vaccineCode,coding,0,display}' as vaccine_name
FROM fhir.immunization;
```

### 4. Date Filtering
```sql
-- Resources from last year
SELECT * FROM fhir.immunization
WHERE (resource->>'occurrenceDateTime')::date > CURRENT_DATE - INTERVAL '1 year';
```

## Code Systems Reference

### Common Code Systems in the Data
- **SNOMED CT**: Conditions/diagnoses (e.g., '44054006' = Diabetes Type 2)
- **LOINC**: Lab tests & observations (e.g., '85354-9' = Blood Pressure)
- **RxNorm**: Medications (e.g., '6809' = Metformin)
- **CVX**: Vaccines (e.g., '140' = Influenza vaccine)
- **CPT**: Procedures

## Tips for LLMs

1. **Always check multiple fields** when searching - vaccine names might be in:
   - `resource->'vaccineCode'->'text'`
   - `resource->'vaccineCode'->'coding'->0->>'display'`
   - `resource->'vaccineCode'->'coding'->0->>'code'`

2. **Use ILIKE for text searches** - case-insensitive pattern matching

3. **Handle arrays properly** - FHIR often uses arrays, access with `->0` for first element

4. **Check status fields** - Many resources have status (active, completed, entered-in-error)

5. **Use DISTINCT** when finding patients to avoid duplicates

## Example Complex Queries

### Find patients with diabetes who got flu shots
```sql
SELECT DISTINCT c.patient_id,
       p.resource->'name'->0->'given'->0 as first_name,
       p.resource->'name'->0->>'family' as last_name
FROM fhir.condition c
JOIN fhir.immunization i ON c.patient_id = i.patient_id
JOIN fhir.patient p ON c.patient_id = p.id
WHERE c.resource->'code'->'coding'->0->>'display' ILIKE '%diabetes%'
  AND i.resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%influenza%';
```

### Population health: Vaccination rates
```sql
WITH patient_count AS (
    SELECT COUNT(DISTINCT id) as total_patients FROM fhir.patient
),
vaccinated AS (
    SELECT
        resource->'vaccineCode'->'coding'->0->>'display' as vaccine_type,
        COUNT(DISTINCT patient_id) as vaccinated_patients
    FROM fhir.immunization
    WHERE resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%influenza%'
    GROUP BY vaccine_type
)
SELECT
    vaccine_type,
    vaccinated_patients,
    total_patients,
    ROUND((vaccinated_patients::numeric / total_patients * 100), 2) as vaccination_rate
FROM vaccinated, patient_count;
```

## Debugging Tips

1. **Check what's in the resource**:
```sql
-- See full JSON structure
SELECT jsonb_pretty(resource) FROM fhir.immunization LIMIT 1;
```

2. **List all vaccine types in database**:
```sql
SELECT DISTINCT
    resource->'vaccineCode'->'coding'->0->>'display' as vaccine_name,
    resource->'vaccineCode'->'coding'->0->>'code' as code
FROM fhir.immunization
ORDER BY vaccine_name;
```

3. **Check if field exists**:
```sql
SELECT COUNT(*)
FROM fhir.immunization
WHERE resource ? 'vaccineCode';
```