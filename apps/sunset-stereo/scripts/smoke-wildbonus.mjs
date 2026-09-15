import { spawn } from "node:child_process";
import { once } from "node:events";

const chromePath = process.env.CHROME_PATH || "/usr/local/bin/google-chrome";
const port = 9336;
const base = "http://127.0.0.1:4173/";

const chrome = spawn(
  chromePath,
  [
    `--remote-debugging-port=${port}`,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-size=1280,900",
    "--user-data-dir=/tmp/sunset-stereo-chrome-wild",
    base,
  ],
  { stdio: ["ignore", "pipe", "pipe"] },
);

let wsUrl = "";
chrome.stderr.on("data", (buf) => {
  const text = buf.toString();
  process.stderr.write(text);
  const match = text.match(/DevTools listening on (ws:\/\/[^\s]+)/);
  if (match) wsUrl = match[1];
});
chrome.stdout.on("data", (buf) => process.stdout.write(buf));

await new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error("chrome start timeout")), 15000);
  const tick = setInterval(() => {
    if (wsUrl) {
      clearInterval(tick);
      clearTimeout(timer);
      resolve();
    }
  }, 50);
});

const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const pageTarget = targets.find((item) => item.type === "page") || targets[0];
if (!pageTarget?.webSocketDebuggerUrl) {
  throw new Error(`no page target: ${JSON.stringify(targets)}`);
}
const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

function send(id, method, params = {}) {
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    const onMessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id === id) {
        ws.removeEventListener("message", onMessage);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    };
    ws.addEventListener("message", onMessage);
  });
}

await once(ws, "open");
await send(1, "Page.enable");
await send(2, "Runtime.enable");
await send(3, "Page.navigate", { url: base });
await new Promise((r) => setTimeout(r, 1800));

const click = async (id, selector) => {
  await send(id, "Runtime.evaluate", {
    expression: `document.querySelector(${JSON.stringify(selector)}).click()`,
  });
};

const readState = async (id) => {
  const res = await send(id, "Runtime.evaluate", {
    expression: `JSON.stringify({
      busy: document.getElementById('spinBtn')?.disabled || false,
      win: document.getElementById('winValue')?.textContent || '',
      start: Boolean(document.getElementById('bonusStartBtn')),
      wildStamp: document.body.dataset.wildStamp || '',
      wildWin: document.body.dataset.wildWin || '',
      bonusDim: document.body.dataset.bonusDim || '',
      anim: document.body.dataset.symbolAnimation || '',
      winCount: document.body.dataset.symbolAnimationWinCount || '0',
      fs: document.getElementById('fsValue')?.textContent || ''
    })`,
    returnByValue: true,
  });
  return JSON.parse(res.result.value);
};

const log = (...args) =>
  process.stdout.write(args.map((a) => (typeof a === "string" ? a : JSON.stringify(a))).join(" ") + "\n");

await click(20, "#bonusBtn");
await new Promise((r) => setTimeout(r, 200));
await click(21, "#buyWildBonusBtn");
await new Promise((r) => setTimeout(r, 200));
await click(22, "#buyConfirmBtn");

const started = Date.now();
let sawStamp = false;
let sawWildWin = false;
let sawBonusDim = false;
let startedBonus = false;
let last;

for (let i = 0; i < 240; i += 1) {
  await new Promise((r) => setTimeout(r, 400));
  last = await readState(30 + i);
  if (!startedBonus && last.start) {
    await click(400 + i, "#bonusStartBtn");
    startedBonus = true;
    log("clicked bonus start");
  }
  if (last.wildStamp) sawStamp = true;
  if (last.wildWin === "1") sawWildWin = true;
  if (last.bonusDim === "1") sawBonusDim = true;
  if (sawStamp && sawWildWin && sawBonusDim) {
    log("wild extra play", last, `ms=${Date.now() - started}`);
    break;
  }
}

if (!sawStamp) throw new Error("4 scatters never stamped a Wild");
if (!sawWildWin) throw new Error("Wild never played a win animation");
if (!sawBonusDim) throw new Error("Wild line paid without hold-and-respin dim/lock");

log("ok", { sawStamp, sawWildWin, sawBonusDim, last });
chrome.kill();
process.exit(0);
