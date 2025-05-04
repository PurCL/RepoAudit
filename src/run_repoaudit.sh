#!/bin/bash

LANGUAGE=Cpp
MODEL=claude-3.7
BUG_TYPE=NPD
PROJECT_NAME=htop

python3 repoaudit.py \
  --language $LANGUAGE \
  --model-name $MODEL \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --temperature 0.0 \
  --scan-type dfbscan \
  --call-depth 3 \
  --max-workers 30