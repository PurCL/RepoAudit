#!/usr/bin/env bash
LANGUAGE=Go
BUG_TYPE=BOF
SCANNER=bugscan


PROJECTS=(
  atomic automaxprocs dig go-helix hackeroni mock ratelimit toy
  dosa goleak icu4go multierr sally zap
  cff flagoverride gopatch kafka-client nilaway tally
  config fx gwr mapdecode protoidl tools
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
  --boundary 3 \
  --max-workers 10 \
  --seed-spec-file ../result/extract/$BUG_TYPE/${LANGUAGE}_${PROJECT}/seed_result.json
done


