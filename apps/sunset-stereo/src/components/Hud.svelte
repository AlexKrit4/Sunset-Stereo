<script lang="ts">
  import { money, ui } from "../lib/ui.svelte";

  let {
    onSpin,
    onBet,
  }: {
    onSpin: () => void;
    onBet: (delta: number) => void;
  } = $props();
</script>

<div class="bar">
  <div class="readout">
    <span>Credit</span>
    <strong id="balanceValue">{money(ui.balance)}</strong>
  </div>
  <div class="readout">
    <span>Paid</span>
    <strong id="winValue">{money(ui.win)}</strong>
  </div>

  <div class="stake">
    <button id="betDown" type="button" disabled={ui.busy} onclick={() => onBet(-1)}>–</button>
    <div class="readout compact">
      <span>Stake</span>
      <strong id="betValue">{money(ui.bet)}</strong>
    </div>
    <button id="betUp" type="button" disabled={ui.busy} onclick={() => onBet(1)}>+</button>
  </div>

  <button id="spinBtn" class="spin" type="button" disabled={ui.busy} onclick={onSpin}>Spin</button>
</div>

<style>
  .bar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: stretch;
    justify-content: center;
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
