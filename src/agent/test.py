from typing import List, Set

def collect_potential_buggy_paths(reachable_ints_per_path, start_int: int) -> List[List[int]]:
    # 如果不存在起始 int 的路径数据，则直接返回只有起始 int 本身的路径
    if start_int not in reachable_ints_per_path:
        return [[start_int]]
    
    # 获取从起始 int 出发的各步可达值集合列表
    steps: List[Set[int]] = reachable_ints_per_path[start_int]
    paths: List[List[int]] = []
    
    def backtrack(i: int, cur_path: List[int]) -> None:
        # 当遍历完所有的步后保存当前路径
        if i == len(steps):
            paths.append(cur_path.copy())
            return
        
        # 对于当前步的每个可能的值，递归构建路径
        for next_val in steps[i]:
            cur_path.append(next_val)
            backtrack(i + 1, cur_path)
            cur_path.pop()
    
    # 初始时将起始 int 放入路径中
    backtrack(0, [start_int])
    return paths


reachable_ints_per_path = {
    1: [{2, 3}, {4, 5}], 
    2: [{3, 4}, {5, 6}]
}


print(collect_potential_buggy_paths(reachable_ints_per_path, 1))