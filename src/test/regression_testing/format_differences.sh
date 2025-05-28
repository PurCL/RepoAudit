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
        section_name=$(echo "$line" | sed 's/://')
        echo "### $section_name" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        continue
    fi
    
    # Handle Bug SRC Info
    if [[ "$line" =~ ^Bug\ SRC\ Info: ]]; then
        # If we have a previous bug, output it first
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
    
    # Handle any other lines as regular text
    if [[ ! "$line" =~ ^Bug\ (SRC|Sink) ]]; then
        echo "$line" >> "$OUTPUT_FILE"
    fi
    
done < "$INPUT_FILE"

# Output the last bug if exists
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

echo "✅ Report formatted and saved to: $OUTPUT_FILE"