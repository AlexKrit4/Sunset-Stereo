import { Assets, Container, Graphics, Texture, Text } from "pixi.js";
import type { RawSymbol } from "../game/typesBookEvent";
import vinylUrl from "../assets/symbols/vinyl.jpg";
import headphonesUrl from "../assets/symbols/headphones.jpg";
import cassetteUrl from "../assets/symbols/cassette.jpg";
import microphoneUrl from "../assets/symbols/microphone.jpg";
import ampUrl from "../assets/symbols/amp.jpg";
import speakerUrl from "../assets/symbols/speaker.jpg";
import noteUrl from "../assets/symbols/note.jpg";
import equalizerUrl from "../assets/symbols/equalizer.jpg";
import palmUrl from "../assets/symbols/palm.jpg";
import cocktailUrl from "../assets/symbols/cocktail.jpg";
import mixerUrl from "../assets/symbols/mixer.jpg";
import sunsetUrl from "../assets/symbols/sunset.jpg";

const ART: Partial<Record<string, Texture>> = {};

const ART_URLS: Record<string, string> = {
  H1: vinylUrl,
  H2: headphonesUrl,
  H3: cassetteUrl,
  H4: microphoneUrl,
  H5: ampUrl,
  L1: speakerUrl,
  L2: noteUrl,
  L3: equalizerUrl,
  L4: palmUrl,
  L5: cocktailUrl,
  W: mixerUrl,
  S: sunsetUrl,
};

export const SYMBOL_PAY_ART: Record<string, string> = {
  high1: vinylUrl,
  high2: headphonesUrl,
  high3: cassetteUrl,
  high4: microphoneUrl,
  high5: ampUrl,
  low1: speakerUrl,
  low2: noteUrl,
  low3: equalizerUrl,
  low4: palmUrl,
  low5: cocktailUrl,
  scatter: sunsetUrl,
};

export async function loadSymbolArt() {
  const entries = Object.entries(ART_URLS).filter(([key]) => !ART[key]);
  if (!entries.length) return;
  const loaded = await Promise.all(entries.map(([, url]) => Assets.load(url)));
  entries.forEach(([key], index) => {
    ART[key] = loaded[index] as Texture;
  });
}

const ALIAS: Record<string, string> = {
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
  wild: "W",
  scatter: "S",
};

const PALETTE: Record<string, { wood: number; ink: number; accent: number }> = {
  H1: { wood: 0x1a1410, ink: 0x0c0a08, accent: 0xb5522a },
  H2: { wood: 0x241c16, ink: 0x3a2a20, accent: 0xc9a06a },
  H3: { wood: 0x2a2218, ink: 0x4a3828, accent: 0xd8c4a0 },
  H4: { wood: 0x1e1614, ink: 0x5a3030, accent: 0xc07058 },
  H5: { wood: 0x201810, ink: 0x2a2418, accent: 0xc09050 },
  L1: { wood: 0x161410, ink: 0x2a2820, accent: 0x8a7a68 },
  L2: { wood: 0x1c1812, ink: 0x3a3020, accent: 0xd0a060 },
  L3: { wood: 0x141816, ink: 0x243028, accent: 0x6a8a70 },
  L4: { wood: 0x141810, ink: 0x243018, accent: 0x6a7a40 },
  L5: { wood: 0x1c1412, ink: 0x402820, accent: 0xc07850 },
  W: { wood: 0x2a2418, ink: 0x1a160e, accent: 0xd4b06a },
  S: { wood: 0x2a1c12, ink: 0xc45c28, accent: 0xf0c878 },
  xWays: { wood: 0x241810, ink: 0x3a2818, accent: 0xe8c070 },
  xNudge: { wood: 0x1a1610, ink: 0x2a2218, accent: 0xd8b070 },
};

function fillRound(g: Graphics, x: number, y: number, w: number, h: number, r: number, color: number, alpha = 1) {
  g.roundRect(x, y, w, h, r).fill({ color, alpha });
}

