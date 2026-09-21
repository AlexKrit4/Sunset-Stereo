<script lang="ts">
  import { BUY_SCATTER } from "../math/config.js";
  import { AUTOPLAY_COUNTS, moneyHud, labels, startAutoplay, stopAutoplay, ui } from "../lib/ui.svelte";
  import { toggleMusicMute } from "../lib/music";

  let {
    onSpin,
    onBet,
  }: {
    onSpin: () => void;
    onBet: (delta: number) => void;
  } = $props();

  const locked = $derived(ui.busy || !ui.ready || ui.bootOpen);
  const spinLocked = $derived(locked && !ui.autoplayOn);
  const showBuy = $derived(!ui.replay && !ui.disableBuyFeature);
  const showAutoplay = $derived(!ui.replay && !ui.disableAutoplay);
  const spinCost = $derived(Math.round(ui.betMicro * (ui.scatterBuyOn ? BUY_SCATTER.cost : 1)));
  const stakeLabel = $derived(ui.scatterBuyOn ? BUY_SCATTER.label : labels.stake());
  const WIN_COUNT_MS = 500;
  let displayedWinMicro = $state(0);
  let displayedWinHold = 0;
  const winLit = $derived(ui.winMicro > 0 || ui.bigWinOpen);

  $effect(() => {
    if (ui.bigWinOpen) {
      displayedWinHold = ui.winMicro;
      displayedWinMicro = ui.winMicro;
      return;
    }
    if (ui.bigWinIntro) {
      return;
    }
    const target = ui.winMicro;
    if (target <= 0) {
      displayedWinHold = 0;
      displayedWinMicro = 0;
      return;
    }
    const from = displayedWinHold;
    const started = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const u = Math.min(1, (now - started) / WIN_COUNT_MS);
      const eased = 1 - (1 - u) ** 3;
      displayedWinHold = Math.round(from + (target - from) * eased);
      displayedWinMicro = displayedWinHold;
      if (u < 1) {
        frame = requestAnimationFrame(tick);
        return;
      }
      displayedWinHold = target;
      displayedWinMicro = target;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  });

  function toggleTray() {
    ui.trayOpen = !ui.trayOpen;
    if (ui.trayOpen) {
      ui.buyMenuOpen = false;
      ui.autoplayMenuOpen = false;
    }
  }

  function toggleBuy() {
    ui.buyMenuOpen = !ui.buyMenuOpen;
    ui.trayOpen = false;
    ui.buyConfirm = "";
    ui.autoplayMenuOpen = false;
  }

  function toggleAutoplayMenu() {
    if (!showAutoplay || !ui.ready) return;
    if (ui.autoplayOn) {
      stopAutoplay();
      return;
    }
    ui.autoplayMenuOpen = !ui.autoplayMenuOpen;
    if (ui.autoplayMenuOpen) {
      ui.buyMenuOpen = false;
      ui.trayOpen = false;
      if (!AUTOPLAY_COUNTS.includes(ui.autoplayPick)) ui.autoplayPick = 10;
    }
  }

  function confirmAutoplay() {
    if (!ui.autoplayPick) return;
    startAutoplay(ui.autoplayPick);
  }

  function onSpinClick() {
    if (ui.autoplayOn) {
      stopAutoplay();
      return;
    }
    ui.autoplayMenuOpen = false;
    onSpin();
  }

  function toggleFastPlay() {
    if (!ui.ready || ui.bootOpen) return;
    ui.fastPlay = !ui.fastPlay;
  }
</script>

