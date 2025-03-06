#!/bin/bash
# LANGUAGE=Go
LANGUAGE=C
# BUG_TYPE=BOF
BUG_TYPE=MLK
SCANNER=bugscan

# PROJECT_NAME=curl
# PROJECT_NAME=php-src
# PROJECT_NAME=zstd
# PROJECT_NAME=cpv-3
PROJECT_NAME=memcached

python3 repoaudit.py \
  --language $LANGUAGE \
  --inference-model claude-3.7 \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --scanners $SCANNER \
  --boundary 3 \
  --seed-spec-file ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json