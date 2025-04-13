#!/bin/bash
# filepath: /Users/xiangqian/Documents/CodeBase/RepoAudit-Plus/src/run_repoaudit.sh

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 {bugscan|dfbscan}"
    exit 1
fi

SCAN_TYPE=$1

# For demo/test run
case "$SCAN_TYPE" in
    bugscan)
        python3 repoaudit.py \
          --language Java \
          --model-name claude-3.7 \
          --project-path ../benchmark/Java/toy/NPD \
          --bug-type NPD \
          --temperature 0.0 \
          --scan-type bugscan \
          --call-depth 6 \
          --max-workers 1
        ;;
    dfbscan)
        python3 repoaudit.py \
          --language Java \
          --model-name claude-3.7 \
          --project-path ../benchmark/Java/toy/NPD \
          --bug-type NPD \
          --is-reachable \
          --temperature 0.0 \
          --scan-type dfbscan \
          --call-depth 6 \
          --max-workers 1
        ;;
    *)
        echo "Unknown scan type: $SCAN_TYPE"
        echo "Usage: $0 {bugscan|dfbscan}"
        exit 1
        ;;
esac