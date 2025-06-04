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

current_stats_table=""
current_false_positive=""
current_false_negative=""
false_positives=false
false_negatives=false
current_bug_type=""
current_language=""
current_fn_file=""
current_fn_line_num=""

num_true_positives=0
num_false_positives=0
num_correct_total=0

while IFS= read -r line; do
    # check if new section
    if [[ "$line" =~ ^Language:[[:space:]]*([^\;]+)\;[[:space:]]*Bug\ Type:[[:space:]]*(.+)$ ]]; then
        current_language="${BASH_REMATCH[1]}"
        current_bug_type="${BASH_REMATCH[2]}"
        echo "## $current_language - $current_bug_type" >> "$OUTPUT_FILE"
        false_positives=false
        false_negatives=false
        continue
    fi

    if [ "$false_negatives" = false ] && [ "$false_positives" = false ]; then

        #start the table
        if [[ "$line" =~ ^True[[:space:]]*Positives:[[:space:]]*([0-9]+)[[:space:]]*$ ]]; then 
            current_stats_table=""
            current_stats_table+="| Statistic | Value |\n"
            current_stats_table+="|-----------|-------|\n"
            current_stats_table+="| True Positives | ${BASH_REMATCH[1]} |\n"
            num_true_positives=$((num_true_positives + "${BASH_REMATCH[1]}"))
            continue
        fi

        if [[ "$line" =~ ^False[[:space:]]*Positives:[[:space:]]*([0-9]+)[[:space:]]*$ ]]; then
            current_stats_table+="| False Positives | ${BASH_REMATCH[1]} |\n"
            num_false_positives=$((num_false_positives + "${BASH_REMATCH[1]}"))
            continue
        fi

        if [[ "$line" =~ ^Total[[:space:]]*Expected[[:space:]]*Positives:[[:space:]]*([0-9]+)[[:space:]]*$ ]]; then
            current_stats_table+="| Expected Positives | ${BASH_REMATCH[1]} |\n"
            num_correct_total=$((num_correct_total + "${BASH_REMATCH[1]}"))
            continue
        fi

        if [[ "$line" =~ ^Precision:[[:space:]]*([0-9\.]+)[[:space:]]*$ ]]; then
            current_stats_table+="| Precision | ${BASH_REMATCH[1]} |\n"
            continue
        fi

        if [[ "$line" =~ ^Recall:[[:space:]]*([0-9\.]+)[[:space:]]*$ ]]; then
            current_stats_table+="| Recall | ${BASH_REMATCH[1]} |\n"
            continue
        fi

        # finish the table
        if [[ "$line" =~ ^F1[[:space:]]*Score:[[:space:]]*([0-9\.]+)[[:space:]]*$ ]]; then
            current_stats_table+="| F1 Score | ${BASH_REMATCH[1]} |\n"
            echo "### Statistics" >> "$OUTPUT_FILE"
            echo -e "$current_stats_table" >> "$OUTPUT_FILE" # -e treats newlines correctly
            continue
        fi

    fi

    # change section if necessary

    if [[ "$line" =~ ^False[[:space:]]*Positives:[[:space:]]*$ ]]; then
        false_positives=true
        false_negatives=false
        echo "### False Positive Info" >> $OUTPUT_FILE
        continue
    fi

    if [[ "$line" =~ ^False[[:space:]]*Negatives:[[:space:]]*$ ]]; then
        false_negatives=true
        false_positives=false
        echo "### False Negative Info" >> $OUTPUT_FILE
        continue
    fi


    # match new false negative or positive sections

    if [ "$false_positives" = true ]; then
        # match start of new bug

        if [[ "$line" =~ ^Bug\ Type:\ ([A-Z]*)$ ]]; then
            current_false_positive=""
            continue
        elif [[ "$line" =~ ^SRC\ Info:\ \(\(([^,]*),\ ([^,]*),\ ([0-9]*),\ ([^,]*)\),\ ([^,]*)\)$ ]]; then
            path="${BASH_REMATCH[2]}"
            line_num="${BASH_REMATCH[3]}"
            line_data="$(sed -n "${line_num}p" "${path#./test/regression_testing/}")" # cut off start of file path for correct traversal
            line_data="$(echo "$line_data" | xargs)"
            short_name="${path#./test/regression_testing/test_files/}"
            current_false_positive+="Source at \`$path:$line_num\`\n"
            current_false_positive+="\nSource Code: \n \`\`\`\n$line_data\n\`\`\`\n"
            continue
        elif [[ "$line" =~ ^$ ]] && [ -n "$current_false_positive" ]; then
            current_false_positive+="\`\`\`\n"
            echo -e "$current_false_positive" >> $OUTPUT_FILE # -e = proper newlines
            current_false_positive=""
            continue
        elif [[ "$line" =~ ^Sink\ Function:\ (.*)$ ]]; then
            current_false_positive+="Sink Function: \n\`\`\`\n"
            current_false_positive+="${BASH_REMATCH[1]}\n"
            continue
        else
            current_false_positive+="$line\n"
            continue
        fi
    fi
    if [ "$false_negatives" = true ]; then
        if [[ "$line" =~ ^Bug\ SRC\ Info:\ ([A-Za-z0-9.]*)-([0-9]*)$ ]]; then
            file="${BASH_REMATCH[1]}"
            line_num="${BASH_REMATCH[2]}"
            path="test_files/$current_language/$current_bug_type/bad/$file"
            line_data="$(sed -n "${line_num}p" "$path" | xargs)" # get line without whitespace at start and end
            # start of bug
            current_false_negative="Source SHOULD have been at \`$path:$line_num\`\n"
            current_false_negative+="Source line code: \n\`\`\`\n$line_data\n\`\`\`\n"
            continue
        elif [[ "$line" =~ ^Bug\ Sink\ File:\ (.*)$ ]]; then
            current_fn_file="test_files/$current_language/$current_bug_type/bad/${BASH_REMATCH[1]}"
            continue
        elif [[ "$line" =~ ^Bug\ Sink\ Line\ Number:\ ([0-9]*)$ ]]; then
            current_fn_line_num="${BASH_REMATCH[1]}"
            current_false_negative+="Sink SHOULD have been at \`$current_fn_file:$current_fn_line_num\`\n"
            continue
        elif [[ "$line" =~ ^Bug\ Sink\ Code:\ (.*)$ ]]; then
            current_false_negative+="Sink line code: \n\`\`\`\n${BASH_REMATCH[1]}\n\`\`\`\n"
            echo -e "$current_false_negative" >> "$OUTPUT_FILE" # end of bug
            current_false_negative="" # reset
            continue
        fi
    fi
    
done < "$INPUT_FILE"

# compile the summary
current_date="$(date)"
final_string="# Regression Test Summary $current_date\n"
final_string+="## Summary\n"
summary_recall="$(echo "scale=5; $num_true_positives / $num_correct_total" | bc)"
num_false_positives=$(($num_false_positives + $num_true_positives))
summary_precision="$(echo "scale=5; $num_true_positives / $num_false_positives" | bc)"
summary_f1="$(echo "scale=5; 2 * $summary_precision * $summary_recall / ($summary_recall + $summary_precision)" | bc)"
final_string+="| Statistic | Value |\n"
final_string+="|-----------|-------|\n"
final_string+="| Precision | $summary_precision |\n"
final_string+="| Recall | $summary_recall |\n"
final_string+="| F1 Score | $summary_f1 |\n\n"

final_string+="$(cat "$OUTPUT_FILE")"
echo -e "$final_string" > "$OUTPUT_FILE"

log_file="regression.log"
echo -e "$USER @ $current_date" >> "$log_file"
echo -e "  precision: $summary_precision; recall: $summary_recall; F1 score: $summary_f1;\n" >> "$log_file"



echo "✨ Formatted report saved to: $OUTPUT_FILE"
echo "📊 Processing complete!"