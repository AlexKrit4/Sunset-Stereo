import { Application, BlurFilter, Container, Graphics, Text } from "pixi.js";
import { createSymbolView } from "./symbols";
import { wait } from "../game/eventEmitter";
import { getReelRows, pickStripItems } from "../math/math.js";
import { MAX_ROWS, NUM_REELS } from "../math/config.js";
import type { RawSymbol, Position } from "../game/typesBookEvent";
import { unpadPosition, visibleNames } from "../rgs/bookView";

export const CELL = 90;
export const GAP = 5;
export const COLS = NUM_REELS;
export const ROWS = MAX_ROWS;

function boardMetrics() {
  return {
    width: COLS * CELL + GAP * 2,
    height: MAX_ROWS * CELL + GAP * 2,
  };
}

const START_STAGGER_MS = 95;
const STOP_STAGGER_MS = 300;
const LINEAR_MS = 900;
const LINEAR_FRAC = 0.86;
const BASE_FILLERS = 16;
const SPIN_WINDUP_PX = 30;
const SPIN_WINDUP_MS = 160;
const SPIN_GRAVITY_MS = 110;
const BLUR_MAX = 12;
const LAND_BOUNCE_PX = 9;
const LAND_BOUNCE_DOWN_MS = 52;
const LAND_BOUNCE_UP_MS = 150;
const SPIN_BELOW_ROWS = 4;
const NUDGE_WINDUP_MS = 100;
const NUDGE_PUSH_MS = 340;
const NUDGE_WINDUP_FRAC = 0.12;
const NUDGE_WINDUP_MAX_PX = 12;
const WIN_DIM_ALPHA = 0.38;
const WIN_DIM_FROM_REEL = 2;
const WIN_SHEEN_MS = 640;
const WIN_SHEEN_STAGGER_MS = 36;
const COCKTAIL_NAMES = new Set(["L5"]);
const ANIMATED_SYMBOL_NAMES = new Set(["H1", "H2", "H3", "H4", "H5", "L1", "L2", "L3", "L4", "L5"]);
const SYMBOL_ANIMATION_ALIASES: Record<string, string> = {
  high1: "H1",
  high2: "H2",
  high3: "H3",
  high4: "H4",
  high5: "H5",
  low1: "L1",
  low2: "L2",
  low3: "L3",
  low4: "L4",
  low5: "L5",
};
const COCKTAIL_LAND_MS = 720;
const SYMBOL_IDLE_MIN_MS = 2400;
const SYMBOL_IDLE_MAX_MS = 4400;
const COCKTAIL_IDLE_MS = 2400;
const COCKTAIL_WIN_MS = 1800;
const THEMED_LAND_MS = 900;
const THEMED_IDLE_MS = 2400;
const THEMED_WIN_MS = 1800;

type CellAnimation = {
  tick: () => void;
  finish: () => void;
};

function spinRng() {
  return {
    random: Math.random.bind(Math),
    randomInt(min: number, max: number) {
      return min + Math.floor(Math.random() * (max - min + 1));
    },
  };
}

function animationSymbolName(name: string) {
  return SYMBOL_ANIMATION_ALIASES[name] ?? name;
}

function applySpinBlur(strip: Container, blur: BlurFilter, strength: number) {
  if (strength <= 0.2) {
    blur.strengthY = 0;
    if (strip.filters?.length) strip.filters = [];
    return;
  }
  blur.strengthY = strength;
  if (strip.filters?.[0] !== blur) strip.filters = [blur];
}

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

function easeInOutQuad(t: number) {
  const x = Math.min(Math.max(t, 0), 1);
  return x < 0.5 ? 2 * x * x : 1 - (-2 * x + 2) ** 2 / 2;
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
  bouncePx: number;
  bounceAt: number;
  landed: boolean;
  finals: string[];
  rows: number;
  done: boolean;
  settled: boolean;
};

export type HoldStep = {
  board: string[][];
  isRespin: boolean;
  locked: Array<{ reel: number; row: number }>;
  totalWin: number;
  totalWays: number;
  wins: SpinRound["wins"];
  highlights: Array<{ reel: number; row: number }>;
};

export type BonusSpin = {
  steps: HoldStep[];
  paidWin: number;
  totalWays: number;
  wins: SpinRound["wins"];
  highlights: Array<{ reel: number; row: number }>;
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
  scatterCount: number;
  scatterPositions: Array<{ reel: number; row: number }>;
  bonusAwarded: number;
  bonusSpins: BonusSpin[];
  bonusWin: number;
  baseWin: number;
  totalWin: number;
  totalWays: number;
  wins: Array<{ sym: string; reelsMatched: number; ways: number; nudgeLineMult: number; win: number }>;
  highlights: Array<{ reel: number; row: number }>;
  bet?: number;
};

export type RoundHooks = {
  onBaseSettled?: (round: SpinRound) => void | Promise<void>;
  onBonusStart?: (round: SpinRound) => void | Promise<void>;
  onBonusSpinStart?: (index: number, total: number) => void | Promise<void>;
  onBonusSpinPaid?: (index: number, total: number, paidWin: number) => void | Promise<void>;
  onBonusEnd?: (round: SpinRound) => void | Promise<void>;
};

export class BoardController {
  app: Application;
  root = new Container();
  reels: Container[] = [];
  cells: Container[][] = [];
  private holds: Container[] = [];
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
  private sheenTick: (() => void) | null = null;
  private sheenResolve: (() => void) | null = null;
  private bonusDim = false;
  private brightCells = new Set<string>();
  private landingBright = new Set<string>();
  private cellAnimations = new Map<Container, CellAnimation>();
  private nextSymbolIdleAt = performance.now() + SYMBOL_IDLE_MIN_MS;
  private idleTick = () => this.tickSymbolIdle();

  constructor(app: Application) {
    this.app = app;
  }

