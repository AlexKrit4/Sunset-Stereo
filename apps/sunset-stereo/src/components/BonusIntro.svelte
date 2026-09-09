<script lang="ts">
  import { confirmBonusStart, ui } from "../lib/ui.svelte";
</script>

{#if ui.bonusIntroOpen}
  <div class="bonus-intro" role="dialog" aria-label="Bonus extra plays" aria-modal="true">
    <div class="card">
      <p class="kicker">Bonus</p>
      <h2>{ui.bonusIntroSpins} Extra Plays</h2>
      <p>
        Winning extra plays hold and respin until nothing new is built. Then that extra play
        pays.
      </p>
      <button id="bonusStartBtn" type="button" onclick={confirmBonusStart}>Start</button>
    </div>
  </div>
{/if}

<style>
  .bonus-intro {
    position: absolute;
    inset: 0;
    z-index: 8;
    display: grid;
    place-items: center;
    padding: 18px;
    background: rgba(10, 4, 16, 0.62);
  }
  .card {
    width: min(420px, 100%);
    padding: 28px 26px 22px;
    text-align: center;
    color: #2a1c12;
    background: linear-gradient(180deg, #f8ecd8 0%, #e8c890 100%);
    border: 2px solid #c4a574;
    box-shadow: 0 16px 40px rgba(8, 2, 16, 0.45);
  }
  .kicker {
    margin: 0 0 6px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    font-size: 11px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    color: #7a3218;
  }
  h2 {
    margin: 0 0 10px;
    font-size: clamp(28px, 5vw, 40px);
    color: #7a3218;
  }
  p {
    margin: 0 0 18px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.45;
  }
  button {
    min-width: 160px;
    min-height: 52px;
    border: 1px solid #c4a574;
    background: #7a3218;
    color: #f8ece0;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    cursor: pointer;
  }
</style>
