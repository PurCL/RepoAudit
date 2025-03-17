#!/bin/bash
LANGUAGE=Cpp
BUG_TYPE=UAF
PROJECT_NAME=toy

# create the directory for the result
if [ ! -d ../result/src_extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/src_extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi

python3 -m tstool.src_extractor.${LANGUAGE}.${LANGUAGE}_${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --seed-path ../result/src_extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json