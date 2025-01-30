# sound_1c4f29e

Project Repo: https://github.com/torvalds/linux/tree/1c4f29ec878bbf1cc0a1eb54ae7da5ff98e19641/sound

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/torvalds/linux/tree/1c4f29ec878bbf1cc0a1eb54ae7da5ff98e19641/sound/soc/qcom/qdsp6/q6apm.c#L66

Bug traces:

* <	graph->graph = audioreach_alloc_graph_pkt(apm, &info->sg_list, graph_id);, q6apm_get_audioreach_graph>

Explanation:

* graph->graph is allocated successfully but not freed when idr_alloc fails at line 38, causing a memory leak.


