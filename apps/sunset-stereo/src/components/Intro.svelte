<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import titleLogo from "../assets/sunset-stereo-logo.png";
  import { ui } from "../lib/ui.svelte";
  import { SYMBOL_PAY_ART } from "../pixi/symbols";
  import { playPendingRestore } from "../game/betMachine.svelte";

  const CLOSE_MS = 480;
  let closing = $state(false);
  let closeTimer: ReturnType<typeof setTimeout> | undefined;

  function dismiss() {
    if (closing) return;
    closing = true;
    closeTimer = setTimeout(() => {
      ui.introOpen = false;
      void playPendingRestore();
    }, CLOSE_MS);
  }

  function onKey(event: KeyboardEvent) {
    if (event.code === "Space" || event.code === "Enter" || event.code === "NumpadEnter" || event.code === "Escape") {
      event.preventDefault();
      dismiss();
    }
  }

  onMount(() => window.addEventListener("keydown", onKey));
  onDestroy(() => {
    window.removeEventListener("keydown", onKey);
    if (closeTimer !== undefined) clearTimeout(closeTimer);
  });
</script>

{#if ui.introOpen}
  <div class="intro" class:closing role="button" tabindex="-1" aria-label="Press to continue" onclick={dismiss} data-intro="1">
    <img class="logo" src={titleLogo} alt="Sunset Stereo" />
    <div class="cards">
      <article class="card">
        <div class="icons">
          <img src={SYMBOL_PAY_ART.scatter} alt="" />
          <img src={SYMBOL_PAY_ART.scatter} alt="" />
          <img src={SYMBOL_PAY_ART.scatter} alt="" />
        </div>
        <h2>Golden Hour<br />Bonus</h2>
        <p>3 солнца на барабанах 2–5 дают 10 экстра-спинов</p>
      </article>
      <article class="card center">
        <div class="icons">
          <img src={SYMBOL_PAY_ART.wild} alt="" />
          <img src={SYMBOL_PAY_ART.high1} alt="" />
          <img src={SYMBOL_PAY_ART.wild} alt="" />
        </div>
        <h2>Hold &amp; Respin</h2>
        <p>
          Выигрышные символы фиксируются, остальные респинятся, пока растёт выигрыш.
          Вайлд за 4 солнца остаётся до конца раунда
        </p>
      </article>
      <article class="card">
        <p class="max">15 000×</p>
        <h2>Max Win</h2>
        <p>Выигрыш до 15 000× от ставки</p>
      </article>
    </div>
    <p class="cta">Нажмите чтобы продолжить</p>
  </div>
{/if}

<style>
  .intro {
    position: fixed;
    inset: 0;
    z-index: 250;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: clamp(14px, 3.5vh, 34px);
    padding: clamp(12px, 3vh, 32px) 20px;
    cursor: pointer;
    background:
      linear-gradient(rgba(10, 6, 20, 0.55), rgba(10, 6, 20, 0.72)),
      url("/sunset-scene.jpg") center 48% / cover no-repeat,
      #14081c;
    animation: intro-in 0.45s ease-out;
    transition: opacity 0.45s ease;
  }
  .intro.closing {
    opacity: 0;
  }
  .logo {
    width: min(46vh, 420px);
    max-width: 82vw;
    filter: drop-shadow(0 6px 24px rgba(10, 4, 16, 0.85));
    animation: card-in 0.6s ease-out both;
  }
  .cards {
    display: flex;
    justify-content: center;
    align-items: stretch;
    gap: clamp(12px, 2.5vw, 34px);
    width: 100%;
    max-width: 1150px;
  }
  .card {
    position: relative;
    flex: 1 1 0;
    max-width: 330px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    gap: 10px;
    padding: clamp(14px, 3vh, 26px) clamp(12px, 2vw, 22px);
    text-align: center;
    background: linear-gradient(180deg, #16204a 0%, #0d1430 100%);
    border: 3px solid #d7ac70;
    outline: 1px solid rgba(215, 172, 112, 0.45);
    outline-offset: 5px;
    border-radius: 10px;
    box-shadow:
      0 0 0 1px rgba(60, 32, 10, 0.9),
      0 18px 40px rgba(6, 2, 14, 0.6),
      inset 0 0 26px rgba(215, 172, 112, 0.1);
    animation: card-in 0.55s ease-out both;
  }
  .card:nth-child(2) {
    animation-delay: 0.12s;
  }
  .card:nth-child(3) {
    animation-delay: 0.24s;
  }
  .card.center {
    transform: scale(1.06);
    border-color: #f2ce8e;
    box-shadow:
      0 0 26px rgba(242, 206, 142, 0.35),
      0 18px 40px rgba(6, 2, 14, 0.6),
      inset 0 0 26px rgba(242, 206, 142, 0.12);
  }
  .card::before,
  .card::after {
    content: "";
    position: absolute;
    top: -9px;
    width: 12px;
    height: 12px;
    background: #f2ce8e;
    transform: rotate(45deg);
    box-shadow: 0 0 8px rgba(242, 206, 142, 0.7);
  }
  .card::before {
    left: -9px;
  }
  .card::after {
    right: -9px;
  }
  .icons {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    min-height: 52px;
  }
  .icons img {
    width: clamp(36px, 6.5vh, 52px);
    height: auto;
    filter: drop-shadow(0 4px 10px rgba(4, 2, 10, 0.7));
  }
  h2 {
    margin: 0;
    font-family: "Arial Narrow", "Franklin Gothic Medium", ui-sans-serif, system-ui, sans-serif;
    font-size: clamp(20px, 4.2vh, 34px);
    font-weight: 900;
    line-height: 1.02;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    background: linear-gradient(180deg, #fff7d6 12%, #f2ce8e 45%, #c07c2e 90%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    filter: drop-shadow(0 2px 4px rgba(4, 2, 10, 0.85));
  }
  .card p {
    margin: 0;
    font-family: "Arial Narrow", "Franklin Gothic Medium", ui-sans-serif, system-ui, sans-serif;
    font-size: clamp(12px, 2.4vh, 16px);
    font-weight: 700;
    letter-spacing: 0.02em;
    line-height: 1.3;
    text-transform: uppercase;
    color: #f4e6cf;
    text-wrap: balance;
  }
  .max {
    display: flex;
    align-items: center;
    min-height: 52px;
    font-family: "Arial Narrow", "Franklin Gothic Medium", ui-sans-serif, system-ui, sans-serif;
    font-size: clamp(26px, 6vh, 44px);
    font-weight: 900;
    line-height: 1;
    background: linear-gradient(180deg, #fff7d6 10%, #ffd060 50%, #c07c2e 95%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    filter: drop-shadow(0 3px 6px rgba(4, 2, 10, 0.85));
  }
  .cta {
    margin: 0;
    font-family: "Arial Narrow", "Franklin Gothic Medium", ui-sans-serif, system-ui, sans-serif;
    font-size: clamp(13px, 2.6vh, 18px);
    font-weight: 800;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #f4e6cf;
    text-shadow: 0 2px 8px rgba(4, 2, 10, 0.9);
    animation: cta-pulse 1.6s ease-in-out infinite;
  }
  @keyframes intro-in {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  @keyframes card-in {
    from {
      opacity: 0;
      transform: translateY(16px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  @keyframes cta-pulse {
    0%,
    100% {
      opacity: 0.65;
    }
    50% {
      opacity: 1;
    }
  }
  @media (max-width: 720px) {
    .cards {
      flex-direction: column;
      align-items: center;
      gap: 14px;
    }
    .card {
      width: min(340px, 92vw);
      max-width: none;
      padding-top: 14px;
      padding-bottom: 14px;
      gap: 6px;
    }
    .card.center {
      transform: none;
    }
    .icons {
      min-height: 40px;
    }
    .icons img {
      width: 36px;
    }
    .max {
      min-height: 36px;
      font-size: 30px;
    }
  }
</style>
