#!/bin/bash
LANGUAGE=C
# BUG_TYPE=BOF
BUG_TYPE=MLK

# PROJECT_NAME=curl
# PROJECT_NAME=php-src
# PROJECT_NAME=zstd
# PROJECT_NAME=cpv-3
PROJECT_NAME=memcached

# create the directory for the result
if [ ! -d ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME} ]; then
  mkdir -p ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}
fi

python -m tstool.extractor.${LANGUAGE}_${BUG_TYPE}_extractor \
  --language $LANGUAGE \
  --project-path ../benchmark/$LANGUAGE/$PROJECT_NAME \
  --seed-path ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT_NAME}/seed_result.json