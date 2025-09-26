"""
FHIR resource fixtures for testing.
"""

import json
from datetime import datetime, timedelta
import random


def create_patient_resource(patient_id="test-patient-123"):
    """Create a sample FHIR Patient resource."""
    return {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "urn:oid:2.16.840.1.113883.4.3.25",
                "value": "999-99-9999"
            },
            {
                "system": "https://github.com/synthetichealth/synthea",
                "value": patient_id
            }
        ],
        "name": [
            {
                "use": "official",
                "family": "TestPatient",
                "given": ["John", "Q"],
                "prefix": ["Mr."]
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": "555-123-4567",
                "use": "home"
            },
            {
                "system": "email",
                "value": "john.testpatient@example.com"
            }
        ],
        "gender": "male",
        "birthDate": "1970-01-01",
        "address": [
            {
                "use": "home",
                "line": ["123 Test Street", "Apt 4B"],
                "city": "Boston",
                "state": "MA",
                "postalCode": "02101",
                "country": "US"
            }
        ],
        "maritalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                    "code": "M",
                    "display": "Married"
                }
            ]
        }
    }


def create_observation_resource(patient_id="test-patient-123", obs_type="blood_pressure"):
    """Create a sample FHIR Observation resource."""
    observations = {
        "blood_pressure": {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel"
                    }
                ]
            },
            "component": [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure"
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": 120,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    }
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure"
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": 80,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    }
                }
            ]
        },
        "heart_rate": {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8867-4",
                        "display": "Heart rate"
                    }
                ]
            },
            "valueQuantity": {
                "value": 72,
                "unit": "beats/min",
                "system": "http://unitsofmeasure.org",
                "code": "/min"
            }
        },
        "glucose": {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "2339-0",
                        "display": "Glucose [Mass/volume] in Blood"
                    }
                ]
            },
            "valueQuantity": {
                "value": 95,
                "unit": "mg/dL",
                "system": "http://unitsofmeasure.org",
                "code": "mg/dL"
            }
        }
    }

    obs = observations.get(obs_type, observations["blood_pressure"])

    base_observation = {
        "resourceType": "Observation",
        "id": f"obs-{patient_id}-{obs_type}",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": datetime.now().isoformat(),
        "performer": [
            {
                "reference": "Practitioner/test-practitioner"
            }
        ]
    }

    base_observation.update(obs)
    return base_observation


def create_condition_resource(patient_id="test-patient-123", condition_type="diabetes"):
    """Create a sample FHIR Condition resource."""
    conditions = {
        "diabetes": {
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "44054006",
                        "display": "Type 2 diabetes mellitus"
                    }
                ]
            },
            "severity": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "6736007",
                        "display": "Moderate"
                    }
                ]
            }
        },
        "hypertension": {
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "38341003",
                        "display": "Hypertensive disorder"
                    }
                ]
            }
        },
        "asthma": {
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "195967001",
                        "display": "Asthma"
                    }
                ]
            }
        }
    }

    condition_data = conditions.get(condition_type, conditions["diabetes"])

    return {
        "resourceType": "Condition",
        "id": f"condition-{patient_id}-{condition_type}",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed"
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": "encounter-diagnosis",
                        "display": "Encounter Diagnosis"
                    }
                ]
            }
        ],
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "onsetDateTime": (datetime.now() - timedelta(days=365)).isoformat(),
        **condition_data
    }


def create_immunization_resource(patient_id="test-patient-123", vaccine_type="covid"):
    """Create a sample FHIR Immunization resource."""
    vaccines = {
        "covid": {
            "vaccineCode": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/cvx",
                        "code": "208",
                        "display": "COVID-19 vaccine, mRNA"
                    }
                ]
            },
            "manufacturer": {
                "reference": "Organization/pfizer"
            },
            "lotNumber": "EL9269"
        },
        "flu": {
            "vaccineCode": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/cvx",
                        "code": "141",
                        "display": "Influenza, seasonal, injectable"
                    }
                ]
            }
        },
        "tdap": {
            "vaccineCode": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/cvx",
                        "code": "115",
                        "display": "Tdap"
                    }
                ]
            }
        }
    }

    vaccine_data = vaccines.get(vaccine_type, vaccines["covid"])

    return {
        "resourceType": "Immunization",
        "id": f"immunization-{patient_id}-{vaccine_type}",
        "status": "completed",
        "patient": {
            "reference": f"Patient/{patient_id}"
        },
        "occurrenceDateTime": (datetime.now() - timedelta(days=30)).isoformat(),
        "recorded": datetime.now().isoformat(),
        "primarySource": True,
        "location": {
            "reference": "Location/test-clinic"
        },
        "route": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-RouteOfAdministration",
                    "code": "IM",
                    "display": "Intramuscular"
                }
            ]
        },
        "doseQuantity": {
            "value": 0.3,
            "unit": "mL",
            "system": "http://unitsofmeasure.org",
            "code": "mL"
        },
        **vaccine_data
    }


