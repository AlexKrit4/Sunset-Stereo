<script lang="ts">
  import { onMount } from "svelte";
  import Game from "./components/Game.svelte";
  import Hud from "./components/Hud.svelte";
  import Rules from "./components/Rules.svelte";
  import BonusIntro from "./components/BonusIntro.svelte";
  import BuyMenu from "./components/BuyMenu.svelte";
  import { bootEngine, playBet, playBuyBonus, playBuyWildBonus } from "./game/betMachine.svelte";
  import { changeBet, confirmBonusStart, ui } from "./lib/ui.svelte";
  import { bindMusicUnlock, bootMusic, musicBedFromUi, setMusicBed, unlockMusic } from "./lib/music";

  async function spin() {
    unlockMusic();
    await playBet(ui.scatterBuyOn ? "scatter" : "base");
  }

  $effect(() => {
    setMusicBed(musicBedFromUi());
  });

  $effect(() => {
    if (
      !ui.autoplayOn ||
      ui.busy ||
      !ui.ready ||
      ui.replay ||
      ui.buyMenuOpen ||
      ui.rulesOpen ||
      ui.bonusIntroOpen ||
      ui.buyConfirm ||
      ui.trayOpen ||
      ui.error
    ) {
      return;
    }
    const timer = window.setTimeout(() => {
      void spin();
    }, 280);
    return () => window.clearTimeout(timer);
  });

  onMount(() => {
    bootMusic();
    const unbindMusic = bindMusicUnlock();
    void bootEngine().catch((error) => {
      ui.error = error instanceof Error ? error.message : "Could not start the engine session.";
      ui.ready = true;
    });
    const onKey = (event: KeyboardEvent) => {
      if (event.code === "Escape") {
        if (ui.buyConfirm) {
          event.preventDefault();
          ui.buyConfirm = "";
          return;
        }
        if (ui.buyMenuOpen) {
          event.preventDefault();
          ui.buyMenuOpen = false;
          return;
        }
        if (ui.trayOpen) {
          event.preventDefault();
          ui.trayOpen = false;
          return;
        }
      }
      if (
        event.code !== "Space" ||
        ui.disableSpacebar ||
        ui.rulesOpen ||
        ui.buyMenuOpen ||
        ui.buyConfirm ||
        ui.trayOpen
      ) {
        return;
      }
      event.preventDefault();
      unlockMusic();
      if (ui.bonusIntroOpen) {
        confirmBonusStart();
        return;
      }
      void spin();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      unbindMusic();
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
  <BuyMenu onBuyBonus={() => playBuyBonus()} onBuyWildBonus={() => playBuyWildBonus()} />
  <Rules />
</div>
