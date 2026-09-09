<script lang="ts">
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
</script>

<div class="bar">
  {#if !ui.replay}
    <div class="readout">
      <span>{labels.credit()}</span>
      <strong id="balanceValue">{moneyHud(ui.balanceMicro)}</strong>
    </div>
  {/if}
  <div class="readout">
    <span>{labels.paid()}</span>
    <strong id="winValue">{moneyHud(ui.winMicro)}</strong>
  </div>

  {#if ui.fsTotal > 0}
    <div class="readout extra">
      <span>Extra plays</span>
      <strong id="fsValue">{ui.fsCurrent}/{ui.fsTotal}</strong>
    </div>
  {/if}

  {#if !ui.replay}
    <div class="stake">
      <button id="betDown" type="button" disabled={locked} onclick={() => onBet(-1)}>–</button>
      <div class="readout compact">
        <span>{labels.stake()}</span>
        <strong id="betValue">{moneyHud(ui.betMicro)}</strong>
      </div>
      <button id="betUp" type="button" disabled={locked} onclick={() => onBet(1)}>+</button>
    </div>
  {/if}

  <button id="spinBtn" class="spin" type="button" disabled={locked} onclick={onSpin}>
    {ui.replay && ui.winMicro ? "Play again" : labels.spin()}
  </button>
  <button class="ghost" type="button" onclick={() => (ui.rulesOpen = true)}>Rules</button>
  <button
    id="musicBtn"
    class="ghost"
    type="button"
    onclick={() => toggleMusicMute()}
    aria-pressed={!ui.musicMuted}
  >
    {ui.musicMuted ? "Music off" : "Music"}
  </button>
</div>

<style>
  .bar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: stretch;
    justify-content: center;
    margin-top: 16px;
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .readout {
    min-width: 118px;
    background: #1a140e;
    border: 1px solid #6a5438;
    padding: 8px 12px;
    color: #f0dcc4;
  }
  .readout span {
    display: block;
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    opacity: 0.62;
  }
  .readout strong {
    font-size: 20px;
    font-variant-numeric: tabular-nums;
  }
  .compact {
    min-width: 92px;
    text-align: center;
  }
  .extra {
    min-width: 96px;
    border-color: #c47848;
    background: #2a1810;
  }
  button {
    border: 1px solid #6a5438;
    background: #2a2118;
    color: #f0dcc4;
    padding: 0 16px;
    cursor: pointer;
    font: inherit;
    min-height: 52px;
  }
  button:disabled {
    opacity: 0.45;
    cursor: wait;
  }
  .spin {
    min-width: 120px;
    background: #7a3218;
    border-color: #c4a574;
    color: #f8ece0;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 700;
  }
  .ghost {
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 12px;
  }
  .stake {
    display: flex;
    align-items: stretch;
    gap: 0;
  }
  .stake button {
    min-width: 44px;
    padding: 0;
  }
</style>
