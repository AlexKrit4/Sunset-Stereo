import { Application, BlurFilter, Container, Graphics } from "pixi.js";
import type { BookEventReveal, BookEventWinInfo, Position, RawSymbol } from "../game/typesBookEvent";
import { createSymbolView } from "./symbols";
import { wait } from "../game/eventEmitter";

export const COLS = 5;
export const ROWS = 3;
export const CELL = 118;
export const GAP = 6;

const FILLER = ["L4", "L2", "H3", "L1", "H1", "L5", "H2", "L3"];

export class BoardController {
  app: Application;
  root = new Container();
  reels: Container[] = [];
  cells: Container[][] = [];
  private blur = new BlurFilter({ strength: 0, quality: 2 });
  private spinning = false;

  constructor(app: Application) {
    this.app = app;
    this.blur.strengthX = 0;
    this.blur.strengthY = 0;
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
      const colCells: Container[] = [];
      for (let row = 0; row < ROWS; row += 1) {
        const cell = new Container();
        cell.y = row * CELL;
        cell.addChild(createSymbolView({ name: FILLER[(col + row) % FILLER.length] }, CELL));
        reel.addChild(cell);
        colCells.push(cell);
      }
      window.addChild(reel);
      this.reels.push(reel);
      this.cells.push(colCells);
    }

    this.root.addChild(window);
    this.app.stage.addChild(this.root);
  }

  private setCell(col: number, row: number, symbol: RawSymbol) {
    const cell = this.cells[col][row];
    cell.removeChildren();
    cell.addChild(createSymbolView(symbol, CELL));
  }

  async spinTo(event: BookEventReveal) {
    if (this.spinning) return;
    this.spinning = true;
    this.clearWins();

    for (let col = 0; col < COLS; col += 1) {
      this.reels[col].filters = [this.blur];
    }
    this.blur.strengthY = 8;

    const names = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "L5", "W", "S"];
    const timers: number[] = [];
    for (let col = 0; col < COLS; col += 1) {
      timers[col] = window.setInterval(() => {
        for (let row = 0; row < ROWS; row += 1) {
          const name = names[Math.floor(Math.random() * names.length)];
          this.setCell(col, row, { name, wild: name === "W", scatter: name === "S" });
        }
      }, 48);
    }

    for (let col = 0; col < COLS; col += 1) {
      const extra = event.anticipation?.[col] ? 180 : 0;
      await wait(240 + col * 95 + extra);
      window.clearInterval(timers[col]);
      const column = event.board[col];
      for (let row = 0; row < ROWS; row += 1) {
        this.setCell(col, row, column[row + 1]);
      }
      this.reels[col].filters = [];
    }

    this.blur.strengthY = 0;
    this.spinning = false;
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
