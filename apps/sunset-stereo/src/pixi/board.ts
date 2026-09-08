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
const WIN_SHEEN_MS = 520;
const WIN_SHEEN_STAGGER_MS = 42;

function spinRng() {
  return {
    random: Math.random.bind(Math),
    randomInt(min: number, max: number) {
      return min + Math.floor(Math.random() * (max - min + 1));
    },
  };
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
  bet?: number;
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
  private sheenTick: (() => void) | null = null;
  private sheenResolve: (() => void) | null = null;

  constructor(app: Application) {
    this.app = app;
  }

  mount() {
    const frame = new Graphics();
    const w = COLS * CELL + (COLS + 1) * GAP;
    const h = MAX_ROWS * CELL + 2 * GAP;
    frame.roundRect(0, 0, w, h, 8).fill({ color: 0x14081c, alpha: 0.12 });
    frame.roundRect(0, 0, w, h, 8).stroke({ color: 0xc4a574, width: 2, alpha: 0.85 });
    this.root.addChild(frame);

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
      const blur = new BlurFilter({ strength: 0, quality: 3 });
      blur.strengthX = 0;
      blur.strengthY = 0;
      const seed = Array.from({ length: rows }, (_, row) => ["low4", "low5", "high3", "high1"][(col + row) % 4]);
      const below = pickStripItems(spinRng(), col, SPIN_BELOW_ROWS);
      this.paintStrip(strip, [...seed, ...below]);
      host.addChild(strip);
      window.addChild(host);
      this.reels.push(strip);
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
    const below = pickStripItems(spinRng(), col, SPIN_BELOW_ROWS);
    this.paintStrip(strip, [...names, ...below], [...resolvedMults, ...Array.from({ length: below.length }, () => 1)]);
    this.visible[col] = names.slice();
    this.cellMults[col] = resolvedMults.slice();
    this.cells[col] = (strip.children as Container[]).slice(0, names.length);
    this.cells[col].forEach((cell) => {
      cell.alpha = 1;
    });
  }

  private planSpin(waysGaps: number[], scatterGaps: number[]) {
    const s0 = (MAX_ROWS + BASE_FILLERS) * CELL;
    const velocity = (LINEAR_FRAC * s0) / LINEAR_MS;
    const gravityLead = 0.5 * velocity * SPIN_GRAVITY_MS;
    const plans: Array<{ delay: number; fillers: number; velocity: number }> = [];
    let prevStop = 0;

    for (let col = 0; col < COLS; col += 1) {
      const delay = col * START_STAGGER_MS;
      const waysGap = waysGaps[col] || 0;
      const scatterGap = scatterGaps[col] || 0;
      const rows = getReelRows(col);
      const stopStagger = scatterGap > 0 ? 0 : STOP_STAGGER_MS;
      const minStop =
        col === 0 ? delay + SPIN_WINDUP_MS + LINEAR_MS : prevStop + stopStagger + waysGap + scatterGap;
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

  async playRound(round: SpinRound) {
    this.clearWins();
    this.badges.forEach((badge) => {
      badge.visible = false;
      badge.text = "";
    });
    const highlights = round.totalWin > 0 ? round.highlights : [];
    await this.spinTo(round.raw, round.waysGaps, round.scatterGaps, highlights);
    if (highlights.length) {
      this.dimNonWinners(highlights, COLS - 1);
      await this.playWinSheen(highlights);
      await wait(round.totalWin >= round.bet * 15 ? 900 : 380);
    }
  }

  async spinTo(
    raw: string[][],
    waysGaps: number[] = [],
    scatterGaps: number[] = [],
    highlights: Array<{ reel: number; row: number }> = [],
  ) {
    if (this.spinning) return;
    this.spinning = true;
    this.teaseOverlay.clear();
    this.scatterOverlay.clear();
    this.teaseOverlay.alpha = 1;
    const plans = this.planSpin(waysGaps, scatterGaps);
    const now = performance.now();
    this.jobs = [];
    const rng = spinRng();

    for (let col = 0; col < COLS; col += 1) {
      const rows = getReelRows(col);
      const finals = raw[col];
      const plan = plans[col];
      const fillers = pickStripItems(rng, col, plan.fillers);
      const strip = this.reels[col];
      const blur = this.blurs[col];
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
      const landed = raw.map((c) => c.slice());
      this.drawScatterTease(landed, col);
      if (highlights.length) {
        this.dimNonWinners(highlights, col);
        return;
      }
      const sym = getWaysTeaseSymbol(landed, col);
      this.drawTease(landed, sym, col);
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

  private playWinSheen(positions: Array<{ reel: number; row: number }>) {
    this.clearSheens();
    const pad = CELL * 0.06;
    const inner = CELL - pad * 2;
    const jobs = positions
      .map((pos) => {
        const cell = this.cells[pos.reel]?.[pos.row];
        if (!cell) return null;
        const wrap = new Container();
        wrap.label = "sheen";
        wrap.eventMode = "none";
        const mask = new Graphics();
        mask.roundRect(pad, pad, inner, inner, 10).fill(0xffffff);
        const shine = new Graphics();
        const len = CELL * 2.35;
        shine.rect(-len / 2, -14, len, 28).fill({ color: 0xfff4dc, alpha: 0.16 });
        shine.rect(-len / 2, -7, len, 14).fill({ color: 0xfffaf2, alpha: 0.34 });
        shine.rect(-len / 2, -2.2, len, 4.4).fill({ color: 0xffffff, alpha: 0.7 });
        shine.rotation = -Math.PI / 4;
        shine.blendMode = "add";
        wrap.addChild(mask, shine);
        wrap.mask = mask;
        cell.addChild(wrap);
        return {
          shine,
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
          const u = easeInOutQuad(Math.min(Math.max((elapsed - job.delay) / WIN_SHEEN_MS, 0), 1));
          job.shine.x = job.fromX + (job.toX - job.fromX) * u;
          job.shine.y = job.fromY + (job.toY - job.fromY) * u;
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
    this.cells.forEach((col) => {
      col.forEach((cell) => {
        cell.children
          .filter((child) => child.label === "sheen")
          .forEach((child) => child.destroy());
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
    const w = COLS * CELL + (COLS + 1) * GAP;
    const h = MAX_ROWS * CELL + 2 * GAP;
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
  return {
    width: COLS * CELL + (COLS + 1) * GAP,
    height: MAX_ROWS * CELL + 2 * GAP,
  };
}
