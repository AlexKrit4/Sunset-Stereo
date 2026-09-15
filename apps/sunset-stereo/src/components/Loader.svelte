<script lang="ts">
  import { ui } from "../lib/ui.svelte";

  let {
    onContinue,
  }: {
    onContinue: () => void;
  } = $props();

  const percent = $derived(Math.max(0, Math.min(100, Math.round(ui.bootProgress * 100))));
</script>

{#if ui.bootOpen}
  <div class="boot" role="dialog" aria-label="Loading" aria-modal="true" data-boot="1" data-boot-ready={ui.bootReady ? "1" : "0"}>
    <div class="card">
      <p class="kicker">Sunset Stereo</p>
      <h1>Sunset Stereo</h1>
      {#if ui.error}
        <p class="status">{ui.error}</p>
        <button id="bootContinueBtn" type="button" onclick={onContinue}>Continue</button>
      {:else if !ui.bootReady}
        <p class="status">Loading</p>
        <div class="bar" aria-hidden="true">
          <span style:width={`${percent}%`}></span>
        </div>
        <p id="bootProgress" class="pct">{percent}%</p>
      {:else}
        <p class="status">Ready</p>
        <button id="bootContinueBtn" type="button" onclick={onContinue}>Continue</button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .boot {
    position: fixed;
    inset: 0;
    z-index: 200;
    display: grid;
    place-items: center;
    padding: 24px;
    background:
      radial-gradient(ellipse at 50% 42%, rgba(48, 18, 8, 0.2) 0%, rgba(8, 2, 16, 0.82) 72%);
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    color: #ffd060;
  }
  .card {
    width: min(440px, 100%);
    text-align: center;
  }
  .kicker {
    margin: 0 0 8px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    font-size: 11px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    color: #e8c890;
  }
  h1 {
    margin: 0 0 18px;
    font-size: clamp(36px, 7vw, 56px);
    font-weight: 600;
    color: #f8ecd8;
    text-shadow: 0 2px 16px rgba(10, 6, 2, 0.8);
  }
  .status {
    margin: 0 0 16px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-size: 13px;
    color: #f0d8a0;
  }
  .bar {
    width: 100%;
    height: 8px;
    overflow: hidden;
    border-radius: 99px;
    background: rgba(20, 10, 8, 0.65);
    box-shadow: inset 0 0 0 1px rgba(196, 165, 116, 0.35);
  }
  .bar span {
    display: block;
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #c47a28, #ffd060);
    transition: width 0.2s ease;
  }
  .pct {
    margin: 12px 0 0;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.08em;
    color: #f8ecd8;
  }
  button {
    min-width: 180px;
    min-height: 54px;
    border: 1px solid #c4a574;
    background: #7a3218;
    color: #f8ece0;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    cursor: pointer;
  }
</style>
