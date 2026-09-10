<script lang="ts">
  import { BUY_BONUS } from "../math/config.js";
  import { labels, moneyHud, ui } from "../lib/ui.svelte";

  let { onBuy }: { onBuy: () => void } = $props();

  const priceMicro = $derived(ui.betMicro * BUY_BONUS.cost);
  const canAfford = $derived(ui.balanceMicro >= priceMicro);

  function close() {
    ui.buyMenuOpen = false;
  }
</script>

{#if ui.buyMenuOpen}
  <div
    class="scrim"
    onclick={(event) => {
      if (event.currentTarget === event.target) close();
    }}
    role="presentation"
  >
    <div class="sheet" role="dialog" aria-label={labels.buyBonus()} aria-modal="true">
      <h2>{labels.buyBonus()}</h2>
      <p>
        One feature: {BUY_BONUS.label}. Starts 10 extra plays at {BUY_BONUS.cost}× the selected
        {ui.social ? "play amount" : "stake"}.
      </p>
      <button
        id="buyScatterBtn"
        class="offer"
        type="button"
        disabled={ui.busy || !canAfford}
        onclick={onBuy}
      >
        <span class="name">{BUY_BONUS.label}</span>
        <span class="meta">10 extra plays · {BUY_BONUS.cost}×</span>
        <strong>{moneyHud(priceMicro)}</strong>
      </button>
      {#if !canAfford}
        <p class="note">Not enough {ui.social ? "balance" : "credit"} for this {ui.social ? "play" : "buy"}.</p>
      {/if}
      <button class="ghost" type="button" onclick={close}>Close</button>
    </div>
  </div>
{/if}

<style>
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 42;
    background: rgba(8, 2, 16, 0.72);
    display: grid;
    place-items: center;
    padding: 24px;
  }
  .sheet {
    width: min(420px, 100%);
    background: #f3e6d2;
    color: #2a1c12;
    padding: 24px;
    border: 1px solid #c4a574;
  }
  h2 {
    margin: 0 0 12px;
  }
  p {
    margin: 0 0 16px;
    line-height: 1.45;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 14px;
  }
  .offer {
    display: grid;
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
    gap: 2px 16px;
    width: 100%;
    margin: 0 0 16px;
    padding: 14px 16px;
    text-align: left;
    border: 1px solid #6a5438;
    background: #7a3218;
    color: #f8ece0;
    cursor: pointer;
    font: inherit;
  }
  .offer:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .name {
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .meta {
    grid-column: 1;
    font-size: 12px;
    opacity: 0.86;
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .offer strong {
    grid-row: 1 / span 2;
    align-self: center;
    font-size: 18px;
    font-variant-numeric: tabular-nums;
  }
  .note {
    font-size: 12px;
    opacity: 0.86;
  }
  .ghost {
    border: 1px solid #6a5438;
    background: transparent;
    color: #2a1c12;
    padding: 10px 16px;
    cursor: pointer;
  }
</style>
