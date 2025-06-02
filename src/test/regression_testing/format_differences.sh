#!/bin/bash

# Check if correct number of arguments provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <input_file> <output_file>"
    echo "Example: $0 bugs.txt report.md"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found."
    exit 1
fi

# Create output directory if it doesn't exist
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR"

# Initialize the output file
echo "# Regression Test Report" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Variables to track current bug info
bug_src_info=""
bug_sink_file=""
bug_sink_line=""
bug_sink_code=""
current_language=""
current_bug_type=""
current_section=""
fp_bug_type=""
fp_src_info=""
fp_sink_function=""

# Function to get line from file
get_line_from_file() {
    local filename="$1"
    local line_num="$2"
    local language="$3"
    local bug_type="$4"
    
    # Construct the full path
    local full_path="test_files/${language}/${bug_type}/bad/${filename}"
    
    if [[ -f "$full_path" ]]; then
        sed -n "${line_num}p" "$full_path" 2>/dev/null
    else
        echo "File not found: $full_path"
    fi
}

# Function to extract filename from SRC Info path
extract_filename_from_path() {
    local src_info="$1"
    # Extract filename from path like "((None, ./test/regression_testing/test_files/Python/NPD/bad/test04.py, 2, -1), ValueLabel.SRC)"
    # First extract the path part, then get just the filename
    local path=$(echo "$src_info" | sed 's/.*,\s*\([^,]*\.\(py\|java\|cc\|go\)\)\s*,.*/\1/')
    echo "$path" | sed 's/.*\///'
}

# Function to extract line number from SRC Info
extract_line_from_src_info() {
    local src_info="$1"
    # Extract line number from format like "((None, ./path/file.py, 2, -1), ValueLabel.SRC)"
    # Look for the number that comes after the file path
    echo "$src_info" | sed 's/.*\.\(py\|java\|cc\|go\),\s*\([0-9]\+\)\s*,.*/\2/'
}

# Function to output False Positive bug
output_false_positive_bug() {
    if [[ -n "$fp_src_info" && -n "$fp_bug_type" ]]; then
        # Extract filename and line number from SRC Info
        filename=$(extract_filename_from_path "$fp_src_info")
        line_number=$(extract_line_from_src_info "$fp_src_info")
        
        # Determine language from the path in SRC Info
        if [[ "$fp_src_info" =~ Python ]]; then
            lang="Python"
        elif [[ "$fp_src_info" =~ Java ]]; then
            lang="Java"
        elif [[ "$fp_src_info" =~ Cpp ]]; then
            lang="Cpp"
        elif [[ "$fp_src_info" =~ Go ]]; then
            lang="Go"
        else
            lang="$current_language"
        fi
        
        # Get the source code line
        src_code=$(get_line_from_file "$filename" "$line_number" "$lang" "$fp_bug_type")
        
        echo "**Bug Type:** $fp_bug_type" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "**Source File:** \`$filename\` **Source Line:** $line_number" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "Source Code:" >> "$OUTPUT_FILE"
        echo "\`\`\`python" >> "$OUTPUT_FILE"
        echo "$src_code" >> "$OUTPUT_FILE"
        echo "\`\`\`" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        
        if [[ -n "$fp_sink_function" ]]; then
            echo "Sink Function:" >> "$OUTPUT_FILE"
            echo "\`\`\`python" >> "$OUTPUT_FILE"
            echo "$fp_sink_function" >> "$OUTPUT_FILE"
            echo "\`\`\`" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
        fi
    fi
}

# Function to output False Negative bug
output_false_negative_bug() {
    if [[ -n "$bug_src_info" ]]; then
        filename=$(echo "$bug_src_info" | cut -d'-' -f1)
        line_number=$(echo "$bug_src_info" | cut -d'-' -f2)
        
        # Get the source code line using the full path
        src_code=$(get_line_from_file "$filename" "$line_number" "$current_language" "$current_bug_type")
        
        echo "**Source File:** \`$filename\` **Source Line:** $line_number" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "Source Code:" >> "$OUTPUT_FILE"
        echo "\`\`\`python" >> "$OUTPUT_FILE"
        echo "$src_code" >> "$OUTPUT_FILE"
        echo "\`\`\`" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "**Sink File:** \`$bug_sink_file\` **Sink Line:** $bug_sink_line" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "Sink Code:" >> "$OUTPUT_FILE"
        echo "\`\`\`python" >> "$OUTPUT_FILE"
        echo "$bug_sink_code" >> "$OUTPUT_FILE"
        echo "\`\`\`" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
}

