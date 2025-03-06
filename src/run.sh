#!/bin/bash
LANGUAGE=C
BUG_TYPE=BOF
PROJECT_NAME=zstd
SCANNER=bugscan


# create the directory for the result
if [ ! -d ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi


python -m tstool.extractor.${LANGUAGE}.${LANGUAGE}_${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --seed-path ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json


python3 repoaudit.py \
  --language $LANGUAGE \
  --inference-model o3-mini \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --scanners $SCANNER \
  --boundary 3 \
  --seed-spec-file ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json
