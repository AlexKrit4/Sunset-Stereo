# Sunset Stereo

Слот для [Stake Engine](https://engine.io/docs). **Прод: 6 барабанов × 4 ряда, ways.**

Тема — закат и стерео. Математика — официальный Math SDK. События раунда — RGS `book.events`.

Старый пакет **5×3 / 20 линий / Golden Hour** выключен: [`games/_inactive_sunset_stereo_5x3/`](games/_inactive_sunset_stereo_5x3/), DOM-плеер — [`frontend/INACTIVE.md`](frontend/INACTIVE.md).

## Механика (прод)

| | |
| --- | --- |
| Сетка | **6×4**, left-to-right ways |
| RTP (цель) | 96% |
| Максимум | 55200× |
| Buy bonus | нет |
| Wilds / xWays / xNudge | не выпадают |
| Scatter | барабаны 2–5, не больше одного на барабан; только tease, **без фриспинов** |

**База.** Три и больше барабанов подряд. Солнце не открывает Golden Hour.

## Структура

```
games/sunset_stereo/              Math SDK 6×4 ways (прод)
games/_inactive_sunset_stereo_5x3/  выключенный 5×3 lines
apps/sunset-stereo/               Pixi-плеер 6×4 (прод)
frontend/                         выключенный 5×3 DOM-плеер
src/                              движок Stake Engine Math SDK
```

Документация Engine: [`docs/ENGINE_DOCUMENTATION.md`](docs/ENGINE_DOCUMENTATION.md).  
Разбор публикации: [`docs/STAKE_PUBLICATION_REVIEW.md`](docs/STAKE_PUBLICATION_REVIEW.md).

## Математика

Нужен Python 3.12+.

```bash
make setup
make run GAME=sunset_stereo
```

`run.py` пишет books в `games/sunset_stereo/library/`. Для Stake позже: больше симов и `run_optimization`.

Пересобрать барабаны:

```bash
make reels
```

## Фронтенд

Прод-плеер: Svelte 5 + PixiJS 8.

```bash
make frontend
```

Открой `http://localhost:4173`. Space — спин.

Сборка: `make frontend-build` → `apps/sunset-stereo/dist`.

## Символы

| Код | Тема |
| --- | --- |
| H1 / high1 | Vinyl |
| H2 / high2 | Headphones |
| H3 / high3 | Cassette |
| H4 / high4 | Microphone |
| H5 / high5 | Amp |
| L1 / low1 | Speaker |
| L2 / low2 | Note |
| L3 / low3 | EQ |
| L4 / low4 | Palm |
| L5 / low5 | Neon cocktail |
| S / scatter | Sunset (tease) |
