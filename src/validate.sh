#!/bin/bash

python3 validate.py \
  --report-path ../result-deepseek/NPD/C++_sofa-pbrpc/bug_report.json \
  --inference-model claude \
  --output-path ../result-deepseek/NPD/C++_sofa-pbrpc/validate.json \
  --report-dir ../result-deepseek/ML > ../log/validate.log