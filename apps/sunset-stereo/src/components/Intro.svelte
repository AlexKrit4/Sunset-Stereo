<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import titleLogo from "../assets/sunset-stereo-logo.png";
  import maxWinLogo from "../assets/max-win-logo.png";
  import cardFrame from "../assets/intro-card-frame.svg";
  import { ui } from "../lib/ui.svelte";
  import { SYMBOL_PAY_ART } from "../pixi/symbols";
  import { playPendingRestore } from "../game/betMachine.svelte";

  const FLIGHT_MS = 900;
  const REVEAL_MS = 600;
  let closing = $state(false);
  let introLogo = $state<HTMLImageElement>();
  let ghost: HTMLImageElement | undefined;
  let flight: Animation | undefined;
  let revealTimer: ReturnType<typeof setTimeout> | undefined;
  let disposed = false;

  async function dismiss() {
    if (!ui.introOpen || closing || !introLogo) return;
    const target = document.querySelector<HTMLImageElement>("#slotLogo");
    const start = introLogo.getBoundingClientRect();
    const end = target?.getBoundingClientRect();
    closing = true;
    ui.introTransitioning = true;

    if (end && start.width && start.height) {
      ghost = introLogo.cloneNode(true) as HTMLImageElement;
      ghost.className = "";
      ghost.setAttribute("aria-hidden", "true");
      Object.assign(ghost.style, {
        display: "block",
        position: "fixed",
        left: `${start.left}px`,
        top: `${start.top}px`,
        width: `${start.width}px`,
        height: `${start.height}px`,
        margin: "0",
        maxWidth: "none",
        zIndex: "300",
        pointerEvents: "none",
        transformOrigin: "top left",
        filter: "drop-shadow(0 6px 24px rgba(10, 4, 16, 0.85))",
      });
      document.body.appendChild(ghost);
      flight = ghost.animate(
        [
          { transform: "translate(0, 0) scale(1)" },
          {
            transform: `translate(${end.left - start.left}px, ${end.top - start.top}px) scale(${end.width / start.width}, ${end.height / start.height})`,
          },
        ],
        { duration: FLIGHT_MS, easing: "cubic-bezier(.22, 1, .36, 1)", fill: "forwards" },
      );
      try {
        await flight.finished;
      } catch {
        if (disposed) return;
      }
    }

    if (disposed) return;
    ui.introOpen = false;
    ui.introTransitioning = false;
    revealTimer = setTimeout(() => {
      ghost?.remove();
      ghost = undefined;
      void playPendingRestore();
    }, REVEAL_MS);
  }

  function onKey(event: KeyboardEvent) {
    if (!ui.introOpen) return;
    if (event.code === "Space" || event.code === "Enter" || event.code === "NumpadEnter" || event.code === "Escape") {
      event.preventDefault();
      void dismiss();
    }
  }

  onMount(() => window.addEventListener("keydown", onKey));
  onDestroy(() => {
    disposed = true;
    window.removeEventListener("keydown", onKey);
    if (revealTimer !== undefined) clearTimeout(revealTimer);
    flight?.cancel();
    ghost?.remove();
  });
</script>

{#if ui.introOpen}
  <div class="intro" class:closing role="button" tabindex="0" aria-label="Press to continue" onclick={() => void dismiss()} onkeydown={onKey} data-intro="1" style={`--frame: url("${cardFrame}")`}>
    <img class="logo" bind:this={introLogo} src={titleLogo} alt="Sunset Stereo" />
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
        <img class="max-logo" src={maxWinLogo} alt="Max Win" />
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
    pointer-events: none;
  }
  .intro.closing .logo {
    visibility: hidden;
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
    min-height: clamp(230px, 42vh, 355px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: clamp(32px, 4vh, 40px) clamp(26px, 2.6vw, 38px);
    text-align: center;
    background: var(--frame) center / 100% 100% no-repeat;
    filter: drop-shadow(0 14px 22px rgba(6, 2, 14, 0.8));
    animation: card-in 0.55s ease-out both;
  }
  .card:nth-child(2) {
    animation-delay: 0.12s;
  }
  .card:nth-child(3) {
    animation-delay: 0.24s;
  }
  .card.center {
    scale: 1.06;
    filter: drop-shadow(0 14px 24px rgba(6, 2, 14, 0.85)) drop-shadow(0 0 13px rgba(255, 154, 61, 0.45));
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
  .max-logo {
    display: block;
    width: 100%;
    height: auto;
    filter: drop-shadow(0 3px 7px rgba(4, 2, 10, 0.8));
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
      gap: 8px;
    }
    .card {
      width: min(340px, 92vw);
      max-width: none;
      min-height: 0;
      padding: 22px 30px;
      gap: 6px;
    }
    .card.center {
      scale: 1;
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
    .max-logo {
      max-width: 220px;
    }
    .logo {
      width: min(46vw, 260px);
    }
  }
</style>
