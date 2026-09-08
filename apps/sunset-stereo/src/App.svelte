<script lang="ts">
  import { onMount } from "svelte";
  import Game from "./components/Game.svelte";
  import Hud from "./components/Hud.svelte";
  import { playBet } from "./game/betMachine.svelte";
  import { changeBet, ui } from "./lib/ui.svelte";
  import { GAME, PAYTABLE } from "./math/config.js";
  import { SYMBOL_NAMES, SYMBOL_NOTES } from "./lib/names";

  const payRows = Object.entries(PAYTABLE) as Array<[string, Record<string, number>]>;

  async function spin(buyBonus = false) {
    await playBet(buyBonus);
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
      <h1>Golden Hour</h1>
    </div>
    <p class="blurb">
      Five reels, three rows, twenty lines. Vinyl, cassette, mixer and sunset scatter. RTP
      {(GAME.rtp * 100).toFixed(0)}%. Maximum win {GAME.wincap}× stake.
    </p>
  </header>

  <div class="frame">
    <Game />
  </div>

  <p class="banner" class:show={Boolean(ui.banner)}>{ui.banner}</p>
  <p id="mixValue" class="sr-only">{ui.mix}×</p>

  <Hud onSpin={() => spin()} onBonus={() => spin(true)} onBet={changeBet} />

  <section class="paytable" aria-label="Paytable">
    <h2>Pays</h2>
    <p>Line wins pay left to right on twenty fixed lines. The mixer substitutes for everything except the sunset.</p>
    <ul>
      {#each payRows as [id, pays]}
        <li>
          <strong>{SYMBOL_NAMES[id] ?? id}</strong>
          <span>5 {pays[5]}× · 4 {pays[4]}× · 3 {pays[3]}×</span>
        </li>
      {/each}
      <li>
        <strong>{SYMBOL_NAMES.S}</strong>
        <span>{SYMBOL_NOTES.S}</span>
      </li>
    </ul>
  </section>

  <footer>
    Malfunction voids all pays. This is a local book-event player for the Sunset Stereo math package — not a live
    Remote Game Server session. Space bar spins.
  </footer>
</div>
