<script lang="ts">
  import { onMount } from "svelte";
  import Game from "./components/Game.svelte";
  import Hud from "./components/Hud.svelte";
  import { playBet } from "./game/betMachine.svelte";
  import { changeBet, ui } from "./lib/ui.svelte";
  import { GAME, PAYOUTS } from "./math/config.js";
  import { SYMBOL_NAMES } from "./lib/names";

  const payRows = Object.entries(PAYOUTS) as Array<[string, Record<string, number>]>;

  async function spin() {
    await playBet();
  }

  onMount(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.code === "Space") {
        event.preventDefault();
        void spin();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
</script>

<div class="cabinet" class:feature={ui.feature}>
  <header class="masthead">
    <div>
      <p class="kicker">{GAME.name}</p>
      <h1>Sunset Stereo</h1>
    </div>
    <p class="blurb">
      Six reels, four rows, left-to-right ways. Three suns start 10 extra plays. Winning extra
      plays hold and respin until nothing new is built. RTP {(GAME.rtp * 100).toFixed(0)}%.
    </p>
  </header>

  <div class="frame">
    <Game />
  </div>

  <p class="banner" class:show={Boolean(ui.banner)}>{ui.banner}</p>
  <p id="mixValue" class="sr-only">1×</p>

  <Hud onSpin={() => spin()} onBet={changeBet} />

  <section class="paytable" aria-label="Paytable">
    <h2>Ways pays</h2>
    <p>
      Left to right, three or more reels. Three suns on reels 2–5 start 10 extra plays (one book).
      A winning extra play is not paid yet — it holds and respins unlocked cells. New ways, even
      of other symbols, can be built. If a respin adds no new winning cells, that extra play ends
      and then pays.
    </p>
    <ul>
      {#each payRows as [id, pays]}
        <li>
          <strong>{SYMBOL_NAMES[id] ?? id}</strong>
          <span>6 {pays[6]}× · 5 {pays[5]}× · 4 {pays[4]}× · 3 {pays[3]}×</span>
        </li>
      {/each}
    </ul>
  </section>

  <footer>
    Malfunction voids all pays. Space bar spins. Base game plus 10 extra plays is one bet.
  </footer>
</div>
