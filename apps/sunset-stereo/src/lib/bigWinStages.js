export const BIG_WIN_MULT = 20;

export const BIG_WIN_STAGES = [
  { id: "win1", from: 0, to: 40, left: "BIG", right: "WIN", file: "win1.mp3" },
  { id: "win2", from: 40, to: 60, left: "SUPER", right: "WIN", file: "win2.mp3" },
  { id: "win3", from: 60, to: 80, left: "MEGA", right: "WIN", file: "win3.mp3" },
  { id: "win4", from: 80, to: 200, left: "EPIC", right: "WIN", file: "win4.mp3" },
  { id: "win5", from: 200, to: Number.POSITIVE_INFINITY, left: "SUNSET", right: "WIN", file: "win5.mp3" },
];

export function isBigWin(micro, betMicro) {
  return micro > betMicro * BIG_WIN_MULT;
}

export function stagesForWin(micro, betMicro) {
  const multiple = micro / betMicro;
  return BIG_WIN_STAGES.filter((stage) => multiple > stage.from).map((stage) => {
    const toMultiple = Number.isFinite(stage.to) ? Math.min(stage.to, multiple) : multiple;
    return {
      ...stage,
      fromMicro: Math.round(stage.from * betMicro),
      toMicro: Math.round(toMultiple * betMicro),
    };
  });
}
