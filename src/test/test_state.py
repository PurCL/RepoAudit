import unittest
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from utility.state import State
from utility.localvalue import *
from utility.function import *

class TestState(unittest.TestCase):
    def setUp(self):
        # Create LocalValue and Function instances
        self.local_value = LocalValue(name="test_var", line_number=1, v_type=ValueType.SRC, file="test_file.py")
        self.function = Function(function_id=0, function_name="test_function", function_code="", start_line_number=1, end_line_number=10, function_node=None, file_name="test_file.py")
        
        # Create State instances
        self.state1 = State(var=self.local_value, function=self.function)
        self.state2 = State(var=self.local_value, function=self.function)
        self.state3 = State(var=self.local_value, function=self.function)
        self.state4 = State(var=self.local_value, function=self.function)
        
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

if __name__ == '__main__':
    unittest.main()