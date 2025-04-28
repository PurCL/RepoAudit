import unittest
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from memory.semantic.bugscan_state import BugScanState
from memory.syntactic.value import *
from memory.syntactic.function import *


class TestState(unittest.TestCase):
    def setUp(self):
        # Create LocalValue and Function instances
        for i in range(1, 5):
            function = Function(
                function_id=i,
                function_name=f"test_function{i}",
                function_code="",
                start_line_number=1,
                end_line_number=10,
                function_node=None,
                file_path="test_file.py",
            )
            local_value = Value(
                name=f"test_var{i}",
                line_number=i,
                v_label=ValueLabel.SRC,
                file="test_file.py",
            )
            setattr(self, f"state{i}", BugScanState(local_value, function))

        # Set up callers and callees
        self.state2.callers.append(self.state1)
        self.state1.callees.append(self.state2)

        self.state2.callers.append(self.state4)
        self.state4.callees.append(self.state2)

        self.state3.callers.append(self.state2)
        self.state2.callees.append(self.state3)

        # Set up slices
        self.state1.slice = "slice1"
        self.state2.slice = "slice2"
        self.state3.slice = "slice3"
        self.state4.slice = "slice4"

    def test_find_root(self):
        # Test if state3 can find the root state1
        roots = self.state3.find_root()
        self.assertEqual(len(roots), 2)
        self.assertEqual(roots, [self.state1, self.state4])

        # Test if state1 is its own root
        roots = self.state1.find_root()
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0], self.state1)

    def test_get_slice_tree(self):
        # Test if root functions can get the entire slice tree
        roots = self.state3.find_root()
        for root in roots:
            slice_list = root.get_slice_tree()
            slices = set(slice_list)
            self.assertEqual(len(slices), 3)
            if root == self.state1:
                self.assertEqual(slices, {"slice1", "slice2", "slice3"})
            elif root == self.state4:
                self.assertEqual(slices, {"slice2", "slice3", "slice4"})

        # Test if state3 can get the entire slice tree
        slices = self.state3.get_slice_tree()
        self.assertEqual(len(slices), 1)
        self.assertEqual(slices, ["slice3"])

    def test_get_call_tree(self):
        expected_tree_state1 = (
            "test_function1\n" "    └── test_function2\n" "        └── test_function3\n"
        )
        self.assertEqual(self.state1.get_call_tree(), expected_tree_state1)

        expected_tree_state4 = (
            "test_function4\n" "    └── test_function2\n" "        └── test_function3\n"
        )
        self.assertEqual(self.state4.get_call_tree(), expected_tree_state4)


if __name__ == "__main__":
    unittest.main()
