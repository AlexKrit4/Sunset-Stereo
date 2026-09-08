"""Hold-respin book events for extra plays."""


def hold_respin_event(gamestate, positions: set[tuple[int, int]], continuing: bool = True) -> None:
    """Lock current winning cells before an extra-play respin."""
    padded = [{"reel": reel, "row": row + 1} for reel, row in sorted(positions)]
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": "holdRespin",
            "positions": padded,
            "continuing": continuing,
        }
    )
