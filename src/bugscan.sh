#!/bin/bash
LANGUAGE=C
BUG_TYPE=BOF
SCANNER=neumeric

# PROJECT_NAME=curl
# PROJECT_NAME=php-src
# PROJECT_NAME=zstd
PROJECT_NAME=zstd

python3 scan.py \
  --language $LANGUAGE \
  --inference-model o3-mini \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --is-fscot \
  --scanners $SCANNER \
  --boundary 3 \
  --src-spec-file ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/src_result.json