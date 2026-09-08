import { Application, BlurFilter, Container, Graphics } from "pixi.js";
import type { BookEventReveal, BookEventWinInfo, Position, RawSymbol } from "../game/typesBookEvent";
import { createSymbolView } from "./symbols";
import { wait } from "../game/eventEmitter";
import { REELS } from "../math/reels.js";

export const COLS = 5;
export const ROWS = 3;
export const CELL = 118;
export const GAP = 6;

const START_STAGGER_MS = 100;
const STOP_STAGGER_MS = 300;
const LINEAR_MS = 900;
const DECEL_MS = 120;
const LINEAR_FRAC = 0.86;
const BASE_FILLERS = 18;
const ANTICIPATION_MS = 480;
const FILLER_NAMES = ["L4", "L2", "H3", "L1", "H1", "L5", "H2", "L3"];

function asSymbol(name: string): RawSymbol {
  return { name, wild: name === "W", scatter: name === "S" };
}

function visibleFromReveal(column: RawSymbol[]): RawSymbol[] {
  return [column[1], column[2], column[3]].map((symbol) => ({
    name: symbol.name,
    wild: symbol.wild,
    scatter: symbol.scatter,
    multiplier: symbol.multiplier,
  }));
}

function fillersFromStrip(col: number, count: number, gameType: "basegame" | "freegame"): RawSymbol[] {
  const strips = gameType === "freegame" ? REELS.FR0 : REELS.BR0;
  const strip = strips?.[col] ?? FILLER_NAMES;
  const start = Math.floor(Math.random() * strip.length);
  const out: RawSymbol[] = [];
  for (let i = 0; i < count; i += 1) {
    out.push(asSymbol(strip[(start + i) % strip.length]));
  }
  return out;
}

type SpinJob = {
  col: number;
  strip: Container;
  blur: BlurFilter;
  startAt: number;
  startOffset: number;
  velocity: number;
  tDecel: number;
  decelMs: number;
  finals: RawSymbol[];
  done: boolean;
};

export class BoardController {
  app: Application;
  root = new Container();
  reels: Container[] = [];
  private blurs: BlurFilter[] = [];
  private visible: RawSymbol[][] = [];
  private spinning = false;
  private jobs: SpinJob[] = [];
  private boundTick = () => this.tickSpins();

  constructor(app: Application) {
    this.app = app;
  }

  mount() {
    const frame = new Graphics();
    const w = COLS * CELL + (COLS + 1) * GAP;
    const h = ROWS * CELL + (ROWS + 1) * GAP;
    frame.roundRect(0, 0, w, h, 8).fill(0x1a140f);
    frame.roundRect(0, 0, w, h, 8).stroke({ color: 0x8a6a40, width: 2 });
    this.root.addChild(frame);

    const window = new Container();
    window.x = GAP;
    window.y = GAP;
    const mask = new Graphics();
    mask.rect(0, 0, COLS * CELL, ROWS * CELL).fill(0xffffff);
    window.addChild(mask);
    window.mask = mask;

    for (let col = 0; col < COLS; col += 1) {
      const reel = new Container();
      reel.x = col * CELL;
      const blur = new BlurFilter({ strength: 0, quality: 3 });
      blur.strengthX = 0;
      blur.strengthY = 0;
      reel.filters = [];
      const seed = FILLER_NAMES.slice(col, col + ROWS).map(asSymbol);
      this.paintStrip(reel, seed);
      window.addChild(reel);
      this.reels.push(reel);
      this.blurs.push(blur);
      this.visible.push(seed);
    }

    this.root.addChild(window);
    this.app.stage.addChild(this.root);
  }

  private paintStrip(strip: Container, symbols: RawSymbol[]) {
    strip.removeChildren();
    symbols.forEach((symbol, index) => {
      const view = createSymbolView(symbol, CELL);
      view.y = index * CELL;
      strip.addChild(view);
    });
    strip.y = 0;
  }

  private planSpin(anticipation: number[]) {
    const s0 = (ROWS + BASE_FILLERS) * CELL;
    const velocity = (LINEAR_FRAC * s0) / LINEAR_MS;
    const decelDistance = Math.max(0, s0 - velocity * LINEAR_MS);
    const plans: Array<{ delay: number; tDecel: number; fillers: number; velocity: number }> = [];
    let prevStop = 0;

    for (let col = 0; col < COLS; col += 1) {
      const delay = col * START_STAGGER_MS;
      const extra = anticipation[col] > 0 ? ANTICIPATION_MS : 0;
      const minStop =
        col === 0 ? delay + LINEAR_MS + DECEL_MS + extra : prevStop + STOP_STAGGER_MS + extra;
      let tDecel = Math.max(80, minStop - delay - DECEL_MS);
      let needed = Math.ceil((velocity * tDecel + decelDistance) / CELL) - ROWS;
      needed = Math.max(10, needed);
      const startOffset = (ROWS + needed) * CELL;
      tDecel = Math.max(tDecel, (startOffset - decelDistance) / velocity);
      prevStop = delay + tDecel + DECEL_MS;
      plans.push({ delay, tDecel, fillers: needed, velocity });
    }
    return plans;
  }

