<script lang="ts">
  import { onMount } from "svelte";
  import { Application } from "pixi.js";
  import { createBoard } from "../pixi/board";
  import { setContext, runtime } from "../game/context";

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

<div class="viewport" bind:this={host}></div>

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
</style>
