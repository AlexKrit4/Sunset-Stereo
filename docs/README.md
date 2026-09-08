# Docs for the next model

Read **[ENGINE_DOCUMENTATION.md](./ENGINE_DOCUMENTATION.md)** first.

Publication gap analysis vs that dump: **[STAKE_PUBLICATION_REVIEW.md](./STAKE_PUBLICATION_REVIEW.md)** (includes ACP steps for the 1000-book test upload).

Production game is **6×4 ways** (`games/sunset_stereo/`, `apps/sunset-stereo/`). The 5×3 lines + Golden Hour package is inactive.

It contains every public technical section from https://engine.io/docs:

- Math SDK (setup, quick start, game format, gamestate, source files, optimization, samples)
- Frontend SDK (getting started, file structure, events, Storybook, UI, context)
- RGS (play/wallet APIs and fifty-fifty example)
- Approval guidelines (replay, tiles, math verification, checklist, jurisdiction)

Part 1 is the live site text. Part 2 is the official Math SDK markdown with code blocks.

Do not fetch engine.io in a browser to continue implementation — this dump is the source of truth in-repo.
