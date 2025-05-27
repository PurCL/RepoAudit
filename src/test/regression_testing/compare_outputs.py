import json

expected_file = "/home/ddeluca/RepoAudit-Plus/src/test/regression_testing/test_files/python/NPD/expected.json"
output_file = "/home/ddeluca/RepoAudit-Plus/result/dfbscan/o3-mini-2025-01-31/NPD/Python/bad/2025-05-27-20-52-51-0/detect_info.json"
differences_file = ""
bug_type = "NPD"

# turn the expected_file and output_file into jsons

expected_data = {}
with open(expected_file, "r") as file:
    expected_data = json.load(file)

output_data = {}
with open(output_file, "r") as file:
    output_data = json.load(file)

false_positives = []
false_negatives = []    

# iterate through the output

for key in output_data.keys():
    # first, put together the name and line into a title
    data = output_data[key]

    if data["bug_type"] != bug_type:
        # wrong bug type, false positive
        false_positives.append(data)
        continue
    
    val = data["buggy_value"]
    val_list = val.split(",")
    bug_filename = val_list[1].split("/")[-1] # last part of the path
    bug_line_num = int(val_list[2]) # line number
    bug_name = bug_filename + "-" + str(bug_line_num)

    if bug_name not in expected_data.keys(): 
        # if we didn't expect a src at this line in this file, then it must be a false positive
        false_positives.append(data)
        continue

    found = False
    for sink_line in expected_data[bug_name]:
        if sink_line in data["relevant_functions"][2][-1]: # last line in relevant functions
            found = True
            expected_data[bug_name].remove(sink_line) # so we don't need to find it again
            break
        
    if not found:
        false_positives.append(data)

    
# find false negatives
for bug in expected_data.keys():
    if len(expected_data[bug]) != 0:
        false_negatives.append({bug: expected_data[bug]})


if len(false_negatives) == 0 and len(false_positives) == 0:
    print("Every bug was properly found here!")
else:
    print("False Positives:")
    for bug in false_positives:
        print("Bug Type: " + bug["bug_type"])
        print("SRC Info: " + bug["buggy_value"])
        print("Sink Function: " +  bug["relevant_functions"][2][-1])

    print("False Negatives:")
    for bug in false_negatives:
        print("Bug SRC Info: " + str(list(bug.keys())[0]))
        print("Bug Sink Info: " + str(bug[str(list(bug.keys())[0])]))
        print()
        print()


    

    


