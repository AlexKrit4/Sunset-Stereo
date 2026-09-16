<script lang="ts">
  import { moneyHud, ui } from "../lib/ui.svelte";
</script>

{#if ui.bigWinOpen}
  <div
    class="bigwin"
    role="dialog"
    aria-label="Big win"
    aria-modal="true"
    data-bigwin="1"
    data-bigwin-left={ui.bigWinLeft}
    data-bigwin-right={ui.bigWinRight}
    data-bigwin-explode={ui.bigWinExplode ? "1" : "0"}
  >
    <div class="titles">
      {#if ui.bigWinOutgoingLeft}
        {#key ui.bigWinOutgoingKey}
          <p class="title away" aria-hidden="true">
            <span>{ui.bigWinOutgoingLeft}</span>
            <span>{ui.bigWinOutgoingRight}</span>
          </p>
        {/key}
      {/if}
      {#if ui.bigWinLeft}
        {#key ui.bigWinTitleKey}
          <h2 class="title current" class:explode={ui.bigWinExplode}>
            <span class="from-left">{ui.bigWinLeft}</span>
            <span class="from-right">{ui.bigWinRight}</span>
          </h2>
        {/key}
      {/if}
    </div>
    {#if ui.bigWinLeft}
      <p id="bigWinValue" class="amount" aria-live="polite">{moneyHud(ui.bigWinDisplayMicro)}</p>
    {/if}
  </div>
{/if}

<style>
  .bigwin {
    position: fixed;
    inset: 0;
    z-index: 80;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding-bottom: 8vh;
    pointer-events: auto;
    background:
      radial-gradient(ellipse at 50% 42%, rgba(48, 18, 8, 0.18) 0%, rgba(8, 2, 16, 0.78) 72%);
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    color: #ffd060;
  }
  .titles {
    position: relative;
    font-size: clamp(34px, 7vw, 72px);
    height: 1.2em;
    min-width: min(90vw, 920px);
    margin-bottom: 52px;
    overflow: visible;
  }
  .title {
    position: absolute;
    inset: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.28em;
    margin: 0;
    font-size: 1em;
    font-weight: 800;
    letter-spacing: 0.12em;
    line-height: 1;
    white-space: nowrap;
    text-transform: uppercase;
    text-shadow:
      0 0 10px #ff9a28,
      0 3px 0 #7a2a08,
      0 8px 22px rgba(8, 2, 16, 0.9);
  }
  .from-left {
    animation: from-left 1s cubic-bezier(0.16, 0.84, 0.28, 1) both;
  }
  .from-right {
    animation: from-right 1s cubic-bezier(0.16, 0.84, 0.28, 1) both;
  }
  .away {
    animation: toward-camera 0.7s cubic-bezier(0.2, 0.8, 0.28, 1) forwards;
  }
  .explode {
    animation: explode 0.72s cubic-bezier(0.12, 0.8, 0.32, 1.15) both;
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
  @keyframes from-left {
    from {
      transform: translateX(-58vw);
      opacity: 0.2;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @keyframes from-right {
    from {
      transform: translateX(58vw);
      opacity: 0.2;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @keyframes toward-camera {
    from {
      transform: scale(1);
      opacity: 1;
      filter: blur(0);
    }
    to {
      transform: scale(3.2);
      opacity: 0;
      filter: blur(6px);
    }
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
</style>
