#!/bin/bash

# Synthea FHIR Data Generation Wrapper
# Simple bash script for quick data generation with defaults

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏥 Synthea FHIR Data Generator (Quick Start)${NC}"
echo "=========================================="

# Check for Java
echo -n "Checking Java installation... "
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2)
    echo -e "${GREEN}✓${NC} Found Java $JAVA_VERSION"

    # Extract major version
    MAJOR_VERSION=$(echo $JAVA_VERSION | cut -d'.' -f1)
    if [[ "$MAJOR_VERSION" == "1" ]]; then
        MAJOR_VERSION=$(echo $JAVA_VERSION | cut -d'.' -f2)
    fi

    if [[ $MAJOR_VERSION -lt 11 ]]; then
        echo -e "${YELLOW}⚠️  Warning: Java 11+ required, you have Java $MAJOR_VERSION${NC}"
        echo "Please upgrade Java before continuing."
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Java not found!"
    echo ""
    echo "Please install Java 11 or higher:"
    echo "  macOS:  brew install openjdk@11"
    echo "  Ubuntu: sudo apt-get install openjdk-11-jdk"
    echo "  RHEL:   sudo yum install java-11-openjdk"
    exit 1
fi

# Default values
POPULATION=${1:-100}
STATE=${2:-"Massachusetts"}
SEED=${3:-""}

# Usage help
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo ""
    echo "Usage: $0 [POPULATION] [STATE] [SEED]"
    echo ""
    echo "Arguments:"
    echo "  POPULATION  Number of patients to generate (default: 100)"
    echo "  STATE       US state name (default: Massachusetts)"
    echo "  SEED        Random seed for reproducible data (optional)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Generate 100 patients in Massachusetts"
    echo "  $0 500                # Generate 500 patients in Massachusetts"
    echo "  $0 200 California     # Generate 200 patients in California"
    echo "  $0 100 Texas 12345    # Generate with seed for reproducibility"
    echo ""
    exit 0
fi

echo ""
echo "Configuration:"
echo "  Population: $POPULATION patients"
echo "  State: $STATE"
if [[ -n "$SEED" ]]; then
    echo "  Seed: $SEED (reproducible)"
fi
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Run the Python script with arguments
echo "Starting Synthea data generation..."
echo "----------------------------------------"

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

CMD="$PYTHON_CMD $SCRIPT_DIR/generate_synthea_data.py --population $POPULATION --state \"$STATE\""

if [[ -n "$SEED" ]]; then
    CMD="$CMD --seed $SEED"
fi

echo "Running: $CMD"
echo ""

# Execute the Python script
eval $CMD

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Data generation complete!${NC}"
    echo ""
    echo "To load the data into PostgreSQL:"
    echo "  export DATABASE_URL='postgresql://user:pass@localhost:5432/synthea'"
    echo "  python scripts/load_synthea_data.py --synthea-dir synthea/output"
else
    echo ""
    echo -e "${RED}❌ Data generation failed!${NC}"
    echo "Please check the error messages above."
fi

exit $EXIT_CODE