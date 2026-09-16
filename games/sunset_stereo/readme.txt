Sunset Stereo
=============

PRODUCTION math package for Stake Engine.

6-reel, 4-row, left-to-right ways. 3 scatters start 10 hold-and-respin
extra plays. 4 scatters do the same and place a locking wild before
each extra play. Scatter lands on reels 2–5 only.

Modes
-----
base        cost 1.0     1,000,000 books   high vol, 25% hit rate
scatter     cost 1.5     1,000,000 books   medium vol, sun locked on reel 2
bonus       cost 95.0      250,000 books   medium vol 3-scatter buy, min 3×
wildbonus   cost 225.0     250,000 books   high vol 4-scatter buy, min 5×

Natural bonuses (base / ante) pay at least 10×. Buy bonuses never pay 0.
Every board is drawn independently — zero spins are not cloned, and the
same payout uses different symbols.

Target RTP
----------
95.00% on every mode, within 0.5% of each other. LUT weights spread RTP
across hit-rate ranges instead of parking it in one 200–500× pocket.
Win cap 15000×.

Generate
--------
python3 games/sunset_stereo/run.py
# or one mode:
SUNSET_SIM_MODE=base python3 games/sunset_stereo/run.py
SUNSET_SIM_MODE=scatter python3 games/sunset_stereo/run.py
SUNSET_SIM_MODE=bonus python3 games/sunset_stereo/run.py
SUNSET_SIM_MODE=wildbonus python3 games/sunset_stereo/run.py
python3 games/sunset_stereo/copy_publish.py
