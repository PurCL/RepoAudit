#!/bin/bash
LANGUAGE=Go
BUG_TYPE=NPD
PROJECT_NAME=sally

# create the directory for the result
if [ ! -d ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi

python3 -m tstool.extractor.${LANGUAGE}.${LANGUAGE}_${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --seed-path ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json


