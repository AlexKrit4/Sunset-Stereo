<script lang="ts">
  import { confirmMaxWin } from "../lib/bigWin";
  import { ui } from "../lib/ui.svelte";

  const displayX = $derived(
    (ui.maxWinDisplayMicro / Math.max(1, ui.betMicro)).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }),
  );
</script>

{#if ui.maxWinOpen}
  <div
    class="maxwin"
    class:leaving={ui.maxWinLeaving}
    role="dialog"
    aria-label="Max win"
    aria-modal="true"
    data-maxwin="1"
  >
    <h2 class="title">MAX WIN</h2>
    <p id="maxWinValue" class="amount" class:pulse={ui.maxWinPulse} aria-live="polite">
      {displayX}×
    </p>
    {#if ui.maxWinReady}
      <button id="maxWinContinue" class="continue" type="button" onclick={() => confirmMaxWin()}>
        Continue
      </button>
    {/if}
  </div>
{/if}

<style>
  .maxwin {
    position: fixed;
    inset: 0;
    z-index: 90;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding-bottom: 6vh;
    background:
      radial-gradient(ellipse at 50% 42%, rgba(48, 18, 8, 0.3) 0%, rgba(8, 2, 16, 0.92) 72%);
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    color: #ffd060;
    transition: opacity 0.6s ease;
  }
  .maxwin.leaving {
    opacity: 0;
  }
  .title {
    margin: 0 0 48px;
    font-size: clamp(36px, 7vw, 72px);
    font-weight: 800;
    letter-spacing: 0.14em;
    line-height: 1;
    text-transform: uppercase;
    white-space: nowrap;
    text-shadow:
      0 0 10px #ff9a28,
      0 3px 0 #7a2a08,
      0 8px 22px rgba(8, 2, 16, 0.9);
  }
  .amount {
    margin: 0;
    font-weight: 800;
    font-size: clamp(52px, 12vw, 108px);
    letter-spacing: 0.03em;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    text-shadow:
      0 0 12px #ff9a28,
      0 0 28px rgba(255, 140, 32, 0.7),
      0 3px 0 #7a2a08,
      0 8px 22px rgba(8, 2, 16, 0.9);
  }
  .amount.pulse {
    animation: explode 0.72s cubic-bezier(0.12, 0.8, 0.32, 1.15) both;
  }
  .continue {
    margin-top: 56px;
    min-width: 200px;
    min-height: 56px;
    border: 1px solid #c4a574;
    background: #7a3218;
    color: #f8ece0;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    font-size: 16px;
    cursor: pointer;
    animation: continue-in 0.4s ease both;
  }
  @keyframes explode {
    0% {
      transform: scale(1);
      filter: brightness(1);
    }
    42% {
      transform: scale(1.7);
      filter: brightness(1.45);
    }
    100% {
      transform: scale(1.12);
      filter: brightness(1.08);
    }
  }
  @keyframes continue-in {
    from {
      transform: translateY(16px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }
</style>
