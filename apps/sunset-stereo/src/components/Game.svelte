<script lang="ts">
  import { onMount } from "svelte";
  import { Application } from "pixi.js";
  import { createBoard } from "../pixi/board";
  import { setContext, runtime } from "../game/context";
  import { ui } from "../lib/ui.svelte";

  setContext();

  let host: HTMLDivElement;
  let app: Application | null = null;

  onMount(() => {
    let disposed = false;
    let stopLayout: (() => void) | undefined;

    const boot = async () => {
      if (!host) return;
      const pixi = new Application();
      await pixi.init({
        background: 0x1c140c,
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
      const layout = () => runtime.board?.resize(host.clientWidth, host.clientHeight);
      layout();
      window.addEventListener("resize", layout);
      stopLayout = () => window.removeEventListener("resize", layout);
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

<div class="viewport" class:feature={ui.feature} bind:this={host}>
  {#if ui.feature}
    <div class="plate">
      <span>Golden Hour {ui.fsCurrent}/{ui.fsTotal}</span>
      <strong>Mix ×{ui.mix}</strong>
    </div>
  {/if}
</div>

<style>
  .viewport {
    position: relative;
    width: 100%;
    height: min(520px, 62vw);
    min-height: 340px;
    background: #1c140c;
    overflow: hidden;
  }
  .viewport.feature {
    background: #24160c;
  }
  .viewport :global(canvas) {
    display: block;
    width: 100%;
    height: 100%;
  }
  .plate {
    position: absolute;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 2;
    display: flex;
    gap: 18px;
    align-items: baseline;
    padding: 6px 14px;
    background: #2a1c12;
    border: 1px solid #c4a574;
    color: #f0dcc4;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 13px;
    pointer-events: none;
  }
  .plate strong {
    font-variant-numeric: tabular-nums;
  }
</style>
