# Sunset Stereo

Слот для [Stake Engine](https://engine.io/docs): 5 барабанов, 3 ряда, 20 линий.

Тема — закат и стерео. Математика собрана по официальному Math SDK, события раунда — в формате RGS `book.events`, который ест Web SDK.

## Механика

| | |
| --- | --- |
| Сетка | 5×3, 20 фиксированных линий |
| RTP | 96% |
| Максимум | 5000× |
| Buy bonus | 80× ставка |

**База.** Wild (микшер) подменяет платящие символы. Scatter (солнце) на всех барабанах. 3 / 4 / 5 скаттеров открывают Golden Hour: 10 / 14 / 18 спинов.

**Golden Hour.** Отдельный рилсет с более частыми wild и хай-символами. Wild несут аддитивные множители линии. **Stereo Mix** — глобальный множитель: стартует с 1× и растёт на +1 после каждого выигрышного фриспина. На фронт уходит стандартный `updateGlobalMult`.

Рериггер только от 3+ скаттеров (4 / 6 / 10 спинов).

## Структура

```
games/sunset_stereo/   Math SDK: config, state, reels
apps/sunset-stereo/    Web SDK-style player: Svelte 5 + PixiJS 8 + XState
src/                   Движок Stake Engine Math SDK (MIT)
```

Полный дамп документации Engine для нейросети: [`docs/ENGINE_DOCUMENTATION.md`](docs/ENGINE_DOCUMENTATION.md).

Оригинал: [engine.io/docs](https://engine.io/docs) (Math, Frontend, RGS, Approval guidelines).

## Математика

Нужен Python 3.12+.

```bash
make setup
make run GAME=sunset_stereo
```

`run.py` пишет books, lookup tables и конфиги в `games/sunset_stereo/library/`. Для прод-симов подними `num_sim_args` и включи `run_optimization`.

Пересобрать барабаны:

```bash
make reels
```

## Фронтенд

Плеер собран по схеме Stake Engine Web SDK:

`book → bookEvents → playBookEvent → bookEventHandlerMap → emitterEvents / Pixi board`

Стек: Svelte 5, PixiJS 8, XState. Символы рисуются на canvas, HUD — credit / stake / spin / extra plays.

```bash
make frontend
```

Открой `http://localhost:4173`. Space — спин. Extra plays — вход в Golden Hour за 80×.

Сборка статики:

```bash
make frontend-build
```

Артефакт: `apps/sunset-stereo/dist`. Docker: `apps/sunset-stereo/Dockerfile`.

Для публикации на Stake скопируй `apps/lines` из [web-sdk](https://github.com/StakeEngine/web-sdk) и перенеси `apps/sunset-stereo/src/game` плюс Pixi-борд.

## Символы

| Код | Тема |
| --- | --- |
| H1 | Vinyl |
| H2 | Headphones |
| H3 | Cassette |
| H4 | Microphone |
| L1 | Speaker |
| L2 | Note |
| L3 | EQ |
| L4 | Palm |
| L5 | Neon cocktail |
| W | Mixer / wild |
| S | Sunset / scatter |
