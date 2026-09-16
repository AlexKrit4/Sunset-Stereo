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
await new Promise((r) => setTimeout(r, 800));

let continued = false;
for (let i = 0; i < 90; i += 1) {
  const boot = await send(4, "Runtime.evaluate", {
    expression: `JSON.stringify({
      continue: Boolean(document.getElementById('bootContinueBtn')),
      ready: document.querySelector('[data-boot]')?.getAttribute('data-boot-ready') || '0',
      progress: document.getElementById('bootProgress')?.textContent || ''
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
if (!continued) throw new Error("boot continue never appeared");
await new Promise((r) => setTimeout(r, 600));

const title = await send(8, "Runtime.evaluate", {
  expression:
    "document.title + '|' + document.querySelector('h1')?.textContent + '|' + document.querySelectorAll('canvas').length + '|' + document.getElementById('balanceValue')?.textContent",
  returnByValue: true,
});
const log = (...args) =>
  process.stdout.write(args.map((a) => (typeof a === "string" ? a : JSON.stringify(a))).join(" ") + "\n");
log("boot", title.result.value);

function assertWinMeter(hud) {
  const won = !/0[.,]00\s*$/.test(hud.win || "");
  if (won && hud.winLit !== "1") throw new Error(`WIN plaque must light when there is a win: ${JSON.stringify(hud)}`);
  if (!won && hud.winLit === "1") throw new Error(`WIN plaque must stay dim at zero: ${JSON.stringify(hud)}`);
}

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
      winLit: document.querySelector('.stat.win')?.getAttribute('data-win-lit') || '0',
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
for (let i = 0; i < 180; i += 1) {
  await new Promise((r) => setTimeout(r, 400));
  lastHud = await readHud(30 + i);
  if (!lastHud.busy) {
    log("after spin", lastHud, `ms=${Date.now() - spinStarted}`);
    break;
  }
}
if (lastHud?.busy) throw new Error(`spin still busy after ${Date.now() - spinStarted}ms`);
assertWinMeter(lastHud);

await click(60, "#betDown");
await click(61, "#betDown");
log("after bet-", await readHud(63));

const hasBonus = await send(64, "Runtime.evaluate", {
  expression: "Boolean(document.getElementById('bonusBtn'))",
  returnByValue: true,
});
log("bonusBtn", hasBonus.result.value);
if (!hasBonus.result.value) throw new Error("bonus buy control must exist");

await click(65, "#bonusBtn");
await new Promise((r) => setTimeout(r, 200));
const menu = await send(66, "Runtime.evaluate", {
  expression: `JSON.stringify({
    bonus: document.getElementById('buyScatterBtn')?.textContent || '',
    bonusCard: document.getElementById('buyBonusCard')?.innerText || '',
    wildBonus: document.getElementById('buyWildBonusBtn')?.textContent || '',
    wildBonusCard: document.getElementById('buyWildBonusCard')?.innerText || '',
    scatter: document.getElementById('buyReel2Btn')?.textContent || '',
    scatterCard: document.getElementById('buyReel2Card')?.innerText || '',
    pressed: document.getElementById('buyReel2Btn')?.getAttribute('aria-pressed') || '',
    title: document.querySelector('[aria-label="Buy bonus"], [aria-label="Get bonus"]') ? true : false
  })`,
  returnByValue: true,
});
log("buy menu", menu.result.value);
const menuState = JSON.parse(menu.result.value);
if (!/sun on reel 2/i.test(menuState.scatterCard)) throw new Error("buy shop must list sun on reel 2");
if (!/activate/i.test(menuState.scatter)) throw new Error("reel-2 sun must use Activate");
if (menuState.pressed === "true") throw new Error("reel-2 sun must start off");
if (!/3 scatters/i.test(menuState.bonusCard)) throw new Error("buy shop must list 3 scatters");
if (!/buy|get/i.test(menuState.bonus)) throw new Error("3 scatters must use Buy");
if (!/4 scatters/i.test(menuState.wildBonusCard)) throw new Error("buy shop must list 4 scatters");
if (!/buy|get/i.test(menuState.wildBonus)) throw new Error("4 scatters must use Buy");

await click(641, "#buyReel2Btn");
await new Promise((r) => setTimeout(r, 200));
const confirmOpen = await send(6415, "Runtime.evaluate", {
  expression: `JSON.stringify({
    open: Boolean(document.getElementById('buyConfirmBtn')),
    pressed: document.getElementById('buyReel2Btn')?.getAttribute('aria-pressed') || '',
    text: document.querySelector('[aria-label="Confirm buy"]')?.innerText || ''
  })`,
  returnByValue: true,
});
log("scatter confirm", confirmOpen.result.value);
const confirmState = JSON.parse(confirmOpen.result.value);
if (!confirmState.open) throw new Error("extra bet must ask for confirm");
if (confirmState.pressed === "true") throw new Error("extra bet must wait for confirm");
if (!/1\.5|reel 2/i.test(confirmState.text)) throw new Error("confirm must describe the extra bet");

await click(6416, "#buyConfirmBtn");
await new Promise((r) => setTimeout(r, 200));
const scatterOn = await send(642, "Runtime.evaluate", {
  expression: `JSON.stringify({
    pressed: document.getElementById('buyReel2Btn')?.getAttribute('aria-pressed') || '',
    text: document.getElementById('buyReel2Btn')?.textContent || '',
    confirm: Boolean(document.getElementById('buyConfirmBtn')),
    stakeLabel: document.getElementById('stakeLabel')?.textContent || '',
    bet: document.getElementById('betValue')?.textContent || ''
  })`,
  returnByValue: true,
});
log("scatter activate", scatterOn.result.value);
const scatterOnState = JSON.parse(scatterOn.result.value);
if (scatterOnState.pressed !== "true" || !/^active$/i.test(scatterOnState.text.trim())) {
  throw new Error("reel-2 sun activate must stay on");
}
if (scatterOnState.confirm) throw new Error("confirm must close after extra bet is armed");
if (!/sun on reel 2/i.test(scatterOnState.stakeLabel)) {
  throw new Error("stake readout must show the extra bet");
}

await click(643, "#buyReel2Btn");
const scatterOff = await send(644, "Runtime.evaluate", {
  expression: `JSON.stringify({
    pressed: document.getElementById('buyReel2Btn')?.getAttribute('aria-pressed') || '',
    text: document.getElementById('buyReel2Btn')?.textContent || '',
    stakeLabel: document.getElementById('stakeLabel')?.textContent || ''
  })`,
  returnByValue: true,
});
log("scatter deactivate", scatterOff.result.value);
const scatterOffState = JSON.parse(scatterOff.result.value);
if (scatterOffState.pressed === "true") {
  throw new Error("reel-2 sun activate must turn off");
}
if (/sun on reel 2/i.test(scatterOffState.stakeLabel)) {
  throw new Error("stake readout must return to the base stake");
}

await click(668, "#buyWildBonusBtn");
await new Promise((r) => setTimeout(r, 200));
const wildConfirm = await send(669, "Runtime.evaluate", {
  expression: `JSON.stringify({
    open: Boolean(document.getElementById('buyConfirmBtn')),
    text: document.querySelector('[aria-label="Confirm buy"]')?.innerText || ''
  })`,
  returnByValue: true,
});
log("wild bonus confirm", wildConfirm.result.value);
const wildConfirmState = JSON.parse(wildConfirm.result.value);
if (!wildConfirmState.open) throw new Error("4 scatters must ask for confirm");
if (!/225|4 scatters|wild/i.test(wildConfirmState.text)) throw new Error("confirm must describe 4 scatters");
if (!/substitut|lock/i.test(wildConfirmState.text)) throw new Error("confirm must say the wild substitutes and stays locked");
await click(670, "#buyCancelBtn");
await new Promise((r) => setTimeout(r, 150));
const wildConfirmClosed = await send(6705, "Runtime.evaluate", {
  expression: "Boolean(document.getElementById('buyConfirmBtn'))",
  returnByValue: true,
});
if (wildConfirmClosed.result.value) throw new Error("4 scatters confirm cancel must close");

await click(67, "#buyScatterBtn");
await new Promise((r) => setTimeout(r, 200));
const bonusConfirm = await send(671, "Runtime.evaluate", {
  expression: `JSON.stringify({
    open: Boolean(document.getElementById('buyConfirmBtn')),
    text: document.querySelector('[aria-label="Confirm buy"]')?.innerText || ''
  })`,
  returnByValue: true,
});
log("bonus confirm", bonusConfirm.result.value);
const bonusConfirmState = JSON.parse(bonusConfirm.result.value);
if (!bonusConfirmState.open) throw new Error("3 scatters must ask for confirm");
if (!/95|3 scatters/i.test(bonusConfirmState.text)) throw new Error("confirm must describe 3 scatters");
await click(672, "#buyConfirmBtn");
const buyStarted = Date.now();
let buyHud;
let startedBonus = false;
for (let i = 0; i < 450; i += 1) {
  await new Promise((r) => setTimeout(r, 400));
  if (!startedBonus) {
    const startBtn = await send(200 + i, "Runtime.evaluate", {
      expression: "Boolean(document.getElementById('bonusStartBtn'))",
      returnByValue: true,
    });
    if (startBtn.result.value) {
      await click(400 + i, "#bonusStartBtn");
      startedBonus = true;
      log("clicked bonus start");
    }
  }
  buyHud = await readHud(100 + i);
  if (!buyHud.busy) {
    log("after buy", buyHud, `ms=${Date.now() - buyStarted}`);
    break;
  }
}
if (buyHud?.busy) throw new Error(`buy bonus still busy after ${Date.now() - buyStarted}ms`);
assertWinMeter(buyHud);

await click(66, "#spinBtn");
const spin2Started = Date.now();
let spin2Hud;
for (let i = 0; i < 180; i += 1) {
  await new Promise((r) => setTimeout(r, 400));
  spin2Hud = await readHud(80 + i);
  if (!spin2Hud.busy) break;
}
log("after spin2", spin2Hud, `ms=${Date.now() - spin2Started}`);
if (spin2Hud?.busy) throw new Error("second spin still busy");
assertWinMeter(spin2Hud);
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
