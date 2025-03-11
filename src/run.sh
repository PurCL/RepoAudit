#!/usr/bin/env bash
LANGUAGE=Cpp
BUG_TYPE=MLK
SCANNER=bugscan


PROJECTS=(
  sofa-pbrpc
)

for PROJECT in "${PROJECTS[@]}"; do
  RESULT_DIR="../result/extract/${BUG_TYPE}/${LANGUAGE}_${PROJECT}"
  echo "Creating directory: $RESULT_DIR"
  mkdir -p "$RESULT_DIR"

  echo "Scanning project: $PROJECT"

  if [ ! -d ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT} ]; then
    mkdir -p ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT}
  fi

  python3 -m tstool.extractor.${LANGUAGE}.${LANGUAGE}_${BUG_TYPE}_extractor \
    --language $LANGUAGE \
    --project-path ../benchmark/$LANGUAGE/$PROJECT \
    --seed-path ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT}/seed_result.json

  python3 repoaudit.py \
  --language $LANGUAGE \
  --inference-model claude-3.7 \
  --project-path ../benchmark/$LANGUAGE/$PROJECT \
  --bug-type $BUG_TYPE \
  --global-temperature 0.0 \
  --scanners $SCANNER \
  --max-workers 10 \
  --boundary 3 \
  --seed-spec-file ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT}/seed_result.json
done


