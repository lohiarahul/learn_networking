"""Batch 11 -- Application Layer."""

from prims import *  # noqa: F401,F403

import os
OUT = os.environ.get("ILLO_OUT", "../11-application-layer")


def http_exchange():
    """A request and its response, each split by a blank line into headers and body."""
    body = [
        card(30, 40, 110, 160, bar=False),
        line(30, 96, 140, 96, stroke=DARK, dash="4 3"),
        pill(42, 54, 78, 7, MID), pill(42, 68, 60, 7, MID), pill(42, 82, 70, 7, MID),
        pill(42, 112, 86, 7, TINT), pill(42, 128, 70, 7, TINT),
        card(180, 40, 110, 160, bar=False),
        line(180, 96, 290, 96, stroke=DARK, dash="4 3"),
        pill(192, 54, 78, 7, PRIM), pill(192, 68, 60, 7, MID), pill(192, 82, 40, 7, MID),
        pill(192, 112, 86, 7, TINT), pill(192, 128, 86, 7, TINT), pill(192, 144, 50, 7, TINT),
        arrow(140, 70, 180, 70, stroke=MID, head=6),
        arrow(180, 170, 140, 170, stroke=PRIM, head=6),
    ]
    return body, "A request and its response, each split by a blank line into headers and body"


TOPICS = [
    ("http-exchange", http_exchange),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