  async spinTo(event: BookEventReveal) {
    if (this.spinning) return;
    this.spinning = true;
    this.clearWins();

    const plans = this.planSpin(event.anticipation ?? []);
    const now = performance.now();
    this.jobs = [];

    for (let col = 0; col < COLS; col += 1) {
      const finals = visibleFromReveal(event.board[col]);
      const plan = plans[col];
      const strip = this.reels[col];
      const blur = this.blurs[col];
      const symbols = [...finals, ...fillersFromStrip(col, plan.fillers, event.gameType), ...this.visible[col]];
      this.paintStrip(strip, symbols);
      const startOffset = (ROWS + plan.fillers) * CELL;
      strip.y = -startOffset;
      blur.strengthX = 0;
      blur.strengthY = 10;
      strip.filters = [blur];
      this.jobs.push({
        col,
        strip,
        blur,
        startAt: now + plan.delay,
        startOffset,
        velocity: plan.velocity,
        tDecel: plan.tDecel,
        decelMs: DECEL_MS,
        finals,
        done: false,
      });
    }

    await new Promise<void>((resolve) => {
      const finishIfIdle = () => {
        if (this.jobs.every((job) => job.done)) {
          this.app.ticker.remove(this.boundTick);
          this.spinning = false;
          resolve();
        }
      };
      this.boundTick = () => {
        this.tickSpins();
        finishIfIdle();
      };
      this.app.ticker.add(this.boundTick);
    });
  }

  private tickSpins() {
    const now = performance.now();
    for (const job of this.jobs) {
      if (job.done || now < job.startAt) continue;
      const elapsed = now - job.startAt;
      let offset: number;
      if (elapsed < job.tDecel) {
        offset = Math.max(0, job.startOffset - job.velocity * elapsed);
        job.blur.strengthY = 10;
      } else {
        const u = Math.min((elapsed - job.tDecel) / job.decelMs, 1);
        const offAtDecel = Math.max(0, job.startOffset - job.velocity * job.tDecel);
        offset = offAtDecel * (1 - u);
        job.blur.strengthY = 10 * (1 - u);
        if (u >= 1) {
          this.landReel(job);
          continue;
        }
      }
      job.strip.y = -offset;
    }
  }

  private landReel(job: SpinJob) {
    job.done = true;
    job.blur.strengthY = 0;
    job.strip.filters = [];
    this.paintStrip(job.strip, job.finals);
    this.visible[job.col] = job.finals;
  }

  highlight(positions: Position[]) {
    this.clearWins();
    const overlay = new Graphics();
    overlay.label = "win";
    positions.forEach((pos) => {
      const x = GAP + pos.reel * CELL + 3;
      const y = GAP + (pos.row - 1) * CELL + 3;
      overlay.roundRect(x, y, CELL - 6, CELL - 6, 8).stroke({ color: 0xe8c878, width: 3 });
    });
    this.root.addChild(overlay);
  }

  markScatters(positions: Position[]) {
    const overlay = new Graphics();
    overlay.label = "scatter";
    positions.forEach((pos) => {
      const x = GAP + pos.reel * CELL + 6;
      const y = GAP + (pos.row - 1) * CELL + 6;
      overlay.roundRect(x, y, CELL - 12, CELL - 12, 8).stroke({ color: 0xc45c28, width: 2 });
    });
    this.root.addChild(overlay);
  }

  async showWins(wins: BookEventWinInfo["wins"]) {
    if (!wins?.length) return;
    for (const win of wins) {
      this.highlight(win.positions);
      await wait(420);
    }
  }

  async flashScatters(positions: Position[] = []) {
    if (positions.length) this.markScatters(positions);
    await wait(480);
    this.clearWins();
  }

  clearWins() {
    this.root.children
      .filter((child) => child.label === "win" || child.label === "scatter")
      .forEach((child) => child.destroy());
  }

  layout(viewWidth: number, viewHeight = 0) {
    const w = COLS * CELL + (COLS + 1) * GAP;
    const h = ROWS * CELL + (ROWS + 1) * GAP;
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
    height: ROWS * CELL + (ROWS + 1) * GAP,
  };
}
