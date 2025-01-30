# mm_73b73ba

Project Repo: https://github.com/torvalds/linux/tree/73b73bac90d97400e29e585c678c4d0ebfd2680d/mm

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/torvalds/linux/tree/73b73bac90d97400e29e585c678c4d0ebfd2680d/mm/damon/reclaim.c#L434

Bug traces:

* <	ctx = damon_new_ctx();, damon_reclaim_init>

Explanation:

* The pointer ctx at line 3 is not freed before the function returns at line 8. Thus there is a memory leak bug.


