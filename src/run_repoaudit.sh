python3 repoaudit.py \
  --language Java \
  --model-name o3-mini \
  --project-path ../benchmark/Java/toy \
  --bug-type NPD \
  --is-reachable \
  --temperature 0.0 \
  --scan-type bugscan \
  --call-depth 6 \
  --max-workers 3 \