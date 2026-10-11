import unittest
import random

from solver import deduce, neighbors


class SolverTests(unittest.TestCase):
    def test_deductions_are_certain_under_all_compatible_small_board_assignments(self):
        from probability import mine_probabilities
        rng=random.Random(752)
        for _ in range(40):
            positions=set(range(12))
            mines=set(rng.sample(sorted(positions),rng.randint(1,5)))
            opened=set(rng.sample(sorted(positions-mines),rng.randint(1,min(5,12-len(mines)))))
            board=[['?']*4 for _ in range(3)]
            for pos in opened:
                r,c=divmod(pos,4)
                board[r][c]=sum(nr*4+nc in mines for nr,nc in neighbors(r,c,3,4))
            risks=mine_probabilities(board,len(mines))
            result=deduce(board,len(mines))
            for (r,c),risk in risks.items():
                if result[r][c]=='f':
                    self.assertEqual(risk,1)
                elif result[r][c]=='o':
                    self.assertEqual(risk,0)

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

    def test_subset_remainder_is_safe(self):
        board = [[1, 1, "b"], ["?", "?", "?"]]
        self.assertEqual(deduce(board), [[1, 1, "b"], ["?", "?", "o"]])

    def test_subset_remainder_contains_mines(self):
        board = [[1, "?", "b"], [3, "?", "b"], ["?", "?", "b"]]
        self.assertEqual(deduce(board),
                         [[1, "?", "b"], [3, "?", "b"], ["f", "f", "b"]])

    def test_subset_discounts_known_mines(self):
        board = [[1, 2, "m"], ["?", "?", "?"]]
        self.assertEqual(deduce(board), [[1, 2, "m"], ["?", "?", "o"]])

    def test_subset_result_enables_basic_rule(self):
        board = [[1, 1, "b", 1], ["?", "?", "?", "?"]]
        self.assertEqual(deduce(board), [[1, 1, "b", 1], ["?", "?", "o", "f"]])

    def test_partial_overlap_does_not_force_cells(self):
        board = [[1, "b", 1], ["?", "?", "?"]]
        self.assertEqual(deduce(board), board)

    def test_equal_groups_with_different_mine_counts_fail(self):
        with self.assertRaises(ValueError):
            deduce([[1, 2], ["?", "?"]])

    def test_impossible_subset_difference_fails(self):
        with self.assertRaises(ValueError):
            deduce([[2, 1, "b"], ["?", "?", "?"]])


if __name__ == "__main__":
    unittest.main()
