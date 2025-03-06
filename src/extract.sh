#!/bin/bash
LANGUAGE=Go
BUG_TYPE=BOF
PROJECT_NAME=toy

# LANGUAGE=C
# BUG_TYPE=BOF
# PROJECT_NAME=zstd

# create the directory for the result
if [ ! -d ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi

python -m tstool.extractor.${LANGUAGE}_${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --seed-path ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json