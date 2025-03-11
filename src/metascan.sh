#!/bin/bash
LANGUAGE=Cpp
BUG_TYPE=NPD
SCANNER=metascan
PROJECT_NAME=sofa-pbrpc

python3 repoaudit.py \
  --language $LANGUAGE \
  --inference-model claude-3.7 \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --scanners $SCANNER \
  --boundary 3 \
  --max-workers 3 \
  --seed-spec-file ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json