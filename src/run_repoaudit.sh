#!/bin/bash

print_usage() {
    echo "Usage: $0 <scan-type> [options]"
    echo
    echo "Scan Types:"
    echo "  bugscan    - Perform general bug scanning"
    echo "  dfbscan    - Perform data flow-based scanning"
    echo "  debugscan  - Perform debug scanning"
    echo
    echo "Required Options (for all scan types):"
    echo "  --language <lang>           Language to analyze"
    echo "  --project-path <path>       Path to the project"
    echo
    echo "Required Options (scan-type specific):"
    echo "  --bug-type <type>          Required for dfbscan"
    echo "  --is-reachable             Required for dfbscan"
    echo "  --is-iterative             Required for bugscan"
    echo "  --is-inlined               Optional for bugscan"
    echo
    echo "Optional Options (with defaults):"
    echo "  --model-name <model>          Model to use (default: claude-3.5)"
    echo "  --temperature <temp>          Temperature setting (default: 0.0)"
    echo "  --call-depth <depth>          Call depth (default: 2)"
    echo "  --max-neural-workers <num>    Maximum neural workers (default: 30)"
    echo "  --max-symbolic-workers <num>  Maximum symbolic workers (default: 10)"
    echo "  --include-test-files          Analyze test files in the subject project as well"
    echo
    echo "Example commands:"
    echo "bash $0 bugscan --language Cpp --project-path ../benchmark/Cpp/htop --is-iterative"
    echo "bash $0 bugscan --language Java --project-path ../benchmark/Java/toy --is-iterative"
    echo "bash $0 dfbscan --language Java --project-path ../benchmark/Java/toy --bug-type NPD --is-reachable"
    echo "bash $0 debugscan --language Cpp --project-path ../benchmark/Cpp/htop"
}

# Check for help flag first
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    print_usage
    exit 0
fi

# Check for minimum arguments
if [[ $# -lt 1 ]]; then
    print_usage
    exit 1
fi

# Default values
SCAN_TYPE=$1
shift
MODEL="o4-mini"
TEMPERATURE="0.0"
CALL_DEPTH="3"
MAX_NEURAL_WORKERS="1"
MAX_SYMBOLIC_WORKERS="10"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --language)
            LANGUAGE="$2"
            shift 2
            ;;
        --model-name)
            MODEL="$2"
            shift 2
            ;;
        --project-path)
            PROJECT_PATH="$2"
            shift 2
            ;;
        --bug-type)
            BUG_TYPE="$2"
            shift 2
            ;;
        --temperature)
            TEMPERATURE="$2"
            shift 2
            ;;
        --call-depth)
            CALL_DEPTH="$2"
            shift 2
            ;;
        --max-neural-workers)
            MAX_NEURAL_WORKERS="$2"
            shift 2
            ;;
        --max-symbolic-workers)
            MAX_SYMBOLIC_WORKERS="$2"
            shift 2
            ;;
        --is-reachable)
            IS_REACHABLE="--is-reachable"
            shift
            ;;
        --is-iterative)
            IS_ITERATIVE="--is-iterative"
            shift
            ;;
        --is-inlined)
            IS_INLINED="--is-inlined"
            shift
            ;;
        --include-test-files)
            INCLUDE_TEST_FILES="--include-test-files"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate required arguments for all scan types
if [ -z "$LANGUAGE" ] || [ -z "$PROJECT_PATH" ]; then
    echo "Error: --language and --project-path are required for all scan types"
    print_usage
    exit 1
fi

# Validate scan-type specific requirements
case "$SCAN_TYPE" in
    bugscan)
        if [ -z "$IS_ITERATIVE" ]; then
            echo "Error: --is-iterative is required for bugscan"
            print_usage
            exit 1
        fi
        ;;
    dfbscan)
        if [ -z "$BUG_TYPE" ] || [ -z "$IS_REACHABLE" ]; then
            echo "Error: --bug-type and --is-reachable are required for dfbscan"
            print_usage
            exit 1
        fi
        ;;
    debugscan)
        # No additional requirements for debugscan
        ;;
    *)
        echo "Unknown scan type: $SCAN_TYPE"
        print_usage
        exit 1
        ;;
esac

# Run the appropriate scan based on scan type
case "$SCAN_TYPE" in
    bugscan)
        python3 repoaudit.py \
          --language "$LANGUAGE" \
          --model-name "$MODEL" \
          --project-path "$PROJECT_PATH" \
          --temperature "$TEMPERATURE" \
          --scan-type bugscan \
          --call-depth "$CALL_DEPTH" \
          --max-neural-workers "$MAX_NEURAL_WORKERS" \
          --max-symbolic-workers "$MAX_SYMBOLIC_WORKERS" \
          $IS_ITERATIVE \
          $IS_INLINED \
          $INCLUDE_TEST_FILES
        ;;
    dfbscan)
        python3 repoaudit.py \
          --language "$LANGUAGE" \
          --model-name "$MODEL" \
          --project-path "$PROJECT_PATH" \
          --bug-type "$BUG_TYPE" \
          --temperature "$TEMPERATURE" \
          --scan-type dfbscan \
          --call-depth "$CALL_DEPTH" \
          --max-neural-workers "$MAX_NEURAL_WORKERS" \
          --max-symbolic-workers "$MAX_SYMBOLIC_WORKERS" \
          $IS_REACHABLE \
          $INCLUDE_TEST_FILES
        ;;
    debugscan)
        python3 repoaudit.py \
          --language "$LANGUAGE" \
          --model-name "$MODEL" \
          --project-path "$PROJECT_PATH" \
          --temperature "$TEMPERATURE" \
          --scan-type debugscan \
          --call-depth "$CALL_DEPTH" \
          --max-neural-workers "$MAX_NEURAL_WORKERS" \
          --max-symbolic-workers "$MAX_SYMBOLIC_WORKERS"
        ;;
esac