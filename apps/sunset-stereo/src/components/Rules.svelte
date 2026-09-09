<script lang="ts">
  import { GAME, PAYOUTS } from "../math/config.js";
  import { ui } from "../lib/ui.svelte";
  import { SYMBOL_PAY_ART } from "../pixi/symbols";

  const payRows = Object.entries(PAYOUTS) as Array<[string, Record<string, number>]>;
  const disclaimer =
    "Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Engine.";
</script>

{#if ui.rulesOpen}
  <div
    class="scrim"
    onclick={(event) => {
      if (event.currentTarget === event.target) ui.rulesOpen = false;
    }}
    role="presentation"
  >
    <div class="sheet" role="dialog" aria-label="Game rules" aria-modal="true">
      <h2>Sunset Stereo</h2>
      <p>
        6×4 left-to-right ways. Three or more matching symbols from the leftmost reel pay.
        Three suns on reels 2–5 start 10 extra plays. A winning extra play holds and respins
        unlocked cells until nothing new is built, then pays. Base game plus extra plays is one bet.
        Buy bonus / Get bonus purchases 3 scatters for 95× the selected stake and starts those
        10 extra plays immediately.
      </p>
      <p>RTP {(GAME.rtp * 100).toFixed(0)}%. Max win {GAME.wincap.toLocaleString()}× of the 1× stake.</p>
      <p>
        Spin / Play starts a round. Buy / Get bonus opens the feature list (currently 3 scatters).
        + / – change the stake using bet levels from the game server.
        Spacebar also starts a round unless the operator disables it. Credit / Balance is the wallet.
        Paid / Won is the last round result. Extra plays shows the bonus counter.
      </p>

      <h3>Ways pays</h3>
      <ul class="pays">
        {#each payRows as [id, pays]}
          <li>
            <img src={SYMBOL_PAY_ART[id]} alt="" />
            <span>6 {pays[6]}× · 5 {pays[5]}× · 4 {pays[4]}× · 3 {pays[3]}×</span>
          </li>
        {/each}
        <li>
          <img src={SYMBOL_PAY_ART.scatter} alt="" />
          <span>3 suns on reels 2–5 start 10 extra plays</span>
        </li>
      </ul>

      <p class="note">{disclaimer}</p>
      {#if ui.source === "mock"}
        <p class="note">Local demo uses sample books until the game is opened from Stake Engine.</p>
      {/if}
      <button type="button" onclick={() => (ui.rulesOpen = false)}>Close</button>
    </div>
  </div>
{/if}

<style>
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 40;
    background: rgba(8, 2, 16, 0.72);
    display: grid;
    place-items: center;
    padding: 24px;
  }
  .sheet {
    max-width: 640px;
    max-height: min(88vh, 860px);
    overflow: auto;
    background: #f3e6d2;
    color: #2a1c12;
    padding: 24px;
    border: 1px solid #c4a574;
  }
  h2 {
    margin: 0 0 12px;
  }
  h3 {
    margin: 16px 0 10px;
    font-size: 18px;
  }
  p {
    margin: 0 0 12px;
    line-height: 1.45;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 14px;
  }
  .pays {
    list-style: none;
    margin: 0 0 16px;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 10px 16px;
  }
  .pays li {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    border-top: 1px solid rgba(42, 28, 18, 0.12);
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 13px;
  }
  .pays img {
    width: 44px;
    height: 44px;
    object-fit: cover;
    border-radius: 8px;
    flex: 0 0 44px;
  }
  .note {
    font-size: 12px;
    opacity: 0.86;
  }
  button {
    border: 1px solid #6a5438;
    background: #7a3218;
    color: #f8ece0;
    padding: 10px 16px;
    cursor: pointer;
  }
</style>
