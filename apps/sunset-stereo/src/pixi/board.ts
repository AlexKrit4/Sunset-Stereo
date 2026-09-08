import { Application, BlurFilter, Container, Graphics, Text } from "pixi.js";
import { createSymbolView } from "./symbols";
import { wait } from "../game/eventEmitter";
import {
  getReelRows,
  getWaysTeaseSymbol,
  pickStripItems,
  reelMatchesWaysTease,
} from "../math/math.js";
import { MAX_ROWS, NUM_REELS, SCATTER_REELS } from "../math/config.js";

export const CELL = 90;
export const GAP = 5;
export const COLS = NUM_REELS;
export const ROWS = MAX_ROWS;

const START_STAGGER_MS = 58;
const STOP_STAGGER_MS = 300;
const LINEAR_MS = 900;
const DECEL_MS = 120;
const LINEAR_FRAC = 0.86;
const BASE_FILLERS = 16;
const SPIN_WINDUP_PX = 22;
const SPIN_WINDUP_MS = 52;
const SPIN_GRAVITY_MS = 70;
const BLUR_MAX = 12;
const NUDGE_WINDUP_MS = 100;
const NUDGE_PUSH_MS = 340;
const NUDGE_WINDUP_FRAC = 0.12;
const NUDGE_WINDUP_MAX_PX = 12;

function asView(name: string, multiplier = 1) {
  return createSymbolView({ name, multiplier: multiplier > 1 ? multiplier : undefined }, CELL);
}

function easeOutCubic(t: number) {
  const x = Math.min(Math.max(t, 0), 1);
  return 1 - (1 - x) ** 3;
}

function easeOutQuad(t: number) {
  const x = Math.min(Math.max(t, 0), 1);
  return 1 - (1 - x) * (1 - x);
}

type SpinJob = {
  col: number;
  strip: Container;
  blur: BlurFilter;
  startAt: number;
  restOffset: number;
  windupPx: number;
  windupMs: number;
  gravityMs: number;
  velocity: number;
  tDecel: number;
  decelMs: number;
  finals: string[];
  rows: number;
  done: boolean;
  settled: boolean;
};

export type SpinRound = {
  raw: string[][];
  resolved: string[][];
  mults: number[][];
  reelNudgeMult: number[];
  xWays: { positions: Array<{ reel: number; row: number; replacement: string; mult: number }>; replacement: string };
  nudge: Array<{ reel: number; landVisible: number; nudges: number; mult: number }>;
  extraStopMs: number[];
  waysGaps: number[];
  scatterGaps: number[];
  scatterHit: number[];
  totalWin: number;
  totalWays: number;
  wins: Array<{ sym: string; reelsMatched: number; ways: number; nudgeLineMult: number; win: number }>;
  highlights: Array<{ reel: number; row: number }>;
};

export class BoardController {
  app: Application;
  root = new Container();
  reels: Container[] = [];
  cells: Container[][] = [];
  private blurs: BlurFilter[] = [];
  private badges: Text[] = [];
  private visible: string[][] = [];
  private cellMults: number[][] = [];
  private spinning = false;
  private jobs: SpinJob[] = [];
  private boundTick = () => this.tickSpins();
  private onSettled: ((col: number) => void) | null = null;
  private teaseOverlay = new Graphics();
  private scatterOverlay = new Graphics();

  constructor(app: Application) {
    this.app = app;
  }

  mount() {
    const frame = new Graphics();
    const w = COLS * CELL + (COLS + 1) * GAP;
    const h = MAX_ROWS * CELL + 2 * GAP;
    frame.roundRect(0, 0, w, h, 8).fill(0x1a140f);
    frame.roundRect(0, 0, w, h, 8).stroke({ color: 0x8a6a40, width: 2 });
    this.root.addChild(frame);

    const window = new Container();
    window.x = GAP;
    window.y = GAP;

    for (let col = 0; col < COLS; col += 1) {
      const rows = getReelRows(col);
      const mask = new Graphics();
      mask.rect(0, 0, CELL, rows * CELL).fill(0xffffff);
      const host = new Container();
      host.x = col * CELL;
      host.y = (MAX_ROWS - rows) * CELL;
      host.addChild(mask);
      host.mask = mask;

      const strip = new Container();
      const blur = new BlurFilter({ strength: 0, quality: 3 });
      blur.strengthX = 0;
      blur.strengthY = 0;
      const seed = Array.from({ length: rows }, (_, row) => ["low4", "low2", "high3", "low1"][(col + row) % 4]);
      this.paintStrip(strip, seed);
      host.addChild(strip);
      window.addChild(host);
      this.reels.push(strip);
      this.blurs.push(blur);
      this.visible.push(seed);
      this.cellMults.push(Array.from({ length: rows }, () => 1));
      this.cells.push([]);

      const badge = new Text({
        text: "",
        style: { fontSize: 13, fill: 0xf0d8a0, fontFamily: "Georgia, serif", fontWeight: "700" },
      });
      badge.anchor.set(0.5, 1);
      badge.x = host.x + CELL / 2;
      badge.y = host.y - 6;
      badge.visible = false;
      window.addChild(badge);
      this.badges.push(badge);
    }

    this.teaseOverlay.eventMode = "none";
    this.scatterOverlay.eventMode = "none";
    window.addChild(this.teaseOverlay, this.scatterOverlay);
    this.root.addChild(window);
    this.app.stage.addChild(this.root);
  }

  private paintStrip(strip: Container, names: string[], mults?: number[]) {
    strip.removeChildren();
    names.forEach((name, index) => {
      const view = asView(name, mults?.[index] ?? 1);
      view.y = Math.round(index * CELL);
      strip.addChild(view);
    });
    strip.y = 0;
    strip.filters = [];
    strip.alpha = 1;
  }

  private landStatic(col: number, names: string[], mults?: number[]) {
    const strip = this.reels[col];
    const resolvedMults = mults ?? Array.from({ length: names.length }, () => 1);
    this.paintStrip(strip, names, resolvedMults);
    this.visible[col] = names.slice();
    this.cellMults[col] = resolvedMults.slice();
    this.cells[col] = strip.children as Container[];
    this.cells[col].forEach((cell) => {
      cell.alpha = 1;
    });
  }

  private planSpin(waysGaps: number[], scatterGaps: number[]) {
    const s0 = (MAX_ROWS + BASE_FILLERS) * CELL;
    const velocity = (LINEAR_FRAC * s0) / LINEAR_MS;
    const decelDistance = Math.max(0, s0 - velocity * LINEAR_MS);
    const plans: Array<{ delay: number; tDecel: number; fillers: number; velocity: number }> = [];
    let prevStop = 0;

    for (let col = 0; col < COLS; col += 1) {
      const delay = col * START_STAGGER_MS;
      const waysGap = waysGaps[col] || 0;
      const scatterGap = scatterGaps[col] || 0;
      const rows = getReelRows(col);
      const stopStagger = scatterGap > 0 ? 0 : STOP_STAGGER_MS;
      const minStop =
        col === 0 ? delay + LINEAR_MS + DECEL_MS : prevStop + stopStagger + waysGap + scatterGap;
      let tDecel = Math.max(80, minStop - delay - DECEL_MS);
      let needed = Math.ceil((velocity * tDecel + decelDistance) / CELL) - rows;
      needed = Math.max(10, needed);
      const startOffset = (rows + needed) * CELL;
      tDecel = Math.max(tDecel, (startOffset - decelDistance) / velocity);
      prevStop = delay + tDecel + DECEL_MS;
      plans.push({ delay, tDecel, fillers: needed, velocity });
    }
    return plans;
  }

  async playRound(round: SpinRound) {
    this.clearWins();
    this.badges.forEach((badge) => {
      badge.visible = false;
      badge.text = "";
    });
    await this.spinTo(round.raw, round.waysGaps, round.scatterGaps);
    await this.playXWays(round);
    await this.playNudge(round);
    if (round.totalWin > 0) {
      this.highlight(round.highlights);
      await wait(round.totalWin >= round.bet * 15 ? 1400 : 640);
    }
  }

  async spinTo(raw: string[][], waysGaps: number[] = [], scatterGaps: number[] = []) {
    if (this.spinning) return;
    this.spinning = true;
    this.teaseOverlay.clear();
    this.scatterOverlay.clear();
    this.teaseOverlay.alpha = 1;
    const plans = this.planSpin(waysGaps, scatterGaps);
    const now = performance.now();
    this.jobs = [];
    const rng = {
      random: Math.random.bind(Math),
      randomInt(min: number, max: number) {
        return min + Math.floor(Math.random() * (max - min + 1));
      },
    };

    for (let col = 0; col < COLS; col += 1) {
      const rows = getReelRows(col);
      const finals = raw[col];
      const plan = plans[col];
      const fillers = pickStripItems(rng, col, plan.fillers);
      const strip = this.reels[col];
      const blur = this.blurs[col];
      const restOffset = (rows + plan.fillers) * CELL;
      this.paintStrip(strip, [...finals, ...fillers, ...this.visible[col]]);
      strip.y = -restOffset;
      blur.strengthY = 0;
      strip.filters = [blur];
      this.jobs.push({
        col,
        strip,
        blur,
        startAt: now + plan.delay,
        restOffset,
        windupPx: SPIN_WINDUP_PX,
        windupMs: SPIN_WINDUP_MS,
        gravityMs: SPIN_GRAVITY_MS,
        velocity: plan.velocity,
        tDecel: plan.tDecel,
        decelMs: DECEL_MS,
        finals,
        rows,
        done: false,
        settled: false,
      });
    }

    this.onSettled = (col) => {
      const landed = raw.map((c) => c.slice());
      const sym = getWaysTeaseSymbol(landed, col);
      this.drawTease(landed, sym, col);
      this.drawScatterTease(landed, col);
    };

    await new Promise<void>((resolve) => {
      this.boundTick = () => {
        this.tickSpins();
        if (this.jobs.every((job) => job.done)) {
          this.app.ticker.remove(this.boundTick);
          this.teaseOverlay.clear();
          this.scatterOverlay.clear();
          this.teaseOverlay.alpha = 1;
          this.spinning = false;
          this.onSettled = null;
          resolve();
        }
      };
      this.app.ticker.add(this.boundTick);
    });
  }

  private drawTease(board: string[][], sym: string | null, upTo: number) {
    this.teaseOverlay.clear();
    if (!sym || upTo < 2) return;
    for (let r = 0; r <= upTo; r += 1) {
      if (!reelMatchesWaysTease(board, r, sym)) continue;
      const rows = getReelRows(r);
      const baseY = (MAX_ROWS - rows) * CELL;
      for (let row = 0; row < rows; row += 1) {
        const cell = board[r][row];
        if (cell !== "xNudge" && cell !== "wild" && cell !== sym) continue;
        this.teaseOverlay.roundRect(r * CELL + 3, baseY + row * CELL + 3, CELL - 6, CELL - 6, 8).stroke({
          color: 0xe8c878,
          width: 2,
          alpha: 0.9,
        });
      }
    }
  }

  private drawScatterTease(board: string[][], upTo: number) {
    this.scatterOverlay.clear();
    for (let r = 0; r <= upTo; r += 1) {
      if (!SCATTER_REELS.includes(r)) continue;
      const rows = getReelRows(r);
      const baseY = (MAX_ROWS - rows) * CELL;
      for (let row = 0; row < rows; row += 1) {
        if (board[r][row] !== "scatter") continue;
        this.scatterOverlay.roundRect(r * CELL + 2, baseY + row * CELL + 2, CELL - 4, CELL - 4, 8).stroke({
          color: 0xf0a050,
          width: 3,
          alpha: 0.95,
        });
      }
    }
  }

  private fallOffset(job: SpinJob, fallMs: number) {
    const apex = job.restOffset + job.windupPx;
    if (fallMs < job.gravityMs) {
      const accel = job.velocity / job.gravityMs;
      return Math.max(0, apex - 0.5 * accel * fallMs * fallMs);
    }
    const dist = 0.5 * job.velocity * job.gravityMs + job.velocity * (fallMs - job.gravityMs);
    return Math.max(0, apex - dist);
  }

  private fallSpeed(job: SpinJob, fallMs: number) {
    if (fallMs < job.gravityMs) return (job.velocity / job.gravityMs) * fallMs;
    return job.velocity;
  }

  private tickSpins() {
    const now = performance.now();
    this.teaseOverlay.alpha = 0.42 + 0.58 * (0.5 + 0.5 * Math.sin(now / 120));
    this.scatterOverlay.alpha = 0.55 + 0.45 * (0.5 + 0.5 * Math.sin(now / 160));
    for (const job of this.jobs) {
      if (job.done || now < job.startAt) continue;
      const elapsed = now - job.startAt;
      let offset: number;
      if (elapsed < job.windupMs) {
        const tossed = job.windupPx * easeOutQuad(elapsed / job.windupMs);
        offset = job.restOffset + tossed;
        job.blur.strengthY = 0;
      } else {
        const fallMs = elapsed - job.windupMs;
        if (fallMs < job.tDecel) {
          offset = this.fallOffset(job, fallMs);
          job.blur.strengthY = BLUR_MAX * Math.min(1, this.fallSpeed(job, fallMs) / job.velocity);
        } else {
          const u = Math.min((fallMs - job.tDecel) / job.decelMs, 1);
          const offAtDecel = this.fallOffset(job, job.tDecel);
          offset = offAtDecel * (1 - u);
          job.blur.strengthY = BLUR_MAX * (1 - u);
          if (u >= 1) {
            this.landReel(job);
            continue;
          }
        }
      }
      job.strip.y = -Math.round(offset);
    }
  }

  private landReel(job: SpinJob) {
    job.done = true;
    job.blur.strengthY = 0;
    job.strip.filters = [];
    this.landStatic(job.col, job.finals);
    if (!job.settled) {
      job.settled = true;
      this.onSettled?.(job.col);
    }
  }

  private async playXWays(round: SpinRound) {
    const { positions } = round.xWays;
    if (!positions.length) return;
    await wait(400);
    const fading = positions
      .map((pos) => this.cells[pos.reel]?.[pos.row])
      .filter((cell): cell is Container => Boolean(cell));
    await Promise.all(fading.map((cell) => this.tweenAlpha(cell, 1, 0, 520)));
    for (const pos of positions) {
      this.replaceCell(pos.reel, pos.row, pos.replacement, pos.mult);
    }
    const appearing = positions
      .map((pos) => this.cells[pos.reel]?.[pos.row])
      .filter((cell): cell is Container => Boolean(cell));
    appearing.forEach((cell) => {
      cell.alpha = 0;
    });
    await Promise.all(appearing.map((cell) => this.tweenAlpha(cell, 0, 1, 420)));
    await wait(80);
  }

  private replaceCell(col: number, row: number, name: string, mult = 1) {
    const strip = this.reels[col];
    const next = asView(name, mult);
    next.y = Math.round(row * CELL);
    if (row < strip.children.length) strip.removeChildAt(row);
    strip.addChildAt(next, Math.min(row, strip.children.length));
    this.cells[col][row] = next;
    this.visible[col][row] = name;
    this.cellMults[col][row] = mult;
  }

  private async playNudge(round: SpinRound) {
    for (const step of round.nudge) {
      const { reel, landVisible, nudges, mult } = step;
      await wait(350);
      let visible = landVisible;
      const names = this.visible[reel].slice();
      for (let n = 0; n < nudges; n += 1) {
        await this.nudgePush(reel, names, visible);
        visible = Math.min(getReelRows(reel), visible + 1);
        this.setBadge(reel, 1 + n + 1);
        await wait(160);
      }
      this.setBadge(reel, mult);
      await wait(180);
      const wilds = Array.from({ length: getReelRows(reel) }, () => "wild");
      this.landStatic(reel, wilds);
      this.setBadge(reel, mult);
      await wait(280);
    }
  }

  private setBadge(reel: number, mult: number) {
    const badge = this.badges[reel];
    if (!badge) return;
    if (mult > 1) {
      badge.text = `x${mult}`;
      badge.visible = true;
    } else {
      badge.text = "";
      badge.visible = false;
    }
  }

  private async nudgePush(reel: number, names: string[], expandRow: number) {
    const strip = this.reels[reel];
    const rows = getReelRows(reel);
    const next = Array.from({ length: rows }, (_, row) => (row === 0 ? "xNudge" : names[row - 1]));
    for (let row = 0; row <= Math.min(expandRow, rows - 1); row += 1) next[row] = "xNudge";

    this.paintStrip(strip, ["xNudge", ...names]);
    strip.y = -CELL;
    const windUp = Math.min(Math.round(CELL * NUDGE_WINDUP_FRAC), NUDGE_WINDUP_MAX_PX);
    await this.tweenY(strip, -CELL, -CELL - windUp, NUDGE_WINDUP_MS);
    await this.tweenY(strip, -CELL - windUp, 0, NUDGE_PUSH_MS);
    for (let i = 0; i < rows; i += 1) names[i] = next[i];
    this.landStatic(reel, names);
  }

  private tweenY(target: Container, from: number, to: number, ms: number) {
    return new Promise<void>((resolve) => {
      const start = performance.now();
      const tick = () => {
        const u = Math.min((performance.now() - start) / ms, 1);
        target.y = Math.round(from + (to - from) * easeOutCubic(u));
        if (u >= 1) {
          this.app.ticker.remove(tick);
          target.y = to;
          resolve();
        }
      };
      this.app.ticker.add(tick);
    });
  }

  private tweenAlpha(target: Container, from: number, to: number, ms: number) {
    return new Promise<void>((resolve) => {
      const start = performance.now();
      const tick = () => {
        const u = Math.min((performance.now() - start) / ms, 1);
        target.alpha = from + (to - from) * u;
        if (u >= 1) {
          this.app.ticker.remove(tick);
          target.alpha = to;
          resolve();
        }
      };
      this.app.ticker.add(tick);
    });
  }

  highlight(positions: Array<{ reel: number; row: number }>) {
    this.clearWins();
    const hits = new Set(positions.map((pos) => `${pos.reel}:${pos.row}`));
    this.cells.forEach((col, reel) => {
      col.forEach((cell, row) => {
        cell.alpha = hits.has(`${reel}:${row}`) ? 1 : 0.38;
      });
    });
    const overlay = new Graphics();
    overlay.label = "win";
    positions.forEach((pos) => {
      const rows = getReelRows(pos.reel);
      const x = GAP + pos.reel * CELL + 3;
      const y = GAP + (MAX_ROWS - rows) * CELL + pos.row * CELL + 3;
      overlay.roundRect(x, y, CELL - 6, CELL - 6, 8).stroke({ color: 0xe8c878, width: 3 });
    });
    this.root.addChild(overlay);
  }

  clearWins() {
    this.root.children
      .filter((child) => child.label === "win" || child.label === "scatter")
      .forEach((cell) => cell.destroy());
    this.teaseOverlay.clear();
    this.scatterOverlay.clear();
    this.cells.forEach((col) => {
      col.forEach((cell) => {
        cell.alpha = 1;
      });
    });
  }

  layout(viewWidth: number, viewHeight = 0) {
    const w = COLS * CELL + (COLS + 1) * GAP;
    const h = MAX_ROWS * CELL + 2 * GAP;
    const scaleX = Math.min(1, Math.max(0.35, (viewWidth - 20) / w));
    const scaleY = viewHeight > 0 ? Math.min(1, Math.max(0.35, (viewHeight - 20) / h)) : scaleX;
    const scale = Math.min(scaleX, scaleY);
    this.root.scale.set(scale);
    this.root.x = (viewWidth - w * scale) / 2;
    this.root.y = viewHeight > 0 ? (viewHeight - h * scale) / 2 : 8;
  }

  resize(viewWidth: number, viewHeight?: number) {
    this.layout(viewWidth, viewHeight);
  }
}

export function createBoard(app: Application) {
  const board = new BoardController(app);
  board.mount();
  return board;
}

export function boardSize() {
  return {
    width: COLS * CELL + (COLS + 1) * GAP,
    height: MAX_ROWS * CELL + 2 * GAP,
  };
}
