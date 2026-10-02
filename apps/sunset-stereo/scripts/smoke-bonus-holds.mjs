import assert from "node:assert/strict";
import { payingBonusCells, validBonusHolds } from "../src/rgs/bookView.ts";

const cases = [
  {
    mode: "3 scatters",
    columns: [
      ["H1", "L1", "L2", "H2"],
      ["H2", "H2", "L4", "H1"],
      ["L4", "L2", "H5", "H1"],
      ["L1", "L5", "L1", "H3"],
      ["H5", "L3", "H3", "L3"],
      ["L1", "H3", "L5", "L5"],
    ],
    proposed: [[0, 1], [0, 4], [1, 1], [1, 2], [1, 4], [2, 4]],
    expected: [[0, 1], [1, 4], [2, 4]],
  },
  {
    mode: "4 scatters",
    columns: [
      ["L2", "H2", "L5", "L2"],
      ["H1", "W", "L2", "L2"],
      ["H2", "H5", "H5", "L3"],
      ["L3", "L5", "L5", "H4"],
      ["H4", "L3", "L4", "L1"],
      ["L3", "L3", "H3", "L5"],
    ],
    proposed: [[0, 2], [1, 1], [1, 2], [2, 1]],
    expected: [[0, 2], [1, 2], [2, 1]],
  },
  {
    mode: "no paying way",
    columns: [
      ["H2", "L1", "L2", "L3"],
      ["H2", "H1", "L4", "L4"],
      ["L1", "H5", "L5", "L4"],
      ["L1", "L2", "L4", "L5"],
      ["L4", "L3", "L1", "L2"],
      ["L1", "H1", "H4", "L1"],
    ],
    proposed: [[0, 1], [1, 1]],
    expected: [],
  },
];

for (const { mode, columns, proposed, expected } of cases) {
  const board = columns.map((column) =>
    ["L5", ...column, "L5"].map((name) => ({ name })),
  );
  const positions = proposed.map(([reel, row]) => ({ reel, row }));
  assert.deepEqual(
    validBonusHolds(board, positions).map(({ reel, row }) => [reel, row]),
    expected,
    mode,
  );
  if (!expected.length) assert.equal(payingBonusCells(board).size, 0, mode);
}

console.log("bonus holds match current paying ways");
