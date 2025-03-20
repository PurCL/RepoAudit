#!/bin/bash
LANGUAGE=Cpp
BUG_TYPE=NPD
SCANNER=slicescan
PROJECT_NAME=sofa-pbrpc

python3 repoaudit.py \
  --language $LANGUAGE \
  --inference-model claude-3.7 \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --scanners $SCANNER \
  --call-depth 1 \
  --max-workers 1 \
  --seed-spec-file ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json