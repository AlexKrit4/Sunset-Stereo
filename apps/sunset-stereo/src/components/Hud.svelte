<script lang="ts">
  import { BUY_SCATTER } from "../math/config.js";
  import { moneyHud, labels, ui } from "../lib/ui.svelte";
  import { toggleMusicMute } from "../lib/music";

  let {
    onSpin,
    onBet,
  }: {
    onSpin: () => void;
    onBet: (delta: number) => void;
  } = $props();

  const locked = $derived(ui.busy || !ui.ready);
  const showBuy = $derived(!ui.replay && !ui.disableBuyFeature);
  const showAutoplay = $derived(!ui.replay && !ui.disableAutoplay);
  const spinCost = $derived(Math.round(ui.betMicro * (ui.scatterBuyOn ? BUY_SCATTER.cost : 1)));
  const stakeLabel = $derived(ui.scatterBuyOn ? BUY_SCATTER.label : labels.stake());

  function toggleTray() {
    ui.trayOpen = !ui.trayOpen;
    if (ui.trayOpen) ui.buyMenuOpen = false;
  }

  function toggleBuy() {
    ui.buyMenuOpen = !ui.buyMenuOpen;
    ui.trayOpen = false;
    ui.buyConfirm = "";
  }

  function toggleAutoplay() {
    if (!showAutoplay || !ui.ready) return;
    ui.autoplayOn = !ui.autoplayOn;
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

  <div class="stat win">
    <span>{labels.win()}</span>
    <strong id="winValue">{moneyHud(ui.winMicro)}</strong>
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

  <button
    id="spinBtn"
    class="spin"
    type="button"
    disabled={locked}
    aria-label={ui.replay && ui.winMicro ? "Play again" : labels.spin()}
    onclick={onSpin}
  >
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <path
        d="M20 18a20 20 0 0 1 28 4l2-8 4 14-14-2 6-4a14 14 0 1 0 4 16"
        fill="none"
        stroke="currentColor"
        stroke-width="5"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <path
        d="M44 46a20 20 0 0 1-28-4l-2 8-4-14 14 2-6 4a14 14 0 1 0-4-16"
        fill="none"
        stroke="currentColor"
        stroke-width="5"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </button>

  <div class="side">
    {#if showAutoplay}
      <button
        id="autoplayBtn"
        class="circle"
        class:on={ui.autoplayOn}
        type="button"
        disabled={!ui.ready}
        aria-label="Autoplay"
        aria-pressed={ui.autoplayOn}
        onclick={toggleAutoplay}
      >
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path
            d="M10 10a8 8 0 0 1 12 2l1-4 2 7-7-1 3-2a5 5 0 1 0 1 6"
            fill="none"
            stroke="currentColor"
            stroke-width="2.6"
            stroke-linecap="round"
          />
          <path
            d="M22 22a8 8 0 0 1-12-2l-1 4-2-7 7 1-3 2a5 5 0 1 0-1-6"
            fill="none"
            stroke="currentColor"
            stroke-width="2.6"
            stroke-linecap="round"
          />
        </svg>
      </button>
    {/if}
    {#if showBuy}
      <button
        id="bonusBtn"
        class="circle bolt"
        class:on={ui.buyMenuOpen}
        class:armed={ui.scatterBuyOn}
        type="button"
        disabled={locked && !ui.buyMenuOpen}
        aria-label={labels.buy()}
        aria-pressed={ui.buyMenuOpen || ui.scatterBuyOn}
        onclick={toggleBuy}
      >
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path d="M18 3 8 18h7l-2 11 12-16h-7z" fill="currentColor" />
        </svg>
      </button>
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
    margin-top: 18px;
    padding: 10px 14px 10px 16px;
    min-height: 72px;
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
  .spin {
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
    width: 46px;
    height: 46px;
  }
  .spin:disabled {
    opacity: 0.45;
    cursor: wait;
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
    width: 20px;
    height: 20px;
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
  }
</style>
