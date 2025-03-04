#!/bin/bash
LANGUAGE=C
BUG_TYPE=BOF
# PROJECT_NAME=curl
# PROJECT_NAME=php-src
# PROJECT_NAME=zstd
PROJECT_NAME=cpv-3-repair

# create the directory for the result
if [ ! -d ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi

python -m extractor.${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --src-path ../result/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/src_result.json