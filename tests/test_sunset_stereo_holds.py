import random
import unittest

from ways_paint import growing_hold_stages, paying_hold_cells, paint_hit_fillers, visible_ways_win


class BonusHoldsTest(unittest.TestCase):
    def test_two_wins_are_held_only_after_each_way_pays(self):
        final = {
            (0, 0): "H1", (1, 3): "H1", (2, 3): "H1",
            (0, 3): "H2", (1, 0): "H2", (1, 1): "H2",
            (2, 0): "H2", (2, 1): "H2",
        }
        for count in (2, 3):
            stages = growing_hold_stages(final, count)
            self.assertEqual(len(stages), count + 1)
            self.assertEqual(stages[-1], final)
            self.assertNotIn((0, 3), stages[0])
            for stage in stages[:-1]:
                self.assertEqual(set(stage), paying_hold_cells(stage))
                self.assertGreater(visible_ways_win(paint_hit_fillers(stage, random.Random(1))), 0)

    def test_sticky_wild_can_stay_without_a_pay(self):
        final = {
            (0, 0): "L2", (1, 1): "W", (2, 0): "L2", (3, 2): "L2",
            (0, 3): "H1", (1, 0): "H1", (2, 1): "H1",
        }
        stages = growing_hold_stages(final, 3)
        for stage in stages[:-1]:
            self.assertEqual(stage[(1, 1)], "W")
            self.assertEqual(
                set(stage) - paying_hold_cells(stage),
                {key for key, name in stage.items() if name == "W"} - paying_hold_cells(stage),
            )


if __name__ == "__main__":
    unittest.main()
