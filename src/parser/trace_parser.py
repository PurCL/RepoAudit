import json

def trace_parser(input_file):
    with open(input_file, "r") as f:
        src_spec = json.load(f)
    bug_traces = set()
    for source, traces in src_spec.items():
        print(source)
        is_global = False
        temp = []
        for trace in traces:
            if is_global:
                break
            is_bug = analyze_trace(trace, is_global)
            if is_bug:
                temp.append(str(trace))
        if not is_global:
            for trace in temp:
                bug_traces.add(trace)
    print("Bug Traces Num: ", len(bug_traces))
    for trace in bug_traces:
        print(trace)


def analyze_trace(trace: list, is_global) -> bool:
    depth = 0
    if len(trace) == 0:
        return False
    for operation in trace:
        label = operation[2:-2].split(", ")
        status = label[0]
        type = label[2]

        if type == "Global Variables":
            is_global = True
            return False
        if type == "Invocation" or type == "Pointer Parameters":
            return False
        if type == "Return" and label[3] == "Yes":
            return False
        if type == "Free":
            return False
        if status == "UnAllocated" or status == "Freed":
            return False
    return True




if __name__ == "__main__":
    trace_parser("/data4/guo846/LLMSCAN/log/ML/C++_libsass/trace.json")