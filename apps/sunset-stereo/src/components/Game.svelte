<script lang="ts">
  import { onMount } from "svelte";
  import { Application } from "pixi.js";
  import { createBoard } from "../pixi/board";
  import { loadSymbolArt } from "../pixi/symbols";
  import { setContext, runtime } from "../game/context";
  import { moneyHud, ui } from "../lib/ui.svelte";

  setContext();

  let host: HTMLDivElement;
  let app: Application | null = null;

  onMount(() => {
    let disposed = false;
    let stopLayout: (() => void) | undefined;

    const boot = async () => {
      if (!host) return;
      await loadSymbolArt();
      if (disposed) return;
      const pixi = new Application();
      await pixi.init({
        backgroundAlpha: 0,
        antialias: true,
        autoDensity: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
        resizeTo: host,
      });
      if (disposed) {
        pixi.destroy(true);
        return;
      }
      host.appendChild(pixi.canvas);
      runtime.board = createBoard(pixi);
      app = pixi;
      const layout = () => runtime.board?.resize(pixi.screen.width, pixi.screen.height);
      pixi.resize();
      layout();
      pixi.renderer.on("resize", layout);
      const ro = new ResizeObserver(() => pixi.resize());
      ro.observe(host);
      stopLayout = () => {
        ro.disconnect();
        pixi.renderer.off("resize", layout);
      };
    };

    void boot();

    return () => {
      disposed = true;
      stopLayout?.();
      app?.destroy(true);
      runtime.board = null;
    };
  });
</script>

<div class="viewport" bind:this={host}>
  {#if ui.spinWinVisible && ui.spinWinMicro > 0}
    {#key ui.spinWinKey}
      <div class="spin-win" class:feature={ui.feature}>
        <p id="spinWinOverlay" class="amount">{moneyHud(ui.spinWinMicro)}</p>
        {#if ui.spinWinLines > 0}
          <p id="spinWinWays" class="ways">
            {ui.spinWinLines} {ui.spinWinLines === 1 ? "LINE" : "LINES"}
          </p>
        {/if}
      </div>
    {/key}
  {/if}
</div>

<style>
  .viewport {
    position: relative;
    width: 100%;
    height: min(620px, 78vw);
    min-height: 400px;
    background: transparent;
    overflow: hidden;
  }
  .viewport :global(canvas) {
    display: block;
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    background: transparent;
  }
  .spin-win {
    position: absolute;
    inset: 0;
    z-index: 4;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin: 0;
    pointer-events: none;
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    color: #ffd060;
  }
  .amount {
    margin: 0;
    font-weight: 800;
    font-size: clamp(52px, 11vw, 96px);
    letter-spacing: 0.03em;
    line-height: 1;
    text-shadow:
      0 0 10px #ff9a28,
      0 0 28px rgba(255, 140, 32, 0.75),
      0 3px 0 #7a2a08,
      0 8px 22px rgba(8, 2, 16, 0.9);
    animation: spin-win-pop 0.38s cubic-bezier(0.18, 0.9, 0.28, 1.15);
  }
  .ways {
    margin: 12px 0 0;
    font-weight: 800;
    font-size: clamp(18px, 3.4vw, 28px);
    letter-spacing: 0.16em;
    line-height: 1;
    text-shadow:
      0 0 8px #ff9a28,
      0 2px 0 #7a2a08,
      0 6px 16px rgba(8, 2, 16, 0.85);
    animation: ways-drop 0.48s cubic-bezier(0.18, 0.82, 0.22, 1) 0.34s both;
  }
  .spin-win.feature .amount,
  .spin-win.feature .ways {
    color: #ffc070;
    text-shadow:
      0 0 12px #ff6a20,
      0 0 32px rgba(255, 90, 40, 0.8),
      0 3px 0 #6a1808,
      0 8px 22px rgba(8, 2, 16, 0.9);
  }
  @keyframes spin-win-pop {
    from {
      transform: scale(0.62);
      opacity: 0;
    }
    to {
      transform: scale(1);
      opacity: 1;
    }
  }
  @keyframes ways-drop {
    from {
      transform: translateY(-40px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }
</style>