def create_medication_request_resource(patient_id="test-patient-123", medication="metformin"):
    """Create a sample FHIR MedicationRequest resource."""
    medications = {
        "metformin": {
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": "860975",
                        "display": "metformin hydrochloride 500 MG Oral Tablet"
                    }
                ]
            },
            "dosageInstruction": [
                {
                    "text": "Take 1 tablet twice daily with meals",
                    "timing": {
                        "repeat": {
                            "frequency": 2,
                            "period": 1,
                            "periodUnit": "d"
                        }
                    },
                    "doseAndRate": [
                        {
                            "doseQuantity": {
                                "value": 500,
                                "unit": "mg",
                                "system": "http://unitsofmeasure.org",
                                "code": "mg"
                            }
                        }
                    ]
                }
            ]
        },
        "lisinopril": {
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": "314076",
                        "display": "lisinopril 10 MG Oral Tablet"
                    }
                ]
            },
            "dosageInstruction": [
                {
                    "text": "Take 1 tablet daily",
                    "timing": {
                        "repeat": {
                            "frequency": 1,
                            "period": 1,
                            "periodUnit": "d"
                        }
                    }
                }
            ]
        }
    }

    med_data = medications.get(medication, medications["metformin"])

    return {
        "resourceType": "MedicationRequest",
        "id": f"medreq-{patient_id}-{medication}",
        "status": "active",
        "intent": "order",
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "authoredOn": datetime.now().isoformat(),
        "requester": {
            "reference": "Practitioner/test-practitioner"
        },
        **med_data
    }


def create_procedure_resource(patient_id="test-patient-123", procedure_type="colonoscopy"):
    """Create a sample FHIR Procedure resource."""
    procedures = {
        "colonoscopy": {
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "73761001",
                        "display": "Colonoscopy"
                    }
                ]
            }
        },
        "appendectomy": {
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "80146002",
                        "display": "Appendectomy"
                    }
                ]
            }
        }
    }

    proc_data = procedures.get(procedure_type, procedures["colonoscopy"])

    return {
        "resourceType": "Procedure",
        "id": f"procedure-{patient_id}-{procedure_type}",
        "status": "completed",
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "performedDateTime": (datetime.now() - timedelta(days=90)).isoformat(),
        **proc_data
    }


def create_encounter_resource(patient_id="test-patient-123"):
    """Create a sample FHIR Encounter resource."""
    return {
        "resourceType": "Encounter",
        "id": f"encounter-{patient_id}",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory"
        },
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "308335008",
                        "display": "Patient encounter procedure"
                    }
                ]
            }
        ],
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "period": {
            "start": (datetime.now() - timedelta(hours=2)).isoformat(),
            "end": (datetime.now() - timedelta(hours=1)).isoformat()
        },
        "reasonCode": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "161891005",
                        "display": "Backache"
                    }
                ]
            }
        ]
    }


def create_allergy_intolerance_resource(patient_id="test-patient-123"):
    """Create a sample FHIR AllergyIntolerance resource."""
    return {
        "resourceType": "AllergyIntolerance",
        "id": f"allergy-{patient_id}",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": "active"
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "confirmed"
                }
            ]
        },
        "type": "allergy",
        "category": ["medication"],
        "criticality": "high",
        "code": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "7980",
                    "display": "Penicillin"
                }
            ]
        },
        "patient": {
            "reference": f"Patient/{patient_id}"
        },
        "onsetDateTime": (datetime.now() - timedelta(days=3650)).isoformat(),
        "reaction": [
            {
                "manifestation": [
                    {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "39579001",
                                "display": "Anaphylaxis"
                            }
                        ]
                    }
                ],
                "severity": "severe"
            }
        ]
    }