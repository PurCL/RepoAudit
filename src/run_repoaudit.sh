#!/bin/bash
# filepath: /Users/xiangqian/Documents/CodeBase/RepoAudit-Plus/src/run_repoaudit.sh

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 {bugscan|dfbscan}"
    exit 1
fi

SCAN_TYPE=$1
LANGUAGE=Cpp
MODEL=claude-3.5
BUG_TYPE=BOF
PROJECT=zstd

# For demo/test run
case "$SCAN_TYPE" in
    bugscan)
        python3 repoaudit.py \
          --language $LANGUAGE \
          --model-name $MODEL \
          --project-path ../benchmark/${LANGUAGE}/${PROJECT} \
          --bug-type $BUG_TYPE \
          --temperature 0.0 \
          --scan-type bugscan \
          --call-depth 4 \
          --max-workers 1
        ;;
    dfbscan)
        python3 repoaudit.py \
          --language $LANGUAGE \
          --model-name $MODEL \
          --project-path ../benchmark/${LANGUAGE}/${PROJECT} \
          --bug-type $BUG_TYPE \
          --is-reachable \
          --temperature 0.0 \
          --scan-type dfbscan \
          --call-depth 4 \
          --max-workers 1
        ;;
    *)
        echo "Unknown scan type: $SCAN_TYPE"
        echo "Usage: $0 {bugscan|dfbscan}"
        exit 1
        ;;
esac