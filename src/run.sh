#!/bin/bash
LANGUAGE=C
BUG_TYPE=BOF
# PROJECT_NAME=curl
# PROJECT_NAME=php-src
# PROJECT_NAME=zstd
PROJECT_NAME=zstd
SCANNER=bugscan


# create the directory for the result
if [ ! -d ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi

python -m tstool.extractor.C_${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --src-path ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/src_result.json


python3 repoaudit.py \
  --language $LANGUAGE \
  --inference-model o3-mini \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --scanners $SCANNER \
  --boundary 3 \
  --src-spec-file ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/src_result.json