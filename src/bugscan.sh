#!/bin/bash
LANGUAGE=C
BUG_TYPE=BOF
PROJECT_NAME=curl
SCANNER=neumeric

python3 scan.py \
  --language $LANGUAGE \
  --inference-model claude-3.7 \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --is-fscot \
  --scanners $SCANNER \
  --src-spec-file ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/src_result.json \
  --sink-spec-file ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/sink_result.json \
  --analyze-prompt-file prompt/$BUG_TYPE/analysis_prompt.json \
  --validate-prompt-file prompt/$BUG_TYPE/validation_prompt.json