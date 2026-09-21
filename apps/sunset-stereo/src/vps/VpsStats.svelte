<script lang="ts">
  import { onMount } from "svelte";
  import { moneyHud } from "../lib/ui.svelte";
  import {
    applyVpsRound,
    chartPoints,
    emptyVpsStats,
    loadVpsStats,
    saveVpsStats,
    vpsNet,
    vpsRtp,
  } from "./stats.js";

  const CHART_W = 220;
  const CHART_H = 72;
  let open = $state(true);
  let stats = $state(emptyVpsStats());

  const rtp = $derived(vpsRtp(stats));
  const net = $derived(vpsNet(stats));
  const chart = $derived(chartPoints(stats.history, CHART_W, CHART_H));
  const zeroY = $derived.by(() => {
    if (!stats.history.length) return CHART_H / 2;
    const span = chart.max - chart.min;
    if (!span) return CHART_H / 2;
    return 8 + ((chart.max - 0) / span) * (CHART_H - 16);
  });

  function persist() {
    saveVpsStats(window.localStorage, stats);
  }

  onMount(() => {
    stats = loadVpsStats(window.localStorage);
    const onRound = (event: Event) => {
      const detail = (event as CustomEvent<{ spentMicro?: number; wonMicro?: number }>).detail;
      if (!detail) return;
      stats = applyVpsRound(stats, detail.spentMicro ?? 0, detail.wonMicro ?? 0);
      persist();
    };
    window.addEventListener("vps-stats-round", onRound);
    return () => window.removeEventListener("vps-stats-round", onRound);
  });

  function reset() {
    stats = emptyVpsStats();
    persist();
  }
</script>

<aside class="panel" class:open data-vps-stats="1">
  <button type="button" class="tab" aria-expanded={open} onclick={() => (open = !open)}>
    Stats
  </button>
  {#if open}
    <div class="body">
      <p class="kicker">VPS session</p>
      <dl>
        <div>
          <dt>Spent</dt>
          <dd id="vpsSpentValue">{moneyHud(stats.spentMicro)}</dd>
        </div>
        <div>
          <dt>Won</dt>
          <dd id="vpsWonValue">{moneyHud(stats.wonMicro)}</dd>
        </div>
        <div>
          <dt>Net</dt>
          <dd id="vpsNetValue" class:up={net > 0} class:down={net < 0}>{moneyHud(net)}</dd>
        </div>
        <div>
          <dt>RTP</dt>
          <dd id="vpsRtpValue">{stats.spentMicro ? `${(rtp * 100).toFixed(1)}%` : "—"}</dd>
        </div>
      </dl>
      <p class="spins">{stats.spins} {stats.spins === 1 ? "spin" : "spins"}</p>
      <svg
        id="vpsStatsChart"
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        width="100%"
        height={CHART_H}
        aria-label="Cumulative net graph"
      >
        <line class="axis" x1="8" y1={zeroY} x2={CHART_W - 8} y2={zeroY} />
        {#if chart.points}
          <polyline class="line" points={chart.points} />
        {/if}
      </svg>
      <button id="vpsStatsReset" type="button" onclick={reset}>Reset</button>
    </div>
  {/if}
</aside>

<style>
  .panel {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 70;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    pointer-events: none;
  }
  .tab,
  .body button {
    pointer-events: auto;
    border: 0;
    cursor: pointer;
  }
  .tab {
    min-height: 32px;
    padding: 0 12px;
    border-radius: 999px;
    background: rgba(20, 10, 8, 0.82);
    color: #f4efe6;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-size: 11px;
  }
  .body {
    pointer-events: auto;
    width: min(260px, calc(100vw - 24px));
    padding: 12px 14px 12px;
    border-radius: 14px;
    background: rgba(16, 10, 8, 0.9);
    color: #f4efe6;
    box-shadow: 0 12px 28px rgba(8, 2, 16, 0.45);
  }
  .kicker {
    margin: 0 0 8px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-size: 10px;
    color: #cbbba8;
  }
  dl {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 12px;
    margin: 0;
  }
  dt {
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #cbbba8;
  }
  dd {
    margin: 2px 0 0;
    font-variant-numeric: tabular-nums;
    font-size: 16px;
  }
  dd.up {
    color: #5ee0a0;
  }
  dd.down {
    color: #ff8a7a;
  }
  .spins {
    margin: 10px 0 8px;
    font-size: 11px;
    color: #cbbba8;
  }
  svg {
    display: block;
    margin: 0 0 10px;
  }
  .axis {
    stroke: rgba(244, 239, 230, 0.2);
    stroke-width: 1;
  }
  .line {
    fill: none;
    stroke: #3ec8f0;
    stroke-width: 2;
    stroke-linejoin: round;
    stroke-linecap: round;
  }
  .body button {
    width: 100%;
    min-height: 32px;
    border-radius: 8px;
    background: #2a2118;
    color: #f4efe6;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-size: 11px;
  }
</style>
