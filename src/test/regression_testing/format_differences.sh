#!/bin/bash

# Bug Analysis Data Formatter
# Usage: ./format_bug_data.sh input_file output_file

if [ $# -ne 2 ]; then
    echo "Usage: $0 <input_file> <output_file>"
    echo "Example: $0 bug_data.txt formatted_report.txt"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found!"
    exit 1
fi

# Create/clear output file
> "$OUTPUT_FILE"

# Function to add section separator
add_separator() {
    echo "════════════════════════════════════════════════════════════════════════════════" >> "$OUTPUT_FILE"
}

# Function to add subsection separator
add_subseparator() {
    echo "────────────────────────────────────────────────────────────────────────────────" >> "$OUTPUT_FILE"
}

# Start formatting
echo "BUG ANALYSIS REPORT" >> "$OUTPUT_FILE"
echo "Generated on: $(date)" >> "$OUTPUT_FILE"
add_separator
echo "" >> "$OUTPUT_FILE"

# Process the input file
current_language=""
current_bug_type=""
in_false_positives=false
in_false_negatives=false

while IFS= read -r line; do
    # Skip empty lines in certain contexts
    if [[ -z "$line" ]] && [[ "$in_false_positives" == false ]] && [[ "$in_false_negatives" == false ]]; then
        continue
    fi
    
    # Detect language and bug type
    if [[ "$line" =~ ^Language:.*Bug\ Type: ]]; then
        if [[ -n "$current_language" ]]; then
            echo "" >> "$OUTPUT_FILE"
            add_separator
            echo "" >> "$OUTPUT_FILE"
        fi
        
        current_language=$(echo "$line" | sed 's/Language: \([^;]*\);.*/\1/')
        current_bug_type=$(echo "$line" | sed 's/.*Bug Type: \(.*\)/\1/')
        
        echo "📊 ANALYSIS: $current_language - $current_bug_type" >> "$OUTPUT_FILE"
        add_subseparator
        in_false_positives=false
        in_false_negatives=false
        
    # Format statistics
    elif [[ "$line" =~ ^True\ Positives: ]]; then
        tp=$(echo "$line" | sed 's/True Positives: //')
        echo "✅ True Positives:  $tp" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^False\ Positives: ]]; then
        fp=$(echo "$line" | sed 's/False Positives: //')
        echo "❌ False Positives: $fp" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Total\ Expected\ Positives: ]]; then
        tep=$(echo "$line" | sed 's/Total Expected Positives: //')
        echo "📈 Expected Total:  $tep" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Precision: ]]; then
        precision=$(echo "$line" | sed 's/Precision: //')
        precision_percent=$(echo "$precision * 100" | bc -l | xargs printf "%.1f")
        echo "🎯 Precision:      $precision_percent%" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Recall: ]]; then
        recall=$(echo "$line" | sed 's/Recall: //')
        recall_percent=$(echo "$recall * 100" | bc -l | xargs printf "%.1f")
        echo "🔍 Recall:         $recall_percent%" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^F1\ Score: ]]; then
        f1=$(echo "$line" | sed 's/F1 Score: //')
        f1_percent=$(echo "$f1 * 100" | bc -l | xargs printf "%.1f")
        echo "⚖️  F1 Score:       $f1_percent%" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        
    # Handle False Positives section
    elif [[ "$line" == "False Positives:" ]]; then
        in_false_positives=true
        in_false_negatives=false
        echo "🚨 FALSE POSITIVES:" >> "$OUTPUT_FILE"
        
    # Handle False Negatives section
    elif [[ "$line" == "False Negatives:" ]]; then
        in_false_positives=false
        in_false_negatives=true
        echo "" >> "$OUTPUT_FILE"
        echo "⚠️  FALSE NEGATIVES:" >> "$OUTPUT_FILE"
        
    # Process bug details
    elif [[ "$line" =~ ^Bug\ Type: ]] && [[ "$in_false_positives" == true || "$in_false_negatives" == true ]]; then
        echo "" >> "$OUTPUT_FILE"
        echo "   • Bug Type: $(echo "$line" | sed 's/Bug Type: //')" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^SRC\ Info: ]]; then
        src_info=$(echo "$line" | sed 's/SRC Info: //' | sed 's/((.*,//' | sed 's/, [^,]*)).*$//')
        echo "     Source: $src_info" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Sink\ Function: ]]; then
        echo "     Function:" >> "$OUTPUT_FILE"
        echo "     ┌─────────────────────────────────────────────────────────────────────┐" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Bug\ SRC\ Info: ]]; then
        src_info=$(echo "$line" | sed 's/Bug SRC Info: //')
        echo "   • Source: $src_info" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Bug\ Sink\ File: ]]; then
        sink_file=$(echo "$line" | sed 's/Bug Sink File: //')
        echo "     File: $sink_file" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Bug\ Sink\ Line\ Number: ]]; then
        line_num=$(echo "$line" | sed 's/Bug Sink Line Number: //')
        echo "     Line: $line_num" >> "$OUTPUT_FILE"
        
    elif [[ "$line" =~ ^Bug\ Sink\ Code: ]]; then
        code=$(echo "$line" | sed 's/Bug Sink Code: //')
        echo "     Code: $code" >> "$OUTPUT_FILE"
        
    # Handle function code (indented lines)
    elif [[ "$in_false_positives" == true ]] && [[ "$line" =~ ^[[:space:]] ]]; then
        if [[ "$line" =~ ^[[:space:]]*}[[:space:]]*$ ]]; then
            echo "     │ $line" >> "$OUTPUT_FILE"
            echo "     └─────────────────────────────────────────────────────────────────────┘" >> "$OUTPUT_FILE"
        else
            echo "     │ $line" >> "$OUTPUT_FILE"
        fi
        
    # Handle empty lines in false positives/negatives sections
    elif [[ -z "$line" ]] && [[ "$in_false_positives" == true || "$in_false_negatives" == true ]]; then
        echo "" >> "$OUTPUT_FILE"
    fi
    
done < "$INPUT_FILE"

# Add final separator
echo "" >> "$OUTPUT_FILE"
add_separator
echo "" >> "$OUTPUT_FILE"
echo "📋 SUMMARY" >> "$OUTPUT_FILE"
echo "Report generated from: $INPUT_FILE" >> "$OUTPUT_FILE"
echo "Total languages analyzed: $(grep -c "^Language:" "$INPUT_FILE")" >> "$OUTPUT_FILE"
echo "Generated on: $(date)" >> "$OUTPUT_FILE"

echo "✨ Formatted report saved to: $OUTPUT_FILE"
echo "📊 Processing complete!"