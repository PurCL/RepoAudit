#!/bin/bash

LANGUAGE=Cpp
MODEL=claude-3.7

python3 repoaudit.py \
  --language $LANGUAGE \
  --model-name $MODEL \
  --project-path "$1" \
  --bug-type "$2" \
  --temperature 0.0 \
  --scan-type dfbscan \
  --call-depth 3 \
  --max-workers 30