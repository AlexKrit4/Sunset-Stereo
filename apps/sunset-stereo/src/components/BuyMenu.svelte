<script lang="ts">
  import { BUY_BONUS, BUY_SCATTER } from "../math/config.js";
  import { labels, moneyHud, ui } from "../lib/ui.svelte";
  import { SYMBOL_PAY_ART } from "../pixi/symbols";

  let {
    onBuyBonus,
  }: {
    onBuyBonus: () => void;
  } = $props();

  const bonusPrice = $derived(Math.round(ui.betMicro * BUY_BONUS.cost));
  const scatterPrice = $derived(Math.round(ui.betMicro * BUY_SCATTER.cost));
  const sunArt = SYMBOL_PAY_ART.scatter;

  function close() {
    ui.buyMenuOpen = false;
    ui.scatterConfirmOpen = false;
  }

  function requestScatter() {
    if (ui.busy) return;
    if (ui.scatterBuyOn) {
      ui.scatterBuyOn = false;
      ui.scatterConfirmOpen = false;
      return;
    }
    if (ui.balanceMicro < scatterPrice) return;
    ui.scatterConfirmOpen = true;
  }

  function confirmScatter() {
    if (ui.busy || ui.balanceMicro < scatterPrice) return;
    ui.scatterBuyOn = true;
    ui.scatterConfirmOpen = false;
  }

  function cancelScatter() {
    ui.scatterConfirmOpen = false;
  }
</script>

{#if ui.buyMenuOpen}
  <div
    class="scrim"
    onclick={(event) => {
      if (event.currentTarget === event.target) close();
    }}
    role="presentation"
  >
    <div class="shop" role="dialog" aria-label={labels.buyBonus()} aria-modal="true">
      <button id="buyCloseBtn" class="close" type="button" aria-label="Close" onclick={close}>
        ×
      </button>

      <div class="grid">
        <article id="buyReel2Card" class="card" class:live={ui.scatterBuyOn}>
          <div class="art sun">
            <img src={sunArt} alt="" />
          </div>
          <div class="body">
            <p class="bolts" aria-hidden="true">⚡⚡</p>
            <h3>{BUY_SCATTER.label}</h3>
            <p class="price">{moneyHud(scatterPrice)}</p>
            <button
              id="buyReel2Btn"
              class="activate"
              class:on={ui.scatterBuyOn}
              type="button"
              disabled={ui.busy || (!ui.scatterBuyOn && ui.balanceMicro < scatterPrice)}
              aria-pressed={ui.scatterBuyOn}
              onclick={requestScatter}
            >
              {ui.scatterBuyOn ? labels.activated() : labels.activate()}
            </button>
          </div>
        </article>

        <article id="buyBonusCard" class="card">
          <div class="art bonus">
            <img src={sunArt} alt="" />
            <img src={sunArt} alt="" />
            <img src={sunArt} alt="" />
          </div>
          <div class="body">
            <p class="bolts" aria-hidden="true">⚡⚡⚡⚡</p>
            <h3>{BUY_BONUS.label}</h3>
            <p class="price">{moneyHud(bonusPrice)}</p>
            <button
              id="buyScatterBtn"
              class="purchase"
              type="button"
              disabled={ui.busy || ui.balanceMicro < bonusPrice}
              onclick={onBuyBonus}
            >
              {labels.buyNow()}
            </button>
          </div>
        </article>
      </div>
    </div>
  </div>
{/if}

{#if ui.scatterConfirmOpen}
  <div
    class="confirm-scrim"
    onclick={(event) => {
      if (event.currentTarget === event.target) cancelScatter();
    }}
    role="presentation"
  >
    <div class="confirm" role="dialog" aria-label="Confirm extra bet" aria-modal="true">
      <h2>Activate extra bet?</h2>
      <p>
        {BUY_SCATTER.label} costs {BUY_SCATTER.cost}× the stake ({moneyHud(scatterPrice)}) on every
        spin and always lands a sun on reel {BUY_SCATTER.reel}.
      </p>
      <div class="actions">
        <button id="scatterCancelBtn" class="ghost" type="button" onclick={cancelScatter}>
          {labels.cancel()}
        </button>
        <button id="scatterConfirmBtn" class="go" type="button" onclick={confirmScatter}>
          {labels.confirm()}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 42;
    background: rgba(10, 16, 28, 0.72);
    display: grid;
    place-items: center;
    padding: 28px 16px 110px;
  }
  .shop {
    position: relative;
    width: min(720px, 100%);
  }
  .close {
    position: fixed;
    top: 18px;
    right: 18px;
    z-index: 43;
    width: 48px;
    height: 48px;
    border: 0;
    border-radius: 14px;
    background: #14181f;
    color: #fff;
    font-size: 32px;
    line-height: 1;
    cursor: pointer;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
  }
  .grid {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 18px;
  }
  .card {
    width: min(220px, 100%);
    overflow: hidden;
    border-radius: 18px;
    background: #fff;
    color: #1b2430;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
  }
  .card.live {
    outline: 3px solid #2ee6a0;
    outline-offset: 2px;
  }
  .art {
    height: 118px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .art.sun {
    background:
      radial-gradient(circle at 50% 40%, rgba(255, 210, 80, 0.95), transparent 55%),
      linear-gradient(180deg, #ff8a2a 0%, #c43a7a 100%);
  }
  .art.bonus {
    background:
      radial-gradient(circle at 50% 30%, rgba(255, 240, 160, 0.85), transparent 50%),
      linear-gradient(180deg, #7a3cff 0%, #e23a8c 100%);
  }
  .art img {
    width: 72px;
    height: 72px;
    object-fit: contain;
    filter: drop-shadow(0 8px 12px rgba(20, 8, 28, 0.35));
  }
  .art.bonus img {
    width: 56px;
    height: 56px;
  }
  .body {
    padding: 10px 14px 14px;
    text-align: center;
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .bolts {
    margin: 0 0 2px;
    color: #3cc4ff;
    letter-spacing: -0.08em;
    font-size: 14px;
    line-height: 1;
  }
  h3 {
    margin: 0;
    font-size: 15px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .price {
    margin: 4px 0 10px;
    font-size: 28px;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
  }
  .activate,
  .purchase {
    width: 100%;
    min-height: 42px;
    border: 0;
    border-radius: 10px;
    font: inherit;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
  }
  .activate {
    background: #2ee6a0;
    color: #fff;
  }
  .activate.on {
    background: #1aae78;
  }
  .purchase {
    background: #3dc6f5;
    color: #fff;
  }
  .activate:disabled,
  .purchase:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .confirm-scrim {
    position: fixed;
    inset: 0;
    z-index: 60;
    background: rgba(8, 2, 16, 0.72);
    display: grid;
    place-items: center;
    padding: 24px;
  }
  .confirm {
    width: min(420px, 100%);
    padding: 24px;
    border-radius: 18px;
    background: #fff;
    color: #1b2430;
    font-family: ui-sans-serif, system-ui, sans-serif;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
  }
  .confirm h2 {
    margin: 0 0 10px;
    font-size: 22px;
  }
  .confirm p {
    margin: 0 0 18px;
    line-height: 1.45;
    font-size: 15px;
  }
  .actions {
    display: flex;
    gap: 10px;
  }
  .actions button {
    flex: 1;
    min-height: 46px;
    border: 0;
    border-radius: 10px;
    font: inherit;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    cursor: pointer;
  }
  .ghost {
    background: #e6e0d8;
    color: #1b2430;
  }
  .go {
    background: #2ee6a0;
    color: #fff;
  }
</style>
