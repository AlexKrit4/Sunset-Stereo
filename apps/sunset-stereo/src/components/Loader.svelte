<script lang="ts">
  import introAnimation from "../assets/big-fathers-intro.webp";
  import introPoster from "../assets/big-fathers-poster.png";
  import { labels, moneyHud, ui } from "../lib/ui.svelte";

  let {
    onContinue,
  }: {
    onContinue: () => void;
  } = $props();

  let imageFailed = $state(false);
  const ready = $derived(ui.bootReady && ui.bootImageReady);
  const percent = $derived(ready ? 100 : Math.max(0, Math.min(99, Math.round(ui.bootProgress * 100))));
  const replayMult = $derived(Number(ui.replayMult.toFixed(2)));
</script>

{#if ui.bootOpen}
  <div class="boot" role="dialog" aria-label="Loading" aria-modal="true" data-boot="1" data-boot-ready={ready ? "1" : "0"}>
    <div class="card">
      <img
        class="preview"
        src={imageFailed ? introPoster : introAnimation}
        alt="Big Fathers"
        onload={() => (ui.bootImageReady = true)}
        onerror={() => {
          if (imageFailed) ui.bootImageReady = true;
          else imageFailed = true;
        }}
      />
      <p id="bootProgress" class="pct" role="status" aria-live="polite">{percent}%</p>
      {#if ui.error}
        <p class="status">{ui.error}</p>
        {#if ready}
          <button id="bootContinueBtn" type="button" onclick={onContinue}>Continue</button>
        {/if}
      {:else if ready}
        {#if ui.replay}
          <dl class="replay-info" data-replay-info="1">
            <div><dt>{labels.stake()}</dt><dd id="replayBet">{moneyHud(ui.betMicro)}</dd></div>
            <div><dt>Round</dt><dd id="replayMult">{replayMult}×</dd></div>
            <div><dt>{labels.win()}</dt><dd id="replayWin">{moneyHud(ui.replayWinMicro)}</dd></div>
          </dl>
        {/if}
        <button id="bootContinueBtn" type="button" onclick={onContinue}>{ui.replay ? "Replay" : "Continue"}</button>
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
    padding: clamp(12px, 2.5vh, 24px);
    background: #000;
    color: #f8ecd8;
  }
  .card {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    max-height: 100%;
    text-align: center;
  }
  .preview {
    display: block;
    width: min(100%, 1120px, 110dvh);
    aspect-ratio: 16 / 9;
    object-fit: contain;
  }
  .status {
    margin: 0 0 18px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 14px;
    color: #f0d8a0;
  }
  .pct {
    margin: 8px 0 18px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: clamp(18px, 3vh, 26px);
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.08em;
    color: #f2dfbd;
  }
  .replay-info {
    display: flex;
    justify-content: center;
    gap: 28px;
    margin: 0 0 20px;
    padding: 0;
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .replay-info div {
    text-align: center;
  }
  .replay-info dt {
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #cbbba8;
  }
  .replay-info dd {
    margin: 4px 0 0;
    font-size: 22px;
    font-variant-numeric: tabular-nums;
    color: #f8ecd8;
  }
  button {
    min-width: 180px;
    min-height: 50px;
    border: 1px solid #d7ac70;
    border-radius: 4px;
    background: #755033;
    color: #f8ece0;
    font-family: ui-sans-serif, system-ui, sans-serif;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    cursor: pointer;
  }
  button:hover,
  button:focus-visible {
    background: #9a6740;
  }
</style>