export function createSymbolView(symbol: RawSymbol, size: number): Container {
  const root = new Container();
  const g = new Graphics();
  const name = ALIAS[symbol.name] ?? symbol.name;
  const pad = size * 0.06;
  const inner = size - pad * 2;
  const cx = size / 2;
  const cy = size / 2 - 4;
  const colors = PALETTE[name] ?? PALETTE[symbol.name] ?? PALETTE.L1;
  const art = ART[name];

  if (art) {
    g.roundRect(pad, pad, inner, inner, 10).fill({ texture: art, textureSpace: "local" });
    g.roundRect(pad, pad, inner, inner, 10).stroke({ color: 0x000000, width: 1, alpha: 0.28 });
    root.addChild(g);
  } else {
  fillRound(g, pad, pad, inner, inner, 10, colors.wood);
  g.roundRect(pad, pad, inner, inner, 10).stroke({ color: 0x000000, width: 1, alpha: 0.45 });

  const s = size * 0.32;

  switch (name) {
    case "H1": {
      g.circle(cx, cy, s + 6).fill(colors.ink);
      g.circle(cx, cy, s + 2).stroke({ color: 0x3a342c, width: 2 });
      for (let i = 0; i < 5; i += 1) {
        g.circle(cx, cy, s - i * 3).stroke({ color: 0x2a2420, width: 1, alpha: 0.7 });
      }
      g.circle(cx, cy, 10).fill(colors.accent);
      g.circle(cx, cy, 3).fill(0x1a100c);
      break;
    }
    case "H2": {
      g.roundRect(cx - s - 10, cy - 6, 16, 22, 6).fill(colors.accent);
      g.roundRect(cx + s - 6, cy - 6, 16, 22, 6).fill(colors.accent);
      g.moveTo(cx - s + 2, cy - 8);
      g.quadraticCurveTo(cx, cy - s - 8, cx + s - 2, cy - 8);
      g.stroke({ color: colors.ink, width: 4 });
      break;
    }
    case "H3": {
      fillRound(g, cx - s - 8, cy - 12, s * 2 + 16, 28, 4, colors.accent);
      g.circle(cx - 10, cy + 2, 6).fill(colors.ink);
      g.circle(cx + 10, cy + 2, 6).fill(colors.ink);
      g.rect(cx - s - 2, cy - 16, 8, 5).fill(0x6a5040);
      g.rect(cx + s - 6, cy - 16, 8, 5).fill(0x6a5040);
      break;
    }
    case "H4": {
      g.circle(cx, cy - 8, 12).fill(colors.accent);
      g.circle(cx, cy - 8, 8).stroke({ color: colors.ink, width: 2 });
      g.roundRect(cx - 3, cy + 2, 6, 22, 2).fill(0xd8c8b0);
      g.roundRect(cx - 8, cy + 22, 16, 5, 2).fill(colors.ink);
      break;
    }
    case "L1": {
      g.circle(cx, cy, s + 4).fill(colors.ink);
      g.circle(cx, cy, s - 2).stroke({ color: colors.accent, width: 3 });
      g.circle(cx, cy, 6).fill(colors.accent);
      break;
    }
    case "L2": {
      g.ellipse(cx - 6, cy + 8, 10, 7).fill(colors.accent);
      g.rect(cx + 2, cy - 18, 3, 26).fill(colors.accent);
      g.moveTo(cx + 5, cy - 18);
      g.quadraticCurveTo(cx + 16, cy - 10, cx + 5, cy - 2);
      g.stroke({ color: colors.accent, width: 2 });
      break;
    }
    case "L3": {
      const bars = [10, 22, 14, 18];
      bars.forEach((h, i) => {
        const x = cx - 22 + i * 12;
        g.roundRect(x, cy + 12 - h, 8, h, 2).fill(i % 2 ? colors.accent : 0xd8c8b0);
      });
      break;
    }
    case "L4": {
      g.roundRect(cx - 3, cy - 2, 6, 24, 2).fill(0x6a5038);
      g.moveTo(cx, cy - 4);
      g.quadraticCurveTo(cx - 22, cy - 8, cx - 18, cy + 8);
      g.quadraticCurveTo(cx - 6, cy + 2, cx, cy - 4);
      g.fill(0x4a6a38);
      g.moveTo(cx, cy - 6);
      g.quadraticCurveTo(cx + 22, cy - 10, cx + 16, cy + 6);
      g.quadraticCurveTo(cx + 4, cy, cx, cy - 6);
      g.fill(0x5a7a40);
      break;
    }
    case "L5": {
      g.moveTo(cx - 14, cy - 6);
      g.lineTo(cx + 14, cy - 6);
      g.lineTo(cx + 2, cy + 16);
      g.lineTo(cx - 2, cy + 16);
      g.closePath();
      g.fill({ color: colors.accent, alpha: 0.85 });
      g.circle(cx + 8, cy + 2, 3).fill(0x6a8a40);
      g.rect(cx - 1, cy + 16, 2, 8).fill(0xd8c8b0);
      break;
    }
    case "H5": {
      g.roundRect(cx - 18, cy - 14, 36, 28, 3).fill(colors.ink);
      [0, 1, 2].forEach((i) => {
        g.roundRect(cx - 12 + i * 10, cy + 2, 6, 8 + i * 3, 1).fill(colors.accent);
      });
      break;
    }
    case "xWays": {
      g.roundRect(cx - 16, cy - 10, 18, 22, 4).fill(colors.accent);
      g.roundRect(cx - 2, cy - 14, 18, 22, 4).fill({ color: colors.accent, alpha: 0.7 });
      g.roundRect(cx - 2, cy - 14, 18, 22, 4).stroke({ color: 0xf0e0c0, width: 1 });
      break;
    }
    case "xNudge": {
      for (let i = 0; i < 3; i += 1) {
        const y = cy + 10 - i * 10;
        g.moveTo(cx, y - 8);
        g.lineTo(cx + 14, y + 4);
        g.lineTo(cx - 14, y + 4);
        g.closePath();
        g.fill({ color: colors.accent, alpha: 0.55 + i * 0.15 });
      }
      break;
    }
    case "W": {
      [-16, 0, 16].forEach((dx, i) => {
        g.roundRect(cx + dx - 4, cy - 16, 8, 32, 2).fill(0x3a342c);
        const h = 10 + i * 6;
        g.roundRect(cx + dx - 6, cy + 8 - h, 12, 6, 2).fill(colors.accent);
      });
      break;
    }
    case "S": {
      g.circle(cx, cy - 4, 16).fill(colors.accent);
      for (let i = 0; i < 8; i += 1) {
        const a = (i / 8) * Math.PI * 2;
        g.moveTo(cx + Math.cos(a) * 18, cy - 4 + Math.sin(a) * 18);
        g.lineTo(cx + Math.cos(a) * 24, cy - 4 + Math.sin(a) * 24);
      }
      g.stroke({ color: 0xf0c878, width: 2 });
      g.ellipse(cx, cy + 18, 28, 6).fill({ color: 0x6a3a28, alpha: 0.55 });
      break;
    }
    default:
      g.circle(cx, cy, 12).fill(colors.accent);
  }

  root.addChild(g);
  }

  if (name === "xWays" || name === "xNudge") {
    const tag = new Text({
      text: name === "xWays" ? "xW" : "xN",
      style: { fontSize: Math.max(11, size * 0.16), fill: 0xf8ecd8, fontWeight: "700", fontFamily: "Georgia, serif" },
    });
    tag.anchor.set(0.5);
    tag.x = cx;
    tag.y = size - pad * 2 - 8;
    root.addChild(tag);
  }

  if (symbol.multiplier && symbol.multiplier > 1) {
    const badge = new Graphics();
    badge.roundRect(size - 34, 8, 26, 16, 4).fill(0xf0d8a0);
    const label = new Text({
      text: `${symbol.multiplier}×`,
      style: { fontSize: 10, fill: 0x2a1a10, fontWeight: "700", fontFamily: "Georgia, serif" },
    });
    label.x = size - 31;
    label.y = 10;
    root.addChild(badge, label);
  }

  root.eventMode = "none";
  return root;
}

export function createPlaceholder(size: number, name = "L5"): Container {
  return createSymbolView({ name }, size);
}
