#!/bin/bash
# filepath: /Users/xiangqian/Documents/CodeBase/RepoAudit-Plus/src/run_repoaudit.sh

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 {bugscan|dfbscan}"
    exit 1
fi

SCAN_TYPE=$1
LANGUAGE=Java
MODEL=claude-3.7
BUG_TYPE=NPD
PROJECT=toy/NPD

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
          --call-depth 3 \
          --max-neural-workers 10
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
          --call-depth 3 \
          --max-neural-workers 1
        ;;
    *)
        echo "Unknown scan type: $SCAN_TYPE"
        echo "Usage: $0 {bugscan|dfbscan}"
        exit 1
        ;;
esac