<div class="dock">
  {#if ui.trayOpen}
    <div class="tray" role="menu">
      <button type="button" onclick={() => (ui.rulesOpen = true, ui.trayOpen = false)}>Rules</button>
      <button
        id="musicBtn"
        type="button"
        aria-pressed={!ui.musicMuted}
        onclick={() => toggleMusicMute()}
      >
        {ui.musicMuted ? "Music off" : "Music"}
      </button>
    </div>
  {/if}

  <button id="menuBtn" class="icon menu" type="button" aria-label="Menu" aria-pressed={ui.trayOpen} onclick={toggleTray}>
    <span></span><span></span><span></span>
  </button>

  {#if !ui.replay}
    <div class="stat">
      <span>{labels.credit()}</span>
      <strong id="balanceValue">{moneyHud(ui.balanceMicro)}</strong>
    </div>
  {/if}

  <div class="stat win" class:lit={winLit} data-win-lit={winLit ? "1" : "0"}>
    <span>{labels.win()}</span>
    <strong id="winValue">{moneyHud(displayedWinMicro)}</strong>
  </div>

  {#if ui.fsTotal > 0}
    <div class="stat extra">
      <span>Extra</span>
      <strong id="fsValue">{ui.fsCurrent}/{ui.fsTotal}</strong>
    </div>
  {/if}

  <div class="spacer"></div>

  {#if !ui.replay}
    <div class="stake" class:extra={ui.scatterBuyOn}>
      <div class="stake-read">
        <span id="stakeLabel">{stakeLabel}</span>
        <strong id="betValue">{moneyHud(spinCost)}</strong>
      </div>
      <div class="chevrons">
        <button id="betUp" type="button" disabled={locked} aria-label="Increase stake" onclick={() => onBet(1)}>
          ▲
        </button>
        <button id="betDown" type="button" disabled={locked} aria-label="Decrease stake" onclick={() => onBet(-1)}>
          ▼
        </button>
      </div>
    </div>
  {/if}

  <div class="play">
    {#if showBuy}
      <button
        id="bonusBtn"
        class="provider"
        class:on={ui.buyMenuOpen}
        class:armed={ui.scatterBuyOn}
        type="button"
        disabled={locked && !ui.buyMenuOpen}
        aria-label={labels.buy()}
        aria-pressed={ui.buyMenuOpen || ui.scatterBuyOn}
        onclick={toggleBuy}
      >
        <img src="./big-fathers-mark.png" alt="" />
      </button>
    {/if}

    <button
      id="spinBtn"
      class="spin"
      class:auto={ui.autoplayOn}
      type="button"
      disabled={spinLocked}
      aria-label={ui.autoplayOn ? "Stop autoplay" : ui.replay && ui.winMicro ? "Play again" : labels.spin()}
      onclick={onSpinClick}
    >
      {#if ui.autoplayOn}
        <span id="spinRemain" class="remain" class:tight={ui.autoplayLeft >= 100}>{ui.autoplayLeft}</span>
        <span class="stopx" aria-hidden="true">×</span>
      {:else}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M4.2 11.2A7.8 7.8 0 0 1 12 4.2c2.8 0 5.2 1.4 6.6 3.6"
            fill="none"
            stroke="currentColor"
            stroke-width="2.4"
            stroke-linecap="round"
          />
          <path d="M19.4 3.2v5.2h-5.2" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
          <path
            d="M19.8 12.8A7.8 7.8 0 0 1 12 19.8c-2.8 0-5.2-1.4-6.6-3.6"
            fill="none"
            stroke="currentColor"
            stroke-width="2.4"
            stroke-linecap="round"
          />
          <path d="M4.6 20.8v-5.2h5.2" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      {/if}
    </button>

    <div class="side">
      {#if showAutoplay}
        <button
          id="autoplayBtn"
          class="circle"
          class:on={ui.autoplayOn || ui.autoplayMenuOpen}
          type="button"
          disabled={!ui.ready}
          aria-label={labels.autoplay()}
          aria-pressed={ui.autoplayOn || ui.autoplayMenuOpen}
          onclick={toggleAutoplayMenu}
        >
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <path d="M11 7.2v17.6L25.2 16 11 7.2z" fill="currentColor" />
          </svg>
        </button>
      {/if}
      {#if !ui.replay}
        <button
          id="turboBtn"
          class="circle bolt"
          class:on={ui.fastPlay}
          type="button"
          disabled={!ui.ready || ui.bootOpen}
          aria-label={labels.turbo()}
          aria-pressed={ui.fastPlay}
          onclick={toggleFastPlay}
        >
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <path d="M18 3 8 18h7l-2 11 12-16h-7z" fill="currentColor" />
          </svg>
        </button>
      {/if}
    </div>

    {#if ui.autoplayMenuOpen}
      <div class="autoplay" id="autoplayPanel" role="dialog" aria-label={labels.autoplay()}>
        <p class="auto-kicker">{labels.autoplay()}</p>
        <p class="auto-title">{labels.rounds()}</p>
        <div class="counts">
          {#each AUTOPLAY_COUNTS as count}
            <button
              id={`autoplayCount-${count}`}
              class="count"
              class:on={ui.autoplayPick === count}
              type="button"
              onclick={() => (ui.autoplayPick = count)}
            >
              {count}
            </button>
          {/each}
        </div>
        <button
          id="autoplayConfirmBtn"
          class="go"
          type="button"
          disabled={!ui.autoplayPick}
          onclick={confirmAutoplay}
        >
          {labels.spin()}
        </button>
      </div>
    {/if}
  </div>
</div>

<style>
  .dock {
    position: relative;
    z-index: 50;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 14px 16px;
    flex: 0 0 auto;
    margin-top: 10px;
    padding: 10px 14px 10px 16px;
    min-height: 64px;
    border-radius: 14px;
    background: #1b140f;
    color: #f4efe6;
    font-family: ui-sans-serif, system-ui, sans-serif;
    box-shadow: 0 10px 28px rgba(8, 2, 16, 0.45);
  }
  .tray {
    position: absolute;
    left: 12px;
    bottom: calc(100% + 8px);
    display: grid;
    gap: 6px;
    padding: 8px;
    border-radius: 12px;
    background: #140e0a;
    box-shadow: 0 10px 24px rgba(8, 2, 16, 0.45);
  }
  .tray button {
    min-width: 120px;
    min-height: 40px;
    border: 0;
    border-radius: 8px;
    background: #2a2118;
    color: #f4efe6;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 12px;
    cursor: pointer;
  }
  .menu {
    display: grid;
    gap: 5px;
    width: 28px;
    padding: 4px 0;
    border: 0;
    background: transparent;
    cursor: pointer;
  }
  .menu span {
    display: block;
    height: 3px;
    border-radius: 2px;
    background: #f4efe6;
  }
  .stat span,
  .stake-read span {
    display: block;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #cbbba8;
  }
  .stat strong,
  .stake-read strong {
    display: block;
    font-size: 22px;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
  }
  .win strong {
    color: #8a7d70;
  }
  .win.lit strong {
    color: #3ec8f0;
  }
  .extra strong {
    color: #ffb070;
  }
  .spacer {
    flex: 1;
    min-width: 8px;
  }
  .stake {
    display: flex;
    align-items: stretch;
    min-width: 128px;
    border-radius: 10px;
    background: #0d0b09;
    overflow: hidden;
  }
  .stake.extra {
    min-width: 168px;
  }
  .stake-read {
    padding: 8px 12px 6px;
  }
  .stake-read strong {
    padding-bottom: 4px;
    border-bottom: 2px solid #f4efe6;
  }
  .stake.extra .stake-read span,
  .stake.extra .stake-read strong {
    color: #3ec8f0;
  }
  .stake.extra .stake-read strong {
    border-bottom-color: #3ec8f0;
  }
  .chevrons {
    display: grid;
    width: 36px;
  }
  .chevrons button {
    border: 0;
    background: transparent;
    color: #f4efe6;
    font-size: 11px;
    line-height: 1;
    cursor: pointer;
  }
  .chevrons button:disabled {
    opacity: 0.35;
    cursor: wait;
  }
  .play {
    position: relative;
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 0 0 auto;
  }
  .provider {
    width: 52px;
    height: 52px;
    display: grid;
    place-items: center;
    padding: 0;
    border: 3px solid #16110c;
    border-radius: 14px;
    background: #ff7a18;
    cursor: pointer;
    box-shadow: 0 3px 0 #16110c;
    flex: 0 0 52px;
  }
  .provider img {
    width: 78%;
    height: 78%;
    object-fit: contain;
    pointer-events: none;
  }
  .provider.on,
  .provider.armed {
    box-shadow: 0 0 0 3px #ffd080, 0 3px 0 #16110c;
  }
  .provider:disabled {
    opacity: 0.45;
    cursor: wait;
  }
  .spin {
    position: relative;
    width: 86px;
    height: 86px;
    margin: -18px 0;
    border: 0;
    border-radius: 50%;
    background: #f4efe6;
    color: #111;
    cursor: pointer;
    box-shadow: 0 4px 0 #0d0b09;
    flex: 0 0 86px;
  }
  .spin svg {
    width: 42px;
    height: 42px;
  }
  .spin .remain,
  .spin .stopx {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    pointer-events: none;
  }
  .spin .remain {
    font-size: 26px;
    letter-spacing: -0.03em;
  }
  .spin .remain.tight {
    font-size: 18px;
  }
  .spin .stopx {
    font-size: 46px;
    line-height: 1;
    opacity: 0;
  }
  .spin.auto:hover .remain,
  .spin.auto:focus-visible .remain {
    opacity: 0;
  }
  .spin.auto:hover .stopx,
  .spin.auto:focus-visible .stopx {
    opacity: 1;
  }
  .spin:disabled {
    opacity: 0.45;
    cursor: wait;
  }
  .spin.auto:disabled {
    opacity: 1;
    cursor: pointer;
  }
  .side {
    display: grid;
    gap: 8px;
  }
  .circle {
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    border: 0;
    border-radius: 50%;
    background: #f4efe6;
    color: #111;
    cursor: pointer;
  }
  .circle svg {
    width: 18px;
    height: 18px;
  }
  .circle.on,
  .circle.armed {
    background: #ffd080;
    box-shadow: 0 0 12px rgba(255, 160, 40, 0.55);
  }
  .circle:disabled {
    opacity: 0.45;
    cursor: wait;
  }
  .autoplay {
    position: absolute;
    right: 0;
    bottom: calc(100% + 12px);
    z-index: 60;
    width: min(280px, 78vw);
    padding: 12px 12px 12px;
    border-radius: 16px;
    background: #140e0a;
    color: #f4efe6;
    box-shadow: 0 12px 28px rgba(8, 2, 16, 0.45);
  }
  .auto-kicker,
  .auto-title {
    margin: 0;
    text-align: center;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }
  .auto-kicker {
    font-size: 10px;
    color: #cbbba8;
  }
  .auto-title {
    margin: 4px 0 10px;
    font-size: 12px;
  }
  .counts {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }
  .count,
  .autoplay .go {
    min-height: 36px;
    border: 0;
    border-radius: 10px;
    cursor: pointer;
    font-weight: 700;
  }
  .count {
    background: #2a2118;
    color: #f4efe6;
  }
  .count.on {
    background: #8b5cf6;
    color: #fff;
  }
  .autoplay .go {
    width: 100%;
    margin-top: 10px;
    background: #f4efe6;
    color: #111;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .autoplay .go:disabled {
    opacity: 0.4;
    cursor: wait;
  }
  @media (max-width: 720px) {
    .dock {
      gap: 10px;
    }
    .stat strong,
    .stake-read strong {
      font-size: 18px;
    }
    .spin {
      width: 72px;
      height: 72px;
      margin: -12px 0;
      flex-basis: 72px;
    }
    .provider {
      width: 44px;
      height: 44px;
      flex-basis: 44px;
    }
  }
</style>
