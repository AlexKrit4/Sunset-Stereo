import {
  roundModeFlags,
  roundStakeAmount,
  stakeFromAuthenticate,
  winMicroForStake,
} from "../src/rgs/roundStake.js";

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

const RUB_1 = 1_000_000;
const RUB_100 = 100_000_000;
const bonusBookCents = 12_500; // 125×

const authDefault = {
  config: { defaultBetLevel: RUB_100, betLevels: [RUB_1, 2_000_000, RUB_100] },
  round: null,
};
assert(stakeFromAuthenticate(authDefault) === RUB_100, "idle session uses defaultBetLevel");

const authActiveBonus = {
  config: { defaultBetLevel: RUB_100, betLevels: [RUB_1, 2_000_000, RUB_100] },
  round: { active: true, amount: RUB_1, mode: "bonus", payoutMultiplier: 125 },
};
assert(stakeFromAuthenticate(authActiveBonus) === RUB_1, "active round restores Play amount, not defaultBetLevel");
assert(roundStakeAmount(authActiveBonus.round) === RUB_1, "round.amount is the Play base bet");
assert(roundModeFlags(authActiveBonus.round.mode).wildBonus === false, "bonus buy is not wildbonus");
assert(roundModeFlags(authActiveBonus.round.mode).scatterBuyOn === false, "bonus buy is not scatter extra");

const countedOnDefault = winMicroForStake(bonusBookCents, RUB_100);
const countedOnPlay = winMicroForStake(bonusBookCents, RUB_1);
const rgsPayout = Math.round((125) * RUB_1);
assert(countedOnPlay === rgsPayout, "displayed win matches RGS payoutMultiplier × original Play amount");
assert(countedOnDefault === rgsPayout * 100, "counting on defaultBetLevel would show 100× the paid win");
assert(countedOnPlay === 125 * RUB_1, "125× of 1 is 125, not 12500");

const authCompleted = {
  config: { defaultBetLevel: RUB_100, betLevels: [RUB_1, RUB_100] },
  round: { active: false, amount: RUB_1, mode: "bonus" },
};
assert(stakeFromAuthenticate(authCompleted) === RUB_100, "completed round does not override the default stake");

const authMissingAmount = {
  config: { defaultBetLevel: RUB_100, betLevels: [RUB_1] },
  round: { active: true, mode: "base" },
};
assert(stakeFromAuthenticate(authMissingAmount) === RUB_100, "active round without amount keeps defaultBetLevel");

assert(roundModeFlags("scatter").scatterBuyOn, "scatter extra-bet restores HUD cost");
assert(roundModeFlags("wildbonus").wildBonus, "4-scatter buy restores wild bonus flag");
assert(roundModeFlags("BASE").scatterBuyOn === false && roundModeFlags("BASE").wildBonus === false, "mode is case-insensitive");

console.log("smoke-round-stake ok");
