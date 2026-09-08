<script lang="ts">
  import { onMount } from "svelte";
  import Game from "./components/Game.svelte";
  import Hud from "./components/Hud.svelte";
  import Rules from "./components/Rules.svelte";
  import { bootEngine, playBet } from "./game/betMachine.svelte";
  import { changeBet, ui } from "./lib/ui.svelte";
  import { GAME, PAYOUTS } from "./math/config.js";
  import { SYMBOL_NAMES } from "./lib/names";

  const payRows = Object.entries(PAYOUTS) as Array<[string, Record<string, number>]>;

  async function spin() {
    await playBet();
  }

  onMount(() => {
    void bootEngine().catch((error) => {
      ui.error = error instanceof Error ? error.message : "Could not start the engine session.";
      ui.ready = true;
    });
    const onKey = (event: KeyboardEvent) => {
      if (event.code !== "Space" || ui.disableSpacebar || ui.rulesOpen) return;
      event.preventDefault();
      void spin();
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
    {#if !ui.ready}
      <p class="loading">
        {ui.replay ? "Loading replay…" : ui.source === "live" ? "Connecting to the game server…" : "Loading reels…"}
      </p>
    {/if}
    {#if ui.error}
      <p class="loading">{ui.error}</p>
    {/if}
  </div>

  <p class="banner" class:show={Boolean(ui.banner)}>{ui.banner}</p>
  <p id="mixValue" class="sr-only">1×</p>

  <Hud onSpin={() => spin()} onBet={changeBet} />
  <Rules />

  <section class="paytable" aria-label="Paytable">
    <h2>Ways pays</h2>
    <p>
      Left to right, three or more reels. Three suns on reels 2–5 start 10 extra plays (one book).
      A winning extra play is not paid yet — it holds and respins unlocked cells. New ways, even
      of other symbols, can be built. If a respin adds no new winning cells, that extra play ends
      and then pays. Max win {GAME.wincap.toLocaleString()}×.
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
    Malfunction voids all wins and plays. A consistent internet connection is required. In the event
    of a disconnection, reload the game to finish any uncompleted rounds. The expected return is
    calculated over many plays. The game display is not representative of any physical device and is
    for illustrative purposes only. Winnings are settled according to the amount received from the
    Remote Game Server and not from events within the web browser. TM and © 2026 Engine.
    {ui.source === "mock" ? " Local demo uses sample books until the game is opened from Stake Engine." : ""}
  </footer>
</div>
