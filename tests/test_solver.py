import unittest

from solver import deduce, neighbors


class SolverTests(unittest.TestCase):
    def test_missing_mines_are_deduced(self):
        self.assertEqual(deduce([[3, "m"], ["?", "?"]]), [[3, "m"], ["f", "f"]])

    def test_remaining_cells_are_safe(self):
        self.assertEqual(deduce([[2, "m", "?"], ["f", "?", "b"]]),
                         [[2, "m", "?"], ["f", "o", "b"]])

    def test_zero_and_holes(self):
        self.assertEqual(deduce([[0, "?"], ["b", "?"]]), [[0, "o"], ["b", "o"]])

    def test_corner_includes_diagonal(self):
        self.assertEqual(set(neighbors(0, 0, 3, 3)), {(0, 1), (1, 0), (1, 1)})

    def test_deductions_propagate(self):
        board = [[1, "?", 1, "?"], ["b", "b", "b", "b"]]
        self.assertEqual(deduce(board)[0], [1, "f", 1, "o"])

    def test_safe_cells_are_not_possible_mines(self):
        self.assertEqual(deduce([[1, "o"], ["?", "b"]]), [[1, "o"], ["f", "b"]])

    def test_ambiguous_cells_remain_unknown(self):
        board = [[1, "?"], ["?", "b"]]
        self.assertEqual(deduce(board), board)

    def test_input_is_preserved(self):
        board = [[0, "?"]]
        deduce(board)
        self.assertEqual(board, [[0, "?"]])

    def test_conflicting_deductions_fail(self):
        with self.assertRaises(ValueError):
            deduce([[0, "?", 1]])

    def test_impossible_clue_fails(self):
        with self.assertRaises(ValueError):
            deduce([[2, "?"]])

    def test_invalid_boards_fail(self):
        for board in ([], [[]], [[0], [0, 0]], [[9]], [["x"]], [[True]]):
            with self.subTest(board=board), self.assertRaises(ValueError):
                deduce(board)


if __name__ == "__main__":
    unittest.main()