# Read the input file line by line
while IFS= read -r line; do
    # Skip completely empty lines
    if [[ -z "$line" ]]; then
        echo "" >> "$OUTPUT_FILE"
        continue
    fi
    
    # Handle Language/Bug Type header
    if [[ "$line" =~ ^Language:.*Bug\ Type: ]]; then
        language=$(echo "$line" | sed 's/Language: \([^;]*\);.*/\1/' | xargs)
        bug_type=$(echo "$line" | sed 's/.*Bug Type: \(.*\)/\1/' | xargs)
        
        # Store current language and bug type for file path construction
        current_language="$language"
        current_bug_type="$bug_type"
        
        echo "## $language - $bug_type" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        continue
    fi
    
    # Handle section headers (False Negatives, False Positives, etc.)
    if [[ "$line" =~ ^[A-Za-z\ ]+:$ ]]; then
        # Output any pending bugs before switching sections
        if [[ "$current_section" == "False Positives" ]]; then
            output_false_positive_bug
        elif [[ "$current_section" == "False Negatives" ]]; then
            output_false_negative_bug
        fi
        
        # Reset variables for new section
        fp_bug_type=""
        fp_src_info=""
        fp_sink_function=""
        bug_src_info=""
        bug_sink_file=""
        bug_sink_line=""
        bug_sink_code=""
        
        section_name=$(echo "$line" | sed 's/://')
        current_section="$section_name"
        echo "### $section_name" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        continue
    fi
    
    # Handle False Positive entries
    if [[ "$current_section" == "False Positives" ]]; then
        if [[ "$line" =~ ^Bug\ Type: ]]; then
            # Output previous bug if exists
            output_false_positive_bug
            
            # Reset and start new bug
            fp_bug_type=$(echo "$line" | sed 's/Bug Type: //')
            fp_src_info=""
            fp_sink_function=""
            continue
        elif [[ "$line" =~ ^SRC\ Info: ]]; then
            fp_src_info=$(echo "$line" | sed 's/SRC Info: //')
            continue
        elif [[ "$line" =~ ^Sink\ Function: ]]; then
            # Start collecting sink function (multiline)
            fp_sink_function=$(echo "$line" | sed 's/Sink Function: //')
            continue
        elif [[ -n "$fp_sink_function" && ! "$line" =~ ^Bug\ Type: && ! "$line" =~ ^SRC\ Info: ]]; then
            # Continue collecting multiline sink function
            fp_sink_function="$fp_sink_function"$'\n'"$line"
            continue
        fi
    fi
    
    # Handle False Negative entries (existing logic)
    if [[ "$current_section" == "False Negatives" ]]; then
        # Handle Bug SRC Info
        if [[ "$line" =~ ^Bug\ SRC\ Info: ]]; then
            # If we have a previous bug, output it first
            output_false_negative_bug
            
            # Store new bug source info
            bug_src_info=$(echo "$line" | sed 's/Bug SRC Info: //')
            # Reset other variables
            bug_sink_file=""
            bug_sink_line=""
            bug_sink_code=""
            continue
        fi
        
        # Handle Bug Sink File
        if [[ "$line" =~ ^Bug\ Sink\ File: ]]; then
            bug_sink_file=$(echo "$line" | sed 's/Bug Sink File: //')
            continue
        fi
        
        # Handle Bug Sink Line Number
        if [[ "$line" =~ ^Bug\ Sink\ Line\ Number: ]]; then
            bug_sink_line=$(echo "$line" | sed 's/Bug Sink Line Number: //')
            continue
        fi
        
        # Handle Bug Sink Code
        if [[ "$line" =~ ^Bug\ Sink\ Code: ]]; then
            bug_sink_code=$(echo "$line" | sed 's/Bug Sink Code: //')
            continue
        fi
    fi
    
    # Handle any other lines as regular text (only if not part of bug entries)
    if [[ ! "$line" =~ ^Bug\ (SRC|Sink|Type) && ! "$line" =~ ^SRC\ Info: && ! "$line" =~ ^Sink\ Function: ]]; then
        echo "$line" >> "$OUTPUT_FILE"
    fi
    
done < "$INPUT_FILE"

# Output the last bug if exists
if [[ "$current_section" == "False Positives" ]]; then
    output_false_positive_bug
elif [[ "$current_section" == "False Negatives" ]]; then
    output_false_negative_bug
fi

echo "✅ Report formatted and saved to: $OUTPUT_FILE"