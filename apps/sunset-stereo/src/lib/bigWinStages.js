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

export function stagesForWin(micro, betMicro, fromMicro = 0) {
  const multiple = micro / betMicro;
  const fromMultiple = Math.max(0, fromMicro / betMicro);
  if (!(multiple > fromMultiple)) return [];
  return BIG_WIN_STAGES.filter((stage) => {
    const stageTo = Number.isFinite(stage.to) ? stage.to : Number.POSITIVE_INFINITY;
    return multiple > stage.from && fromMultiple < stageTo;
  })
    .map((stage) => {
      const stageTo = Number.isFinite(stage.to) ? stage.to : Number.POSITIVE_INFINITY;
      const from = Math.max(stage.from, fromMultiple);
      const to = Math.min(stageTo, multiple);
      return {
        ...stage,
        fromMicro: Math.round(from * betMicro),
        toMicro: Math.round(to * betMicro),
      };
    })
    .filter((stage) => stage.toMicro > stage.fromMicro);
}

/** Running total already paid, so a wincap count can start there instead of 0. */
export function wincapCountFrom(totalMicro, spinWinMicro, hudMicro) {
  const remainder = totalMicro - spinWinMicro;
  if (spinWinMicro > 0 && remainder > 0 && remainder < totalMicro) return remainder;
  if (hudMicro > 0 && hudMicro < totalMicro) return hudMicro;
  return 0;
}

const WINCAP_STOP = ["reveal", "updateFreeSpin", "freeSpinEnd", "finalWin"];

/** Math books emit winInfo → wincap and skip setWin. Demo books may still send setWin first. */
export function followingWincap(events, current) {
  let start = events.indexOf(current);
  if (start < 0) start = events.findIndex((event) => event.index === current.index);
  if (start < 0) return null;
  for (let index = start + 1; index < events.length; index += 1) {
    const event = events[index];
    if (event.type === "wincap") return event;
    if (WINCAP_STOP.includes(event.type)) return null;
  }
  return null;
}
