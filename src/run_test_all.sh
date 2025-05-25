# Test DFBScanAgent

## Test Cpp support of DFBScanAgent
bash run_repoaudit.sh dfbscan --language Cpp --project-path ../benchmark/Cpp/toy/NPD --bug-type NPD --is-reachable
bash run_repoaudit.sh dfbscan --language Cpp --project-path ../benchmark/Cpp/toy/MLK --bug-type MLK
bash run_repoaudit.sh dfbscan --language Cpp --project-path ../benchmark/Cpp/toy/NPD --bug-type UAF --is-reachable

## Test Java support of DFBScanAgent
bash run_repoaudit.sh dfbscan --language Java --project-path ../benchmark/Java/toy/NPD --bug-type NPD --is-reachable

## Test Python support of DFBScanAgent
bash run_repoaudit.sh dfbscan --language Python --project-path ../benchmark/Python/toy/NPD --bug-type NPD --is-reachable

## Test Go support of DFBScanAgent
bash run_repoaudit.sh dfbscan --language Go --project-path ../benchmark/Go/toy/NPD --bug-type NPD --is-reachable