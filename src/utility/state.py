from utility.function import *
from utility.localvalue import *
import copy


class Operation:
    def __init__(self, name, function_name, function_id, file_name):
        self.function_name = function_name
        self.function_id = function_id
        self.file_name = file_name

        labels = name[2:-2].split(", ")
        labels.append(function_name)
        labels.append(file_name)
        self.name = f"<<{', '.join(labels)}>>"
        self.status = None
        self.type = None
        self.line = None
        self.index = None
        self.callee_name = None
        self.is_propagate = None
        self.error_message = self.parse(name)
    
    def parse(self, name: str) -> str:
        try:
            labels = name[2:-2].split(", ")
            self.status = labels[0]
            self.line = labels[1]
            self.type = labels[2]
            if self.type == "Invocation":
                # callee function
                self.callee_name = labels[3]
                self.index = int(labels[4])

            if self.type == "Return":
                is_propagate = labels[3]
                if is_propagate == "No":
                    self.is_propagate = False
                else:
                    self.is_propagate = True

            if self.type == "Pointer Parameters":
                self.index = int(labels[3])
        except Exception as e:
            return str(e)
        return ""

    def __str__(self) -> str:
        return self.name

# class Path:
#     def __init__(self, lines:str, trace: list[Operation]):
#         trace: list[Operation] = trace
#         lines = lines

#     def set_status(self, status: str):
#         map = {
#             "allocated": Status.Allocated,
#             "unallocated": Status.UnAllocated,
#             "freed": Status.Freed,
#             "unknown": Status.Unknown
#         }
#         status = status.lower()
#         if status not in map:
#             raise ValueError(f"Invalid status: {status}")
#         self.status = map[status]

#     def get_status(self) -> str:
#         return self.status.name


class Function_State:
    def __init__(self, source: LocalValue, function: Function):
        self.source = source
        self.function = function
        self.subpath: list[list[Operation]] = []
        self.depth = 0
    
    def get_src_line(self) -> int:
        return self.source.line_number - self.function.start_line_number + 1
    
    def get_subpath(self) -> list[list[Operation]]:
        return copy.deepcopy(self.subpath)
        