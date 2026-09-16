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


def place_wild_event(gamestate, reel: int, row: int) -> None:
    """Camera wild for a 4-scatter extra play. Row is 0-based on the visible board."""
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": "placeWild",
            "reel": int(reel),
            "row": int(row) + 1,
        }
    )
