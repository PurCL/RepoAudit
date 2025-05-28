import json
import os
import argparse

parser = argparse.ArgumentParser(description='Process bug analysis arguments')
parser.add_argument('--expected', required=True, help='Expected output file or value')
parser.add_argument('--output', required=True, help='Actual output file or value')
parser.add_argument('--differences', required=True, help='File to store differences')
parser.add_argument('--bug-type', required=True, help='Type of bug being analyzed')

args = parser.parse_args()

# Now you can use the variables
expected_file = args.expected
output_file = args.output
differences = args.differences
bug_type = args.bug_type

# turn the expected_file and output_file into jsons

expected_data = {}
with open(expected_file, "r") as file:
    expected_data = json.load(file)

output_data = {}
if os.path.exists(output_file):
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


lines=[]

if len(false_negatives) == 0 and len(false_positives) == 0:
    lines.append("Every bug was properly found here!")
else:
    if len(false_positives) > 0:
        lines.append("False Positives:")
    for bug in false_positives:
        lines.append("Bug Type: " + bug["bug_type"])
        lines.append("SRC Info: " + bug["buggy_value"])
        lines.append("Sink Function: " +  bug["relevant_functions"][2][-1])
        lines.append("\n")

    if len(false_negatives) > 0:
        lines.append("False Negatives:\n")
    for bug in false_negatives:
        lines.append("Bug SRC Info: " + str(list(bug.keys())[0]))
        lines.append("Bug Sink Info: " + str(bug[str(list(bug.keys())[0])]))
        lines.append("\n")

with open(differences, "a+") as file:
    file.writelines([s + '\n' for s in lines]) #CHECK


    

    


