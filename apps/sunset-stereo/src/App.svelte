<script lang="ts">
  import { onMount } from "svelte";
  import Game from "./components/Game.svelte";
  import Hud from "./components/Hud.svelte";
  import BigWin from "./components/BigWin.svelte";
  import Rules from "./components/Rules.svelte";
  import BonusIntro from "./components/BonusIntro.svelte";
  import BuyMenu from "./components/BuyMenu.svelte";
  import Loader from "./components/Loader.svelte";
  import { bootEngine, playBet, playBuyBonus, playBuyWildBonus, playPendingRestore } from "./game/betMachine.svelte";
  import { changeBet, confirmBonusStart, stopAutoplay, ui } from "./lib/ui.svelte";
  import { bindMusicUnlock, bootMusic, musicBedFromUi, setMusicBed, unlockMusic } from "./lib/music";
  import { preloadGame } from "./lib/preload";

  let unbindMusic = () => {};

  async function spin() {
    if (ui.bootOpen) return false;
    unlockMusic();
    return playBet(ui.scatterBuyOn ? "scatter" : "base");
  }

  function continueBoot() {
    if (!ui.bootReady && !ui.error) return;
    bootMusic();
    unlockMusic();
    ui.bootOpen = false;
    unbindMusic = bindMusicUnlock();
    void playPendingRestore();
  }

  $effect(() => {
    if (ui.bootOpen) return;
    setMusicBed(musicBedFromUi());
  });

  $effect(() => {
    if (
      ui.bootOpen ||
      !ui.autoplayOn ||
      ui.autoplayLeft <= 0 ||
      ui.autoplayMenuOpen ||
      ui.busy ||
      !ui.ready ||
      ui.replay ||
      ui.buyMenuOpen ||
      ui.rulesOpen ||
      ui.bonusIntroOpen ||
      ui.bigWinOpen ||
      ui.buyConfirm ||
      ui.trayOpen ||
      ui.error
    ) {
      return;
    }
    const timer = window.setTimeout(async () => {
      const ok = await spin();
      if (!ui.autoplayOn) return;
      if (!ok) {
        stopAutoplay();
        return;
      }
      ui.autoplayLeft = Math.max(0, ui.autoplayLeft - 1);
      if (ui.autoplayLeft <= 0) stopAutoplay();
    }, ui.fastPlay ? 90 : 280);
    return () => window.clearTimeout(timer);
  });

  onMount(() => {
    void (async () => {
      try {
        await Promise.all([
          preloadGame((ratio) => {
            ui.bootProgress = ratio;
          }),
          bootEngine(),
        ]);
      } catch (error) {
        ui.error = error instanceof Error ? error.message : "Could not start the engine session.";
        ui.ready = true;
      }
      ui.bootProgress = 1;
      ui.bootReady = true;
    })();
    const onKey = (event: KeyboardEvent) => {
      if (ui.bootOpen) {
        if ((event.code === "Space" || event.code === "Enter") && (ui.bootReady || ui.error)) {
          event.preventDefault();
          continueBoot();
        }
        return;
      }
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
        if (ui.autoplayMenuOpen) {
          event.preventDefault();
          ui.autoplayMenuOpen = false;
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
        ui.trayOpen ||
        ui.autoplayMenuOpen ||
        ui.bigWinOpen
      ) {
        return;
      }
      event.preventDefault();
      unlockMusic();
      if (ui.bonusIntroOpen) {
        confirmBonusStart();
        return;
      }
      if (ui.autoplayOn) {
        stopAutoplay();
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

<Loader onContinue={continueBoot} />

<div class="stage">
<div class="cabinet" class:feature={ui.feature} class:booting={ui.bootOpen}>
  <header class="masthead">
    <h1>Sunset Stereo</h1>
  </header>

  <div class="frame">
    <Game />
    <BonusIntro />
    {#if !ui.ready && !ui.bootOpen}
      <p class="loading">
        {ui.replay ? "Loading replay…" : ui.source === "live" ? "Connecting to the game server…" : "Loading reels…"}
      </p>
    {/if}
    {#if ui.error && !ui.bootOpen}
      <p class="loading">{ui.error}</p>
    {/if}
  </div>

  <p class="banner" class:show={Boolean(ui.banner)}>{ui.banner}</p>
  <p id="mixValue" class="sr-only">1×</p>

  <Hud onSpin={() => spin()} onBet={changeBet} />
  <BigWin />
  <BuyMenu onBuyBonus={() => playBuyBonus()} onBuyWildBonus={() => playBuyWildBonus()} />
  <Rules />
</div>
</div>
{#if import.meta.env.VITE_VPS === "1"}
  {#await import("./vps/VpsStats.svelte") then mod}
    <mod.default />
  {/await}
{/if}
