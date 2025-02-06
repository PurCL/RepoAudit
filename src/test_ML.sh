#!/bin/bash
LANGUAGE=C
BUG_TYPE=ML
PROJECT_NAME=memcached
SCANNER=bugscan

# create the directory for the result
if [ ! -d ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi

python -m parser.${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --src-path ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/src_result.json \
  --sink-path ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/sink_result.json 


python3 scan.py \
  --language $LANGUAGE \
  --inference-model claude \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --is-fscot \
  --scanners $SCANNER \
  --src-spec-file ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/src_result.json \
  --sink-spec-file ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/sink_result.json \
  --analyze-prompt-file prompt/$BUG_TYPE/analysis_prompt_reach.json \
  --validate-prompt-file prompt/$BUG_TYPE/validation_prompt.json