  mount() {
    const window = new Container();
    window.x = GAP;
    window.y = GAP;

    for (let col = 0; col < COLS; col += 1) {
      const rows = getReelRows(col);
      const glass = new Graphics();
      glass.roundRect(0, 0, CELL, rows * CELL, 6).fill({ color: 0x14081c, alpha: 0.28 });
      const mask = new Graphics();
      mask.rect(0, 0, CELL, rows * CELL).fill(0xffffff);
      const host = new Container();
      host.x = col * CELL;
      host.y = (MAX_ROWS - rows) * CELL;
      host.addChild(glass, mask);
      host.mask = mask;

      const strip = new Container();
      const hold = new Container();
      hold.eventMode = "none";
      const blur = new BlurFilter({ strength: 0, quality: 3 });
      blur.strengthX = 0;
      blur.strengthY = 0;
      const seed = Array.from({ length: rows }, (_, row) => ["low4", "low5", "high3", "high1"][(col + row) % 4]);
      const below = pickStripItems(spinRng(), col, SPIN_BELOW_ROWS);
      this.paintStrip(strip, [...seed, ...below]);
      host.addChild(strip, hold);
      window.addChild(host);
      this.reels.push(strip);
      this.holds.push(hold);
      this.blurs.push(blur);
      this.visible.push(seed);
      this.cellMults.push(Array.from({ length: rows }, () => 1));
      this.cells.push((strip.children as Container[]).slice(0, rows));

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
    this.app.ticker.add(this.idleTick);
  }

  private setCellRestPosition(view: Container, row: number) {
    view.pivot.set(CELL / 2, CELL / 2);
    view.position.set(CELL / 2, Math.round(row * CELL) + CELL / 2);
    view.scale.set(1);
    view.rotation = 0;
  }

  private paintStrip(strip: Container, names: string[], mults?: number[]) {
    strip.children.forEach((child) => {
      if (child instanceof Container) this.cellAnimations.get(child)?.finish();
    });
    strip.removeChildren();
    names.forEach((name, index) => {
      const view = asView(name, mults?.[index] ?? 1);
      this.setCellRestPosition(view, index);
      strip.addChild(view);
    });
    strip.y = 0;
    strip.filters = [];
    strip.alpha = this.bonusDim ? WIN_DIM_ALPHA : 1;
  }

  private landStatic(col: number, names: string[], mults?: number[]) {
    const strip = this.reels[col];
    const resolvedMults = mults ?? Array.from({ length: names.length }, () => 1);
    const below = pickStripItems(spinRng(), col, SPIN_BELOW_ROWS);
    this.paintStrip(strip, [...names, ...below], [...resolvedMults, ...Array.from({ length: below.length }, () => 1)]);
    this.visible[col] = names.slice();
    this.cellMults[col] = resolvedMults.slice();
    this.cells[col] = (strip.children as Container[]).slice(0, names.length);
    this.cells[col].forEach((cell) => {
      cell.alpha = 1;
    });
  }

  private planSpin(waysGaps: number[], scatterGaps: number[], pace: "base" | "bonus" | "respin" = "base") {
    const linearMs = pace === "base" ? LINEAR_MS : 640;
    const startStagger = START_STAGGER_MS;
    const s0 = (MAX_ROWS + BASE_FILLERS) * CELL;
    const velocity = (LINEAR_FRAC * s0) / linearMs;
    const gravityLead = 0.5 * velocity * SPIN_GRAVITY_MS;
    const plans: Array<{ delay: number; fillers: number; velocity: number }> = [];
    let prevStop = 0;

    for (let col = 0; col < COLS; col += 1) {
      const delay = col * startStagger;
      const waysGap = pace === "base" ? waysGaps[col] || 0 : 0;
      const scatterGap = pace === "base" ? scatterGaps[col] || 0 : 0;
      const rows = getReelRows(col);
      const stopStagger = scatterGap > 0 ? 0 : STOP_STAGGER_MS;
      const minStop =
        col === 0 ? delay + SPIN_WINDUP_MS + linearMs : prevStop + stopStagger + waysGap + scatterGap;
      const tFall = Math.max(80, minStop - delay - SPIN_WINDUP_MS);
      let rest = velocity * tFall - SPIN_WINDUP_PX - gravityLead;
      rest = Math.max((rows + 10) * CELL, rest);
      let needed = Math.ceil(rest / CELL) - rows;
      needed = Math.max(10, needed);
      const restOffset = (rows + needed) * CELL;
      const actualFall = (restOffset + SPIN_WINDUP_PX + gravityLead) / velocity;
      prevStop = delay + SPIN_WINDUP_MS + actualFall;
      plans.push({ delay, fillers: needed, velocity });
    }
    return plans;
  }

  async playRound(round: SpinRound, hooks: RoundHooks = {}) {
    this.clearWins();
    this.clearHolds();
    this.badges.forEach((badge) => {
      badge.visible = false;
      badge.text = "";
    });
    const highlights = round.baseWin > 0 ? round.highlights : [];
    await this.spinTo(round.raw, round.waysGaps, round.scatterGaps, highlights, "base");
    if (highlights.length) {
      this.dimNonWinners(highlights, COLS - 1);
      await this.playWinSheen(highlights);
      await wait(round.baseWin >= (round.bet ?? 1) * 15 ? 900 : 380);
    }
    await hooks.onBaseSettled?.(round);
    if (round.bonusAwarded > 0) {
      await this.playBonus(round, hooks);
    }
  }

  private async playBonus(round: SpinRound, hooks: RoundHooks = {}) {
    await hooks.onBonusStart?.(round);
    await wait(720);
    this.scatterOverlay.clear();
    const total = round.bonusSpins.length;
    for (let i = 0; i < total; i += 1) {
      const spin = round.bonusSpins[i];
      await hooks.onBonusSpinStart?.(i, total);
      this.clearWins();
      this.clearHolds();
      for (let s = 0; s < spin.steps.length; s += 1) {
        const step = spin.steps[s];
        const pace = step.isRespin ? "respin" : "bonus";
        const holdDuring = step.isRespin ? spin.steps[s - 1].locked : [];
        await this.spinTo(step.board, [], [], step.highlights, pace, holdDuring);
        if (step.totalWin > 0) {
          this.setHolds(step.board, step.locked);
          this.dimNonWinners(step.highlights, COLS - 1);
        }
        if (s < spin.steps.length - 1) await wait(180);
      }
      const last = spin.steps[spin.steps.length - 1];
      if (spin.paidWin > 0 && last.highlights.length) {
        await this.playWinSheen(last.highlights);
        await wait(spin.paidWin >= (round.bet ?? 1) * 8 ? 520 : 220);
      } else {
        await wait(160);
      }
      await hooks.onBonusSpinPaid?.(i, total, spin.paidWin);
    }
    this.clearHolds();
    this.clearWins();
    await hooks.onBonusEnd?.(round);
  }

  async playBookReveal(
    board: RawSymbol[][],
    opts: {
      pace: "base" | "bonus" | "respin";
      anticipation?: number[];
      holds?: Position[];
      upcomingWins?: Position[];
    },
  ) {
    const names = visibleNames(board);
    const extra = Array.from({ length: COLS }, (_, col) => (opts.anticipation?.[col] || 0) * 480);
    const holds = (opts.holds ?? []).map(unpadPosition);
    const upcomingWins = (opts.upcomingWins ?? []).map(unpadPosition);
    this.landingBright = new Set(upcomingWins.map((pos) => `${pos.reel}:${pos.row}`));
    if (this.bonusDim) this.clearSheens();
    else this.clearWins();
    await this.spinTo(names, [], extra, [], opts.pace, holds);
  }

  applyBookHolds(board: RawSymbol[][], positions: Position[]) {
    this.syncHolds(visibleNames(board), positions.map(unpadPosition));
    if (this.bonusDim) this.applyBonusDim();
  }

  lockBonusWinners(positions: Position[]) {
    const cells = positions.map(unpadPosition);
    this.bonusDim = true;
    this.brightCells = new Set(cells.map((pos) => `${pos.reel}:${pos.row}`));
    this.landingBright.clear();
    if (this.visible.length) this.syncHolds(this.visible, cells);
    this.applyBonusDim();
  }

  async flashBonusWins(positions: Position[]) {
    const cells = positions.map(unpadPosition);
    if (!cells.length) return;
    await this.playWinSheen(cells);
    await wait(220);
  }

  async presentNewBonusWins(fresh: Position[], allWins: Position[], firstCombo: boolean) {
    if (firstCombo) {
      if (fresh.length) {
        await wait(80);
        await this.flashBonusWins(fresh);
      }
      this.lockBonusWinners(allWins);
      if (fresh.length) await wait(140);
      return;
    }
    this.lockBonusWinners(allWins);
    if (!fresh.length) return;
    await this.flashBonusWins(fresh);
  }

  async showBookWins(positions: Position[]) {
    const cells = positions.map(unpadPosition);
    if (!cells.length) return;
    if (this.bonusDim) {
      this.brightCells = new Set(cells.map((pos) => `${pos.reel}:${pos.row}`));
      if (this.visible.length) this.syncHolds(this.visible, cells);
      this.applyBonusDim();
    } else {
      this.dimNonWinners(cells, COLS - 1);
    }
    this.markSymbolActivity();
    await Promise.all([this.playWinSheen(cells), this.playSymbolWins(cells)]);
  }

  showBookScatters(_board: RawSymbol[][]) {}

  clearBookVisuals() {
    this.bonusDim = false;
    this.brightCells.clear();
    this.landingBright.clear();
    this.clearHolds();
    this.clearWins();
    this.syncBonusDimFlag();
  }

  async spinTo(
    raw: string[][],
    waysGaps: number[] = [],
    scatterGaps: number[] = [],
    highlights: Array<{ reel: number; row: number }> = [],
    pace: "base" | "bonus" | "respin" = "base",
    holds: Array<{ reel: number; row: number }> = [],
  ) {
    if (this.spinning) return;
    this.markSymbolActivity();
    this.finishCellAnimations();
    this.spinning = true;
    this.teaseOverlay.clear();
    this.scatterOverlay.clear();
    this.teaseOverlay.alpha = 1;
    const locked = new Set(holds.map((pos) => `${pos.reel}:${pos.row}`));
    if (holds.length) this.syncHolds(raw, holds);
    if (this.bonusDim) this.applyBonusDim();
    const plans = this.planSpin(waysGaps, scatterGaps, pace);
    const now = performance.now();
    this.jobs = [];
    const rng = spinRng();

    for (let col = 0; col < COLS; col += 1) {
      const rows = getReelRows(col);
      const finals = raw[col];
      const reelLocked = Array.from({ length: rows }, (_, row) => locked.has(`${col}:${row}`)).every(Boolean);
      const strip = this.reels[col];
      const blur = this.blurs[col];
      if (reelLocked) {
        this.landStatic(col, finals);
        continue;
      }
      const plan = plans[col];
      const fillers = pickStripItems(rng, col, plan.fillers);
      const restOffset = (rows + plan.fillers) * CELL;
      const below = pickStripItems(rng, col, SPIN_BELOW_ROWS);
      this.paintStrip(strip, [...finals, ...fillers, ...this.visible[col], ...below]);
      strip.y = -restOffset;
      applySpinBlur(strip, blur, 0);
      this.jobs.push({
        col,
        strip,
        blur,
        startAt: now + plan.delay,
        restOffset,
        windupPx: SPIN_WINDUP_PX,
        windupMs: SPIN_WINDUP_MS,
        gravityMs: SPIN_GRAVITY_MS,
        velocity: plan.velocity * (0.97 + col * 0.012),
        bouncePx: LAND_BOUNCE_PX + (col % 3) - 1,
        bounceAt: 0,
        landed: false,
        finals,
        rows,
        done: false,
        settled: false,
      });
    }

    this.onSettled = (col) => {
      if (this.bonusDim) {
        this.applyBonusDim();
        return;
      }
      if (highlights.length) this.dimNonWinners(highlights, col);
    };

    if (!this.jobs.length) {
      this.spinning = false;
      this.onSettled = null;
      return;
    }

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

  private holdLabel(reel: number, row: number) {
    return `hold:${reel}:${row}`;
  }

  private setHolds(board: string[][], positions: Array<{ reel: number; row: number }>) {
    this.syncHolds(board, positions);
  }

  private syncHolds(board: string[][], positions: Array<{ reel: number; row: number }>) {
    const wanted = new Set(positions.map((pos) => this.holdLabel(pos.reel, pos.row)));
    this.holds.forEach((layer) => {
      layer.children.slice().forEach((child) => {
        if (!wanted.has(child.label)) child.destroy();
      });
    });
    positions.forEach((pos) => {
      const layer = this.holds[pos.reel];
      const name = board[pos.reel]?.[pos.row];
      if (!layer || !name) return;
      const label = this.holdLabel(pos.reel, pos.row);
      if (layer.children.some((child) => child.label === label)) return;
      layer.addChild(this.makeHoldView(name, pos));
    });
  }

  private makeHoldView(name: string, pos: { reel: number; row: number }) {
    const view = asView(name);
    view.label = this.holdLabel(pos.reel, pos.row);
    view.eventMode = "none";
    view.pivot.set(CELL / 2, CELL / 2);
    view.x = CELL / 2;
    view.y = Math.round(pos.row * CELL) + CELL / 2;
    return view;
  }

  private clearHolds() {
    this.holds.forEach((layer) => layer.removeChildren());
  }

  private fallOffset(job: SpinJob, fallMs: number) {
    const apex = job.restOffset + job.windupPx;
    if (fallMs < job.gravityMs) {
      const accel = job.velocity / job.gravityMs;
      return apex - 0.5 * accel * fallMs * fallMs;
    }
    const dist = 0.5 * job.velocity * job.gravityMs + job.velocity * (fallMs - job.gravityMs);
    return apex - dist;
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
      if (job.done) continue;
      if (job.landed) {
        this.tickLandBounce(job, now);
        continue;
      }
      if (now < job.startAt) continue;
      const elapsed = now - job.startAt;
      if (elapsed < job.windupMs) {
        const tossed = job.windupPx * easeOutQuad(elapsed / job.windupMs);
        job.strip.y = -(job.restOffset + tossed);
        applySpinBlur(job.strip, job.blur, 0);
        continue;
      }
      const fallMs = elapsed - job.windupMs;
      const offset = this.fallOffset(job, fallMs);
      if (offset <= 0) {
        this.landReel(job, now);
        continue;
      }
      job.strip.y = -offset;
      const spinBlur = BLUR_MAX * Math.min(1, this.fallSpeed(job, fallMs) / job.velocity);
      applySpinBlur(job.strip, job.blur, offset < CELL ? spinBlur * (offset / CELL) : spinBlur);
    }
  }

  private tickLandBounce(job: SpinJob, now: number) {
    const elapsed = now - job.bounceAt;
    const down = LAND_BOUNCE_DOWN_MS;
    const up = LAND_BOUNCE_UP_MS;
    if (elapsed < down) {
      job.strip.y = job.bouncePx * easeOutQuad(elapsed / down);
      return;
    }
    const back = elapsed - down;
    if (back < up) {
      job.strip.y = job.bouncePx * (1 - easeOutCubic(back / up));
      return;
    }
    job.strip.y = 0;
    job.done = true;
  }

  private landReel(job: SpinJob, now: number) {
    job.landed = true;
    job.bounceAt = now;
    applySpinBlur(job.strip, job.blur, 0);
    this.landStatic(job.col, job.finals);
    this.playSymbolLanding(job.col);
    job.strip.y = 0;
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
    this.setCellRestPosition(next, row);
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

  private traceSymbolAnimation(phase: "land" | "idle" | "win", name: string) {
    if (typeof document === "undefined") return;
    const count = Number(document.body.dataset.symbolAnimationCount ?? 0) + 1;
    const phaseKey = `symbolAnimation${phase[0].toUpperCase()}${phase.slice(1)}Count`;
    document.body.dataset.symbolAnimation = `${phase}:${name}`;
    document.body.dataset.symbolAnimationCount = String(count);
    document.body.dataset[phaseKey] = String(Number(document.body.dataset[phaseKey] ?? 0) + 1);
  }

  private markSymbolActivity() {
    const spread = SYMBOL_IDLE_MAX_MS - SYMBOL_IDLE_MIN_MS;
    this.nextSymbolIdleAt = performance.now() + SYMBOL_IDLE_MIN_MS + Math.random() * spread;
  }

  private clearCellEffects(cell: Container) {
    cell.children
      .filter((child) => child.label?.startsWith("symbol-fx"))
      .forEach((child) => child.destroy());
  }

  private finishCellAnimations() {
    [...this.cellAnimations.values()].forEach((animation) => animation.finish());
  }

  private animateCell(
    cell: Container,
    duration: number,
    render: (progress: number, elapsed: number) => void,
  ) {
    const restX = cell.x;
    const restY = cell.y;
    let settled = false;
    let resolveAnimation: () => void = () => {};
    const promise = new Promise<void>((resolve) => {
      resolveAnimation = resolve;
    });
    const reset = () => {
      cell.position.set(restX, restY);
      cell.scale.set(1);
      cell.rotation = 0;
      this.resetSymbolParts(cell);
      this.clearCellEffects(cell);
    };
    const finish = () => {
      if (settled) return;
      settled = true;
      this.app.ticker.remove(tick);
      reset();
      this.cellAnimations.delete(cell);
      resolveAnimation();
    };
    const started = performance.now();
    const tick = () => {
      if (!cell.parent) {
        finish();
        return;
      }
      const elapsed = performance.now() - started;
      const progress = Math.min(elapsed / duration, 1);
      render(progress, elapsed);
      if (progress >= 1) finish();
    };
    this.cellAnimations.set(cell, { tick, finish });
    render(0, 0);
    this.app.ticker.add(tick);
    return promise;
  }

  private playSymbolLanding(reel: number) {
    this.visible[reel]?.forEach((rawName, row) => {
      const name = animationSymbolName(rawName);
      if (!ANIMATED_SYMBOL_NAMES.has(name)) return;
      const cell = this.cells[reel]?.[row];
      if (!cell) return;
      this.traceSymbolAnimation("land", name);
      if (!COCKTAIL_NAMES.has(name)) {
        void this.playThemedLanding(cell, name);
        return;
      }
      this.cellAnimations.get(cell)?.finish();
      this.clearCellEffects(cell);
      const splash = new Graphics();
      splash.label = "symbol-fx-cocktail-land";
      splash.ellipse(CELL / 2, CELL * 0.8, CELL * 0.28, 5).stroke({
        color: 0xffd37a,
        width: 3,
        alpha: 0.9,
      });
      [-1, 0, 1].forEach((offset) => {
        splash.circle(CELL / 2 + offset * 15, CELL * 0.72 - Math.abs(offset) * 3, 2.5).fill({
          color: offset === 0 ? 0xfff2be : 0xffa85c,
          alpha: 0.92,
        });
      });
      splash.alpha = 0;
      cell.addChild(splash);
      const restY = cell.y;
      void this.animateCell(cell, COCKTAIL_LAND_MS, (progress) => {
        if (progress < 0.2) {
          const u = easeOutQuad(progress / 0.2);
          cell.y = restY - 16 + 22 * u;
          cell.scale.set(0.82 + 0.36 * u, 1.2 - 0.42 * u);
          cell.rotation = -0.09 + 0.16 * u;
          splash.alpha = u;
          splash.scale.set(0.7 + u * 0.35);
        } else if (progress < 0.58) {
          const u = easeOutCubic((progress - 0.2) / 0.38);
          cell.y = restY + 6 - 10 * u;
          cell.scale.set(1.18 - 0.22 * u, 0.78 + 0.32 * u);
          cell.rotation = 0.07 - 0.11 * u;
          splash.alpha = 1 - u;
          splash.scale.set(1.05 + u * 0.35);
        } else {
          const u = easeOutCubic((progress - 0.58) / 0.42);
          cell.y = restY - 4 + 4 * u;
          cell.scale.set(0.96 + 0.04 * u, 1.1 - 0.1 * u);
          cell.rotation = -0.04 * (1 - u);
          splash.alpha = 0;
        }
      });
    });
  }

  private tickSymbolIdle() {
    const now = performance.now();
    if (
      now < this.nextSymbolIdleAt ||
      this.spinning ||
      this.bonusDim ||
      Boolean(this.sheenTick) ||
      this.cellAnimations.size > 0
    ) {
      return;
    }
    const candidates: Array<{ cell: Container; name: string }> = [];
    this.visible.forEach((names, reel) => {
      names.forEach((rawName, row) => {
        const name = animationSymbolName(rawName);
        const cell = this.cells[reel]?.[row];
        if (ANIMATED_SYMBOL_NAMES.has(name) && cell?.parent) candidates.push({ cell, name });
      });
    });
    if (!candidates.length) {
      this.markSymbolActivity();
      return;
    }
    const { cell, name } = candidates[Math.floor(Math.random() * candidates.length)];
    this.traceSymbolAnimation("idle", name);
    if (!COCKTAIL_NAMES.has(name)) {
      void this.playThemedIdle(cell, name).finally(() => this.markSymbolActivity());
      return;
    }
    this.cellAnimations.get(cell)?.finish();
    this.clearCellEffects(cell);
    const glint = new Graphics();
    glint.label = "symbol-fx-cocktail-idle";
    glint
      .moveTo(CELL * 0.7, CELL * 0.19)
      .lineTo(CELL * 0.7, CELL * 0.33)
      .moveTo(CELL * 0.63, CELL * 0.26)
      .lineTo(CELL * 0.77, CELL * 0.26)
      .stroke({ color: 0xfff7d0, width: 2.5, alpha: 0.95 });
    glint.alpha = 0;
    glint.scale.set(0.4);
    cell.addChild(glint);
    const restY = cell.y;
    void this.animateCell(cell, COCKTAIL_IDLE_MS, (progress) => {
      const wave = Math.sin(progress * Math.PI * 4);
      const envelope = Math.sin(progress * Math.PI);
      cell.rotation = wave * envelope * 0.12;
      cell.y = restY - envelope * 8;
      cell.scale.set(1 + envelope * 0.06, 1 - envelope * 0.035);
      glint.alpha = Math.max(0, Math.sin(progress * Math.PI * 2)) * 0.95;
      glint.scale.set(0.4 + envelope * 0.85);
      glint.rotation = progress * Math.PI * 0.8;
    }).finally(() => this.markSymbolActivity());
  }

  private playSymbolWins(positions: Array<{ reel: number; row: number }>) {
    const seen = new Set<Container>();
    const symbols = positions
      .map((pos) => ({
        cell: this.sheenCell(pos),
        name: animationSymbolName(this.visible[pos.reel]?.[pos.row] ?? ""),
      }))
      .filter((entry): entry is { cell: Container; name: string } => {
        if (!entry.cell || !ANIMATED_SYMBOL_NAMES.has(entry.name) || seen.has(entry.cell)) return false;
        seen.add(entry.cell);
        this.traceSymbolAnimation("win", entry.name);
        return true;
      });
    if (!symbols.length) return Promise.resolve();
    return Promise.all(
      symbols.map(({ cell, name }, index) => {
        if (!COCKTAIL_NAMES.has(name)) return this.playThemedWin(cell, name, index);
        this.cellAnimations.get(cell)?.finish();
        this.clearCellEffects(cell);
        const celebration = new Graphics();
        celebration.label = "symbol-fx-cocktail-win";
        celebration.circle(CELL / 2, CELL / 2, CELL * 0.39).stroke({
          color: 0xffd060,
          width: 4,
          alpha: 0.95,
        });
        const bubbles = [
          { x: 21, y: 62, r: 3 },
          { x: 68, y: 60, r: 4 },
          { x: 28, y: 29, r: 2.5 },
          { x: 73, y: 28, r: 2.5 },
        ];
        bubbles.forEach((bubble) => {
          celebration.circle(bubble.x, bubble.y, bubble.r).stroke({
            color: 0xfff2b0,
            width: 2,
            alpha: 0.9,
          });
        });
        celebration.blendMode = "add";
        celebration.alpha = 0;
        celebration.scale.set(0.72);
        cell.addChild(celebration);
        const restY = cell.y;
        return this.animateCell(cell, COCKTAIL_WIN_MS + index * 25, (progress) => {
          const entrance = easeOutCubic(Math.min(progress / 0.22, 1));
          const exit = progress > 0.78 ? 1 - easeOutQuad((progress - 0.78) / 0.22) : 1;
          const energy = entrance * exit;
          cell.y = restY - Math.sin(progress * Math.PI * 2) * 9 * energy;
          cell.rotation = Math.sin(progress * Math.PI * 6) * 0.13 * energy;
          const pulse = 1 + Math.sin(progress * Math.PI * 4) * 0.17 * energy;
          cell.scale.set(pulse);
          celebration.alpha = energy * (0.58 + Math.sin(progress * Math.PI * 4) * 0.32);
          celebration.scale.set(0.72 + entrance * 0.5 + progress * 0.18);
          celebration.rotation = progress * Math.PI * 1.5;
        });
      }),
    ).then(() => undefined);
  }

  private symbolPart(cell: Container, name: string) {
    const part = cell.children.find((child) => child.label === `symbol-part:${name}`);
    return part instanceof Container ? part : null;
  }

  private equalizerParts(cell: Container) {
    return [1, 2, 3, 4]
      .map((index) => this.symbolPart(cell, `equalizer-bar-${index}`))
      .filter((part): part is Container => Boolean(part));
  }

  private resetSymbolParts(cell: Container) {
    cell.children
      .filter((child) => child.label?.startsWith("symbol-part:"))
      .forEach((child) => {
        child.scale.set(1);
        child.rotation = 0;
        child.alpha = 1;
      });
  }

  private prepareThemedAnimation(cell: Container) {
    this.cellAnimations.get(cell)?.finish();
    this.clearCellEffects(cell);
    this.resetSymbolParts(cell);
  }

  private playThemedLanding(cell: Container, name: string) {
    this.prepareThemedAnimation(cell);
    const impact = new Graphics();
    impact.label = "symbol-fx-land";
    impact.ellipse(CELL / 2, CELL * 0.82, CELL * 0.3, 4).fill({
      color: name === "L4" ? 0x8cff9d : 0xffc064,
      alpha: 0.75,
    });
    impact.alpha = 0;
    cell.addChild(impact);
    const crown = this.symbolPart(cell, "palm-crown");
    const bars = this.equalizerParts(cell);
    const restY = cell.y;
    return this.animateCell(cell, THEMED_LAND_MS, (progress) => {
      if (progress < 0.26) {
        const u = easeOutQuad(progress / 0.26);
        cell.y = restY - 18 + u * 24;
        cell.scale.set(0.9 + u * 0.18, 1.12 - u * 0.3);
        impact.alpha = u;
        impact.scale.set(0.55 + u * 0.65, 0.7 + u * 0.35);
      } else {
        const u = (progress - 0.26) / 0.74;
        const damping = 1 - u;
        cell.y = restY + Math.cos(u * Math.PI * 3) * 6 * damping;
        cell.scale.set(1 + Math.sin(u * Math.PI * 3) * 0.08 * damping, 1 - Math.sin(u * Math.PI * 3) * 0.1 * damping);
        impact.alpha = Math.max(0, 1 - u * 2.4);
      }

      if (name === "L4" && crown) {
        crown.rotation = Math.sin(progress * Math.PI * 5) * (1 - progress) * 0.25;
        crown.scale.set(1 + Math.sin(progress * Math.PI * 4) * (1 - progress) * 0.06);
      } else if (name === "L3" && bars.length) {
        bars.forEach((bar, index) => {
          const phase = Math.min(Math.max((progress - index * 0.07) / 0.72, 0), 1);
          bar.scale.y = 1 - Math.sin(phase * Math.PI) * 0.5;
        });
      } else if (name === "H3") {
        cell.rotation = Math.sin(progress * Math.PI * 4) * (1 - progress) * 0.08;
      } else if (name === "H4") {
        cell.rotation = Math.sin(progress * Math.PI * 3) * (1 - progress) * 0.07;
      } else if (name === "H5") {
        cell.scale.x *= 1 - Math.sin(progress * Math.PI) * 0.04;
      }
    });
  }

  private playThemedIdle(cell: Container, name: string) {
    this.prepareThemedAnimation(cell);
    const fx = new Graphics();
    fx.label = "symbol-fx-idle";
    const crown = this.symbolPart(cell, "palm-crown");
    const bars = this.equalizerParts(cell);
    const restX = cell.x;
    const restY = cell.y;

    if (name === "L2") {
      fx.circle(67, 27, 3).fill({ color: 0xffed9a, alpha: 0.95 });
      fx.circle(73, 16, 2).fill({ color: 0xff9bd2, alpha: 0.9 });
    } else if (name === "L1" || name === "H2" || name === "H4") {
      [18, 27, 36].forEach((radius) =>
        fx.circle(CELL / 2, CELL / 2, radius).stroke({ color: 0xffc86b, width: 2, alpha: 0.55 }),
      );
    } else if (name === "H3") {
      [31, 59].forEach((x) => {
        fx.circle(x, 45, 8).stroke({ color: 0xffee9a, width: 2, alpha: 0.9 });
        fx.moveTo(x, 37).lineTo(x, 53).stroke({ color: 0xffee9a, width: 1.5, alpha: 0.8 });
      });
    } else if (name === "H5") {
      [27, 38, 49, 60].forEach((x) => fx.circle(x, 25, 2.5).fill({ color: 0xffd060, alpha: 0.95 }));
    } else if (name === "H1") {
      fx.circle(CELL / 2, CELL / 2, 8).stroke({ color: 0xffe2a0, width: 2, alpha: 0.85 });
      fx.moveTo(CELL / 2, CELL / 2).lineTo(66, 35).stroke({ color: 0xffe2a0, width: 2, alpha: 0.85 });
    }
    fx.alpha = 0;
    cell.addChild(fx);

    return this.animateCell(cell, THEMED_IDLE_MS, (progress) => {
      const envelope = Math.sin(progress * Math.PI);
      const wave = Math.sin(progress * Math.PI * 4);
      fx.alpha = envelope * 0.85;

      if (name === "L4") {
        cell.rotation = wave * envelope * 0.055;
        cell.y = restY - envelope * 4;
        if (crown) crown.rotation = Math.sin(progress * Math.PI * 6) * envelope * 0.09;
      } else if (name === "L3" && bars.length) {
        bars.forEach((bar, index) => {
          bar.scale.y = 1 - (0.1 + index * 0.035) * envelope * (0.5 + 0.5 * Math.sin(progress * Math.PI * 6 + index));
        });
      } else if (name === "L2") {
        cell.y = restY - envelope * 7;
        cell.rotation = wave * envelope * 0.055;
        fx.y = -envelope * 8;
      } else if (name === "L1") {
        const pulse = 1 + envelope * (0.025 + 0.025 * Math.sin(progress * Math.PI * 8));
        cell.scale.set(pulse);
        fx.scale.set(0.75 + progress * 0.7);
        fx.alpha *= 1 - progress;
      } else if (name === "H1") {
        cell.rotation = easeInOutQuad(progress) * Math.PI * 0.7;
        fx.rotation = -cell.rotation;
      } else if (name === "H2") {
        const beat = Math.max(0, Math.sin(progress * Math.PI * 6)) * envelope;
        cell.scale.set(1 + beat * 0.06);
        fx.scale.set(0.75 + progress * 0.55);
        fx.alpha *= 1 - progress;
      } else if (name === "H3") {
        cell.rotation = wave * envelope * 0.025;
        fx.rotation = progress * Math.PI * 2;
      } else if (name === "H4") {
        cell.rotation = wave * envelope * 0.07;
        fx.x = wave * 3;
        fx.scale.set(0.8 + progress * 0.45);
      } else if (name === "H5") {
        cell.x = restX + wave * envelope * 0.5;
        fx.alpha = (0.3 + 0.7 * Math.max(0, Math.sin(progress * Math.PI * 8))) * envelope;
      }
    });
  }

  private playThemedWin(cell: Container, name: string, index: number) {
    this.prepareThemedAnimation(cell);
    const fx = new Container();
    fx.label = "symbol-fx-win";
    const drawing = new Graphics();
    fx.addChild(drawing);
    const crown = this.symbolPart(cell, "palm-crown");
    const bars = this.equalizerParts(cell);
    const equalizerCells: Graphics[] = [];
    const restX = cell.x;
    const restY = cell.y;

    if (name === "L1") {
      [18, 28, 38].forEach((radius) =>
        drawing.circle(CELL / 2, CELL / 2, radius).stroke({ color: 0xffd060, width: 3, alpha: 0.9 }),
      );
    } else if (name === "L3") {
      const heights = [4, 6, 3, 5];
      heights.forEach((height, column) => {
        for (let row = 0; row < height; row += 1) {
          const cellBar = new Graphics();
          cellBar.roundRect(21 + column * 13, 66 - row * 10, 9, 7, 2).fill({
            color: row > 3 ? 0xff6b5c : 0xffd45c,
            alpha: 0.95,
          });
          cellBar.alpha = 0;
          fx.addChild(cellBar);
          equalizerCells.push(cellBar);
        }
      });
    } else if (name === "L4") {
      [[18, 25], [72, 22], [14, 56], [76, 58], [46, 12]].forEach(([x, y], particle) =>
        drawing.circle(x, y, 2 + (particle % 2)).fill({ color: particle % 2 ? 0x7dff9b : 0xffe27a, alpha: 0.95 }),
      );
    } else if (name === "H1") {
      drawing.circle(45, 45, 39).stroke({ color: 0xffca62, width: 3, alpha: 0.95 });
      drawing.moveTo(45, 45).lineTo(70, 24).stroke({ color: 0xffffff, width: 2, alpha: 0.9 });
    } else if (name === "H2") {
      [22, 32, 42].forEach((radius) =>
        drawing.circle(45, 45, radius).stroke({ color: 0xffc45c, width: 2.5, alpha: 0.8 }),
      );
    } else if (name === "H3") {
      [31, 59].forEach((x) => {
        drawing.circle(x, 45, 10).stroke({ color: 0xffeea0, width: 2.5, alpha: 0.95 });
        drawing.moveTo(x, 35).lineTo(x, 55).stroke({ color: 0xffeea0, width: 2, alpha: 0.95 });
      });
      drawing.moveTo(31, 45).bezierCurveTo(41, 26, 49, 64, 59, 45).stroke({ color: 0xff8fbc, width: 2, alpha: 0.85 });
    } else if (name === "H4") {
      [20, 31, 42].forEach((radius) =>
        drawing.circle(45, 39, radius).stroke({ color: 0xffd978, width: 2.5, alpha: 0.82 }),
      );
    } else if (name === "H5") {
      drawing
        .moveTo(16, 60)
        .lineTo(31, 42)
        .lineTo(40, 52)
        .lineTo(56, 30)
        .lineTo(73, 48)
        .stroke({ color: 0xffed72, width: 3, alpha: 0.95 });
    } else if (name === "L2") {
      drawing.circle(45, 45, 39).stroke({ color: 0xffd66b, width: 3, alpha: 0.9 });
      drawing.circle(45, 45, 33).stroke({ color: 0xff79d9, width: 2, alpha: 0.75 });
    }
    drawing.blendMode = "add";
    fx.alpha = 0;
    cell.addChild(fx);

    return this.animateCell(cell, THEMED_WIN_MS + index * 20, (progress) => {
      const entrance = easeOutCubic(Math.min(progress / 0.2, 1));
      const exit = progress > 0.82 ? 1 - easeOutQuad((progress - 0.82) / 0.18) : 1;
      const energy = entrance * exit;
      fx.alpha = energy;

      if (name === "L2") {
        cell.rotation = easeInOutQuad(progress) * Math.PI * 2;
        cell.scale.set(1 + Math.sin(progress * Math.PI * 4) * energy * 0.08);
        fx.rotation = -cell.rotation * 0.35;
      } else if (name === "L1") {
        const kick = Math.max(0, Math.sin(progress * Math.PI * 8)) * energy;
        cell.scale.set(1 + kick * 0.1);
        fx.scale.set(0.55 + progress * 1.2);
        fx.alpha *= 1 - progress * 0.85;
      } else if (name === "L3") {
        bars.forEach((bar, barIndex) => {
          const local = Math.min(Math.max(progress * 2.2 - barIndex * 0.1, 0), 1);
          bar.scale.y = 0.28 + easeOutCubic(local) * 0.72;
        });
        equalizerCells.forEach((barCell, cellIndex) => {
          const local = Math.min(Math.max(progress * 2.4 - cellIndex * 0.035, 0), 1);
          barCell.alpha = local * exit;
        });
        cell.scale.set(1 + Math.sin(progress * Math.PI * 6) * energy * 0.04);
      } else if (name === "L4") {
        if (crown) crown.rotation = Math.sin(progress * Math.PI * 12) * energy * 0.13;
        cell.scale.set(1 + Math.sin(progress * Math.PI * 4) * energy * 0.07);
        drawing.rotation = progress * Math.PI * 2;
      } else if (name === "H1") {
        cell.rotation = progress * Math.PI * 4;
        fx.rotation = -progress * Math.PI * 2;
        cell.scale.set(1 + energy * 0.08);
      } else if (name === "H2") {
        const beat = Math.max(0, Math.sin(progress * Math.PI * 8)) * energy;
        cell.scale.set(1 + beat * 0.12);
        fx.scale.set(0.6 + progress * 1.15);
        fx.alpha *= 1 - progress * 0.75;
      } else if (name === "H3") {
        cell.rotation = Math.sin(progress * Math.PI * 8) * energy * 0.04;
        drawing.rotation = progress * Math.PI * 4;
      } else if (name === "H4") {
        cell.rotation = Math.sin(progress * Math.PI * 6) * energy * 0.08;
        fx.scale.set(0.65 + progress * 1.1);
        fx.alpha *= 1 - progress * 0.78;
      } else if (name === "H5") {
        cell.x = restX + Math.sin(progress * Math.PI * 14) * energy * 2;
        cell.scale.set(1 + Math.sin(progress * Math.PI * 6) * energy * 0.06);
        drawing.alpha = 0.45 + Math.max(0, Math.sin(progress * Math.PI * 10)) * 0.55;
      }
      cell.y = restY - Math.sin(progress * Math.PI * 2) * energy * 4;
    });
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

  private dimNonWinners(positions: Array<{ reel: number; row: number }>, upTo: number) {
    if (upTo < WIN_DIM_FROM_REEL || !positions.length) return;
    const hits = new Set(positions.map((pos) => `${pos.reel}:${pos.row}`));
    for (let reel = 0; reel <= upTo; reel += 1) {
      const strip = this.reels[reel];
      if (strip) strip.alpha = 1;
      this.cells[reel]?.forEach((cell, row) => {
        cell.alpha = hits.has(`${reel}:${row}`) ? 1 : WIN_DIM_ALPHA;
      });
    }
    for (let reel = upTo + 1; reel < COLS; reel += 1) {
      const strip = this.reels[reel];
      if (strip) strip.alpha = WIN_DIM_ALPHA;
    }
  }

  private applyBonusDim() {
    if (!this.bonusDim) return;
    const bright = new Set([...this.brightCells, ...this.landingBright]);
    const spinning = new Set(this.jobs.filter((job) => !job.landed).map((job) => job.col));
    for (let reel = 0; reel < COLS; reel += 1) {
      const strip = this.reels[reel];
      const hold = this.holds[reel];
      if (hold) hold.alpha = 1;
      if (!strip) continue;
      if (spinning.has(reel)) {
        strip.alpha = WIN_DIM_ALPHA;
        continue;
      }
      strip.alpha = 1;
      this.cells[reel]?.forEach((cell, row) => {
        cell.alpha = bright.has(`${reel}:${row}`) ? 1 : WIN_DIM_ALPHA;
      });
    }
    this.syncBonusDimFlag();
  }

  private syncBonusDimFlag() {
    if (typeof document === "undefined") return;
    document.body.dataset.bonusDim = this.bonusDim ? "1" : "0";
    document.body.dataset.bonusBright = String(this.brightCells.size);
  }

  private sheenCell(pos: { reel: number; row: number }) {
    const key = `${pos.reel}:${pos.row}`;
    if (this.landingBright.has(key)) return this.cells[pos.reel]?.[pos.row];
    if (this.bonusDim) {
      const layer = this.holds[pos.reel];
      const held = layer?.children.find((child) => child.label === this.holdLabel(pos.reel, pos.row));
      if (held instanceof Container) return held;
    }
    return this.cells[pos.reel]?.[pos.row];
  }

  private playWinSheen(positions: Array<{ reel: number; row: number }>) {
    this.clearSheens();
    const pad = CELL * 0.06;
    const inner = CELL - pad * 2;
    const jobs = positions
      .map((pos) => {
        const cell = this.sheenCell(pos);
        if (!cell) return null;
        const wrap = new Container();
        wrap.label = "sheen";
        wrap.eventMode = "none";
        const mask = new Graphics();
        mask.roundRect(pad, pad, inner, inner, 10).fill(0xffffff);
        const pulse = new Graphics();
        pulse.roundRect(pad, pad, inner, inner, 10).fill({ color: 0xffe7a8, alpha: 0.7 });
        pulse.blendMode = "add";
        pulse.alpha = 0;
        const shine = new Graphics();
        const len = CELL * 2.35;
        shine.rect(-len / 2, -16, len, 32).fill({ color: 0xfff4dc, alpha: 0.28 });
        shine.rect(-len / 2, -8, len, 16).fill({ color: 0xfffaf2, alpha: 0.5 });
        shine.rect(-len / 2, -2.4, len, 4.8).fill({ color: 0xffffff, alpha: 0.92 });
        shine.rotation = -Math.PI / 4;
        shine.blendMode = "add";
        wrap.addChild(mask, pulse, shine);
        wrap.mask = mask;
        cell.addChild(wrap);
        return {
          shine,
          pulse,
          delay: pos.reel * WIN_SHEEN_STAGGER_MS + pos.row * 12,
          fromX: pad - 8,
          fromY: pad - 8,
          toX: pad + inner + 8,
          toY: pad + inner + 8,
        };
      })
      .filter((job): job is NonNullable<typeof job> => Boolean(job));

    if (!jobs.length) return Promise.resolve();
    for (const job of jobs) {
      job.shine.x = job.fromX;
      job.shine.y = job.fromY;
    }

    const totalMs = WIN_SHEEN_MS + Math.max(...jobs.map((job) => job.delay));
    return new Promise<void>((resolve) => {
      this.sheenResolve = resolve;
      const start = performance.now();
      const tick = () => {
        const elapsed = performance.now() - start;
        for (const job of jobs) {
          const local = Math.min(Math.max((elapsed - job.delay) / WIN_SHEEN_MS, 0), 1);
          const u = easeInOutQuad(local);
          job.shine.x = job.fromX + (job.toX - job.fromX) * u;
          job.shine.y = job.fromY + (job.toY - job.fromY) * u;
          job.pulse.alpha = Math.sin(local * Math.PI) * 0.9;
        }
        if (elapsed >= totalMs) this.clearSheens();
      };
      this.sheenTick = tick;
      this.app.ticker.add(tick);
    });
  }

  private clearSheens() {
    if (this.sheenTick) {
      this.app.ticker.remove(this.sheenTick);
      this.sheenTick = null;
    }
    const stripSheens = (cell: Container) => {
      cell.children
        .filter((child) => child.label === "sheen")
        .forEach((child) => child.destroy());
    };
    this.cells.forEach((col) => {
      col.forEach(stripSheens);
    });
    this.holds.forEach((layer) => {
      layer.children.forEach((child) => {
        if (child instanceof Container) stripSheens(child);
      });
    });
    const resolve = this.sheenResolve;
    this.sheenResolve = null;
    resolve?.();
  }

  clearWins() {
    this.clearSheens();
    this.root.children
      .filter((child) => child.label === "win" || child.label === "scatter")
      .forEach((cell) => cell.destroy());
    this.teaseOverlay.clear();
    this.scatterOverlay.clear();
    this.reels.forEach((strip) => {
      strip.alpha = 1;
    });
    this.cells.forEach((col) => {
      col.forEach((cell) => {
        cell.alpha = 1;
      });
    });
  }

  layout(viewWidth: number, viewHeight = 0) {
    const { width: w, height: h } = boardMetrics();
    const padX = 6;
    const padTop = 22;
    const padBottom = 6;
    const scaleX = Math.max(0.35, (viewWidth - padX * 2) / w);
    const scaleY =
      viewHeight > 0 ? Math.max(0.35, (viewHeight - padTop - padBottom) / h) : scaleX;
    const scale = Math.min(scaleX, scaleY);
    this.root.scale.set(scale);
    this.root.x = (viewWidth - w * scale) / 2;
    this.root.y =
      viewHeight > 0 ? padTop + (viewHeight - padTop - padBottom - h * scale) / 2 : padTop;
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
  return boardMetrics();
}
