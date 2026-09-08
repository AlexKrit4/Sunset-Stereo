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
| Scatter | барабаны 2–5, не больше одного на барабан |
| Бонус | 3 солнца → 10 экстра-спинов (hold + respin). База + бонус = одна ставка / одна книга |
| Шанс бонуса | ~1 к 150–180 (live p=0.12 ≈ 1/159) |

**База.** Три и больше барабанов подряд. Три солнца открывают 10 экстра-спинов.

**Экстра-спины.** Выигрыш сразу не платится: выигрышные ячейки держатся, остальные респинятся (респин не тратит один из 10). Новые ways, в том числе других символов, могут достроиться. Если респин не добавил новых выигрышных ячеек — этот экстра-спин заканчивается и тогда платится.

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
| S / scatter | Sunset (3 на барабанах 2–5 → 10 экстра-спинов) |
