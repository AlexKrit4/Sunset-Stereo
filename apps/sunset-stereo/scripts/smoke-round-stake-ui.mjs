import { spawn } from "node:child_process";
import { once } from "node:events";

const chromePath = process.env.CHROME_PATH || "/usr/local/bin/google-chrome";
const port = 9336;
const base = process.env.SMOKE_BASE || "http://127.0.0.1:4173/";
const restoreUrl = `${base}?restore=true&amount=1000000&mode=base&event=0`;

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

const chrome = spawn(
  chromePath,
  [
    `--remote-debugging-port=${port}`,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-size=1280,900",
    "--user-data-dir=/tmp/sunset-stereo-chrome-restore",
    restoreUrl,
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
await send(3, "Page.navigate", { url: restoreUrl });

let continued = false;
for (let i = 0; i < 90; i += 1) {
  const boot = await send(4, "Runtime.evaluate", {
    expression: `JSON.stringify({
      continue: Boolean(document.getElementById('bootContinueBtn')),
      ready: document.querySelector('[data-boot]')?.getAttribute('data-boot-ready') || '0'
    })`,
    returnByValue: true,
  });
  const state = JSON.parse(boot.result.value);
  if (state.continue) {
    await send(5, "Runtime.evaluate", {
      expression: `document.getElementById('bootContinueBtn').click()`,
    });
    continued = true;
    break;
  }
  await new Promise((r) => setTimeout(r, 400));
}
assert(continued, "boot continue never appeared");

const readHud = async (id) => {
  const res = await send(id, "Runtime.evaluate", {
    expression: `JSON.stringify({
      bet: document.getElementById('betValue')?.textContent || '',
      win: document.getElementById('winValue')?.textContent || '',
      busy: document.getElementById('spinBtn')?.disabled || false
    })`,
    returnByValue: true,
  });
  return JSON.parse(res.result.value);
};

let hud;
for (let i = 0; i < 40; i += 1) {
  hud = await readHud(20 + i);
  if (hud.bet) break;
  await new Promise((r) => setTimeout(r, 200));
}

process.stdout.write(`restore hud ${JSON.stringify(hud)}\n`);
assert(hud?.bet, "HUD stake never appeared");
assert(!/100/.test(hud.bet), `restored stake must not show defaultBetLevel 100: ${hud.bet}`);
assert(/1[.,]00/.test(hud.bet), `restored stake must show the original Play amount of 1: ${hud.bet}`);

for (let i = 0; i < 90; i += 1) {
  await new Promise((r) => setTimeout(r, 400));
  hud = await readHud(80 + i);
  if (!hud.busy) break;
}
process.stdout.write(`settled hud ${JSON.stringify(hud)}\n`);
assert(!hud.busy, "restored round never settled");
assert(/0[.,]40/.test(hud.win), `0.40x of 1 must display as 0.40, not defaultBetLevel 100: ${hud.win}`);
assert(!/[1-9]40[.,]00/.test(hud.win), `win must not be counted on 100: ${hud.win}`);

ws.close();
chrome.kill();
console.log("smoke-round-stake-ui ok");
