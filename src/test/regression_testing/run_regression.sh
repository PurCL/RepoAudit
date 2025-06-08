#!/bin/bash

print_usage() {
    echo "Usage: $0 [options]"
    echo
    echo
    echo "Optional Options (with defaults):"
    echo "  --model <model>        Model to use (default: o3-mini)"
    echo "  --language <language>  Language's suite to run (default: all)"
    echo "  --bug-type <bug type>  Bug type's suite to run (default: all)"
    echo
}

if [ $# -gt 6 ]; then # greater than allowed args
    print_usage
    exit 0
fi

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    print_usage
    exit 0
fi

# default values
LANGUAGE="unspecified"
BUG_TYPE="unspecified"
MODEL="o3-mini-2025-01-31"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --language)
            LANGUAGE="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --bug-type)
            BUG_TYPE="$2"
            shift 2
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

#echo "Language $LANGUAGE"
#echo "Bug type $BUG_TYPE"
#echo "Model $MODEL"

# Default run parameters for running analyzer

# ../../run_repoaudit.sh dfbscan --language Java --project-path ../benchmark/Java/toy --bug-type NPD --is-reachable
# --model-name <model>
# --call-depth <depth>

CALL_DEPTH=3

LANGUAGES=("Python" "Java" "Cpp" "Go")
BUG_TYPES=("NPD" "MLK" "UAF")

# Truncate the file to 0 for this runthrough
truncate -s 0 dif.txt



# Loop through each language, then each bug type
for language in "${LANGUAGES[@]}"; do
    if [ "$language" == "$LANGUAGE" ] || [ "$LANGUAGE" == "unspecified" ]; then
        for bug in "${BUG_TYPES[@]}"; do
            if [ "$BUG_TYPE" == "unspecified" ] || [ "$bug" == "$BUG_TYPE" ]; then
                #compile the the file path for the project based on bug type and language
                project_path="./test/regression_testing/test_files/$language/$bug"
                echo "project path $project_path"
                
                # echo "project path $project_path"
                # echo "Trying " $(realpath $project_path)
                cd ../.. # this is so we can run run_repoaudit.sh
                pwd
                output_file=""
                if [ -d $project_path ]; then # run the analyzer and get the output file
                    echo "Running dfbscan on $language $bug..."
                    
                    bash_output=$(bash ./run_repoaudit.sh dfbscan --language $language --project-path $project_path --bug-type $bug --model-name $MODEL --call-depth $CALL_DEPTH --is-reachable --include-test-files 2>/dev/null)
                    echo "bash output: bash ./run_repoaudit.sh dfbscan --language $language --project-path $project_path --bug-type $bug --model-name $MODEL --call-depth $CALL_DEPTH --is-reachable --include-test-files"
                    output_file=$(echo $bash_output | grep -o '[^[:space:]]*detect_info\.json') 
                    echo "Comparing file $output_file"
                else
                    cd "test/regression_testing"
                    echo "WARNING: The test suite for $language $bug is not implemented"
                    continue
                fi

                
                

                # run it into the difference checker
                cd "test/regression_testing"


                # write a header for this type to the difference file
                echo "Language: $language; Bug Type: $bug" >> dif.txt
                expected_path=$(realpath "./test_files/$language/$bug/expected.json")
                if [ -f $expected_path ]; then
                    python compare_outputs.py --expected $expected_path --output $output_file --differences dif.txt --bug-type $bug
                else
                    echo "WARNING: Expected output file not implemented for $language $bug"
                    continue
                fi

            fi
        done
    fi
done

# Run the difference checker


# Compile all into MD
bash format_differences.sh dif.txt regression_results.md
