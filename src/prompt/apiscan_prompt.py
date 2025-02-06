prompt_dict = {
"BN_secure_new": """
Task: If a function BN_secure_new() is called, i.e., `p = BN_secure_new();`, then we have to invoke BN_free(p) after the last use of p. 
Otherwise, please report a resource leak bug.
Please check the function body. If it violate the above rule, please report it as a resource bug.
Here is the function:
{function_code}
Please think step by step and give the answer in the following format:
Answer: [Your explanation]
Yes/No.
Specifically, the second line should contain Yes if there is a bug. Otherwise, it should contain No.
""",

"kalloc": """
Task: If a function kalloc() is called, i.e., `p = kalloc();`, then we have to check whther the return value p is null or not after using p
Otherwise, please report a null pointer dereference bug.
Please check the function body. If it violate the above rule, please report it as a bug.
Here is the function:
{function_code}
Please think step by step and give the answer in the following format:
Answer: [Your explanation]
Yes/No.
Specifically, the second line should contain Yes if there is a bug. Otherwise, it should contain No.
""",

"mhi_alloc_controller": """
Task: If a function mhi_alloc_controller() is called, i.e., `p = mhi_alloc_controller();`, then we have to invoke mhi_free_controller(p) after the last use of p.
Otherwise, please report a resource leak bug.
Please check the function body. If it violate the above rule, please report it as a resource bug.
Here is the function:
{function_code}
Please think step by step and give the answer in the following format:
Answer: [Your explanation]
Yes/No.
Specifically, the second line should contain Yes if there is a bug. Otherwise, it should contain No.
"""
}