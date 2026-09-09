<script lang="ts">
  import { onMount } from "svelte";
  import Game from "./components/Game.svelte";
  import Hud from "./components/Hud.svelte";
  import Rules from "./components/Rules.svelte";
  import BonusIntro from "./components/BonusIntro.svelte";
  import { bootEngine, playBet } from "./game/betMachine.svelte";
  import { changeBet, confirmBonusStart, ui } from "./lib/ui.svelte";
  import { bootMusic, musicBedFromUi, setMusicBed, unlockMusic } from "./lib/music";

  async function spin() {
    await playBet();
  }

  $effect(() => {
    void setMusicBed(musicBedFromUi());
  });

  onMount(() => {
    bootMusic();
    const unlock = () => {
      void unlockMusic();
    };
    window.addEventListener("pointerdown", unlock, { once: true });
    void bootEngine().catch((error) => {
      ui.error = error instanceof Error ? error.message : "Could not start the engine session.";
      ui.ready = true;
    });
    const onKey = (event: KeyboardEvent) => {
      if (event.code !== "Space" || ui.disableSpacebar || ui.rulesOpen) return;
      event.preventDefault();
      void unlockMusic();
      if (ui.bonusIntroOpen) {
        confirmBonusStart();
        return;
      }
      void spin();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", onKey);
    };
  });
</script>

<div class="cabinet" class:feature={ui.feature}>
  <header class="masthead">
    <h1>Sunset Stereo</h1>
  </header>

  <div class="frame">
    <Game />
    <BonusIntro />
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
</div>
