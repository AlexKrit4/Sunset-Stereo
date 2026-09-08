import type { RawSymbol, Position } from "../game/typesBookEvent";

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
