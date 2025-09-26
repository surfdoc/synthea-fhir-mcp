#!/usr/bin/env python3
"""
Load Synthea FHIR data into PostgreSQL

This script loads synthetic patient data from Synthea output files into
a PostgreSQL database for use with the MCP server.

Usage:
    python load_synthea_data.py --synthea-dir /path/to/synthea/output
"""

import os
import json
import psycopg
from psycopg.rows import dict_row
import argparse
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_connection_string():
    """Get connection string from environment or arguments"""
    return os.getenv("DATABASE_URL", os.getenv("POSTGRES_CONNECTION_STRING", ""))

def create_schema(conn):
    """Create the FHIR schema if it doesn't exist"""
    with conn.cursor() as cur:
        # Create schema
        cur.execute("CREATE SCHEMA IF NOT EXISTS fhir")

        # Create tables for each resource type used by MCP server
        resource_types = [
            'patient', 'observation', 'condition', 'procedure',
            'medication_request', 'allergy_intolerance', 'immunization',
            'encounter'
        ]

        # Additional tables for future use (not currently queried by MCP)
        # Uncomment if needed: 'care_plan', 'diagnostic_report', 'claim'

        for resource_type in resource_types:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS fhir.{resource_type} (
                    id VARCHAR(255) PRIMARY KEY,
                    patient_id VARCHAR(255),
                    resource JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{resource_type}_patient
                ON fhir.{resource_type}(patient_id)
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{resource_type}_resource
                ON fhir.{resource_type} USING gin(resource)
            """)

        conn.commit()
        logger.info("Schema and tables created successfully")

def load_bundle(bundle_path: Path, conn):
    """Load a single FHIR bundle file"""
    try:
        with open(bundle_path, 'r') as f:
            bundle = json.load(f)

        if bundle.get('resourceType') != 'Bundle':
            return 0

        loaded = 0
        patient_id = None

        with conn.cursor() as cur:
            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                resource_type = resource.get('resourceType', '').lower()
                resource_id = resource.get('id')

                if not resource_type or not resource_id:
                    continue

                # Extract patient ID
                if resource_type == 'patient':
                    patient_id = resource_id
                elif 'subject' in resource:
                    patient_id = resource['subject'].get('reference', '').split('/')[-1]
                elif 'patient' in resource:
                    patient_id = resource['patient'].get('reference', '').split('/')[-1]

                # Map to table name
                table_map = {
                    'medicationrequest': 'medication_request',
                    'allergyintolerance': 'allergy_intolerance',
                    'careplan': 'care_plan',
                    'diagnosticreport': 'diagnostic_report'
                }
                table_name = table_map.get(resource_type, resource_type)

                # Skip if table doesn't exist (only load resources we use in MCP)
                if table_name not in ['patient', 'observation', 'condition', 'procedure',
                                     'medication_request', 'allergy_intolerance', 'immunization',
                                     'encounter']:
                    # Skip care_plan, diagnostic_report, claim as they're not used by MCP
                    continue

                # Insert or update
                cur.execute(f"""
                    INSERT INTO fhir.{table_name} (id, patient_id, resource)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET resource = EXCLUDED.resource
                """, (resource_id, patient_id, json.dumps(resource)))

                loaded += 1

        conn.commit()
        return loaded

    except Exception as e:
        logger.error(f"Error loading {bundle_path}: {e}")
        conn.rollback()
        return 0

def load_synthea_output(synthea_dir: Path, conn):
    """Load all FHIR bundles from Synthea output directory"""
    fhir_dir = synthea_dir / "fhir"
    if not fhir_dir.exists():
        logger.error(f"FHIR directory not found: {fhir_dir}")
        return

    bundle_files = list(fhir_dir.glob("*.json"))
    logger.info(f"Found {len(bundle_files)} bundle files")

    total_loaded = 0
    for i, bundle_file in enumerate(bundle_files, 1):
        loaded = load_bundle(bundle_file, conn)
        total_loaded += loaded
        if i % 10 == 0:
            logger.info(f"Processed {i}/{len(bundle_files)} files, loaded {total_loaded} resources")

    logger.info(f"Loading complete: {total_loaded} resources from {len(bundle_files)} files")

    # Show statistics
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 'patient' as type, COUNT(*) as count FROM fhir.patient
            UNION ALL SELECT 'observation', COUNT(*) FROM fhir.observation
            UNION ALL SELECT 'condition', COUNT(*) FROM fhir.condition
            UNION ALL SELECT 'procedure', COUNT(*) FROM fhir.procedure
            UNION ALL SELECT 'medication_request', COUNT(*) FROM fhir.medication_request
            UNION ALL SELECT 'encounter', COUNT(*) FROM fhir.encounter
            ORDER BY count DESC
        """)

        logger.info("\nDatabase statistics:")
        for row in cur.fetchall():
            logger.info(f"  {row['type']}: {row['count']}")

def main():
    parser = argparse.ArgumentParser(description='Load Synthea FHIR data into PostgreSQL')
    parser.add_argument('--synthea-dir', required=True, help='Path to Synthea output directory')
    parser.add_argument('--conn', help='PostgreSQL connection string (or set DATABASE_URL env var)')
    parser.add_argument('--create-schema', action='store_true', help='Create schema and tables')

    args = parser.parse_args()

    # Get connection string
    conn_string = args.conn or get_connection_string()
    if not conn_string:
        logger.error("No connection string provided. Use --conn or set DATABASE_URL")
        return 1

    # Connect to database
    try:
        conn = psycopg.connect(conn_string, row_factory=dict_row)
        logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return 1

    # Create schema if requested
    if args.create_schema:
        create_schema(conn)

    # Load data
    synthea_dir = Path(args.synthea_dir)
    if not synthea_dir.exists():
        logger.error(f"Synthea directory not found: {synthea_dir}")
        return 1

    load_synthea_output(synthea_dir, conn)

    conn.close()
    logger.info("Done!")
    return 0

if __name__ == "__main__":
    exit(main())