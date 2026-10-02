import type { RawSymbol, Position } from "../game/typesBookEvent";
import { PAYABLE } from "../math/config.js";

const FROM_MATH: Record<string, string> = {
  H1: "high1",
  H2: "high2",
  H3: "high3",
  H4: "high4",
  H5: "high5",
  L1: "low1",
  L2: "low2",
  L3: "low3",
  L4: "low4",
  L5: "low5",
  W: "wild",
  S: "scatter",
};

export function cellName(cell: RawSymbol | string) {
  const raw = typeof cell === "string" ? cell : cell.name;
  return FROM_MATH[raw] ?? raw;
}

export function visibleNames(board: RawSymbol[][]): string[][] {
  return board.map((col) => {
    const names = col.map(cellName);
    if (names.length >= 6) return names.slice(1, 5);
    return names.slice(0, 4);
  });
}

export function unpadPosition(pos: Position): Position {
  const row = pos.row > 0 ? pos.row - 1 : pos.row;
  return { reel: pos.reel, row: Math.max(0, Math.min(3, row)) };
}

export function winningWays(wins: Array<{ positions: Position[] }>) {
  return wins.reduce((total, win) => {
    const perReel = new Map<number, number>();
    for (const pos of win.positions) {
      perReel.set(pos.reel, (perReel.get(pos.reel) ?? 0) + 1);
    }
    let ways = 1;
    for (const count of perReel.values()) ways *= count;
    return total + ways;
  }, 0);
}

export function payingBonusCells(board: RawSymbol[][]): Set<string> {
  const names = visibleNames(board);
  const cells = new Set<string>();
  for (const symbol of PAYABLE) {
    const matching: string[][] = [];
    for (let reel = 0; reel < names.length; reel += 1) {
      const positions = names[reel].flatMap((name, row) =>
        name === symbol || name === "wild" ? [`${reel}:${row}`] : [],
      );
      if (!positions.length) break;
      matching.push(positions);
    }
    if (matching.length >= 3) {
      for (const column of matching) {
        for (const position of column) cells.add(position);
      }
    }
  }
  return cells;
}

export function validBonusHolds(board: RawSymbol[][], positions: Position[]): Position[] {
  const names = visibleNames(board);
  const paying = payingBonusCells(board);
  return positions.filter(({ reel, row }) => {
    const cell = unpadPosition({ reel, row });
    return names[cell.reel]?.[cell.row] === "wild" || paying.has(`${cell.reel}:${cell.row}`);
  });
}
