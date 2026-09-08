import { spawn } from "node:child_process";
import { once } from "node:events";
import { writeFile } from "node:fs/promises";

const chromePath = process.env.CHROME_PATH || "/usr/local/bin/google-chrome";
const port = 9335;
const base = "http://127.0.0.1:4173/";

const chrome = spawn(
  chromePath,
  [
    `--remote-debugging-port=${port}`,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-size=1280,900",
    "--user-data-dir=/tmp/sunset-stereo-chrome",
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

const title = await send(5, "Runtime.evaluate", {
  expression:
    "document.title + '|' + document.querySelector('h1')?.textContent + '|' + document.querySelectorAll('canvas').length + '|' + document.getElementById('balanceValue')?.textContent",
  returnByValue: true,
});
const log = (...args) =>
  process.stdout.write(args.map((a) => (typeof a === "string" ? a : JSON.stringify(a))).join(" ") + "\n");
log("boot", title.result.value);

const click = async (id, selector) => {
  await send(id, "Runtime.evaluate", {
    expression: `document.querySelector(${JSON.stringify(selector)}).click()`,
  });
};

const readHud = async (id) => {
  const res = await send(id, "Runtime.evaluate", {
    expression: `JSON.stringify({
      balance: document.getElementById('balanceValue').textContent,
      win: document.getElementById('winValue').textContent,
      bet: document.getElementById('betValue').textContent,
      busy: document.getElementById('spinBtn').disabled,
      mix: document.getElementById('mixValue').textContent
    })`,
    returnByValue: true,
  });
  return JSON.parse(res.result.value);
};

await click(20, "#spinBtn");
const spinStarted = Date.now();
let lastHud;
for (let i = 0; i < 90; i += 1) {
  await new Promise((r) => setTimeout(r, 400));
  lastHud = await readHud(30 + i);
  if (!lastHud.busy) {
    log("after spin", lastHud, `ms=${Date.now() - spinStarted}`);
    break;
  }
}
if (lastHud?.busy) throw new Error(`spin still busy after ${Date.now() - spinStarted}ms`);

await click(60, "#betDown");
await click(61, "#betDown");
log("after bet-", await readHud(63));

const hasBonus = await send(64, "Runtime.evaluate", {
  expression: "Boolean(document.getElementById('bonusBtn'))",
  returnByValue: true,
});
log("bonusBtn", hasBonus.result.value);
if (hasBonus.result.value) throw new Error("bonus buy control must not exist");

await click(66, "#spinBtn");
const spin2Started = Date.now();
let spin2Hud;
for (let i = 0; i < 90; i += 1) {
  await new Promise((r) => setTimeout(r, 400));
  spin2Hud = await readHud(80 + i);
  if (!spin2Hud.busy) break;
}
log("after spin2", spin2Hud, `ms=${Date.now() - spin2Started}`);
if (spin2Hud?.busy) throw new Error("second spin still busy");
const banner = await send(89, "Runtime.evaluate", {
  expression: "document.querySelector('.banner')?.textContent || ''",
  returnByValue: true,
});
log("banner", banner.result.value);

const shot = await send(90, "Page.captureScreenshot", { format: "png" });
await writeFile("/tmp/sunset-stereo-desktop.png", Buffer.from(shot.data, "base64"));

await send(91, "Emulation.setDeviceMetricsOverride", {
  width: 390,
  height: 844,
  deviceScaleFactor: 2,
  mobile: true,
});
await new Promise((r) => setTimeout(r, 300));
const mobile = await send(92, "Page.captureScreenshot", { format: "png" });
await writeFile("/tmp/sunset-stereo-mobile.png", Buffer.from(mobile.data, "base64"));
log("mobile", await readHud(93));

chrome.kill();
process.exit(0);
