from typing import Iterable


def stream_tokens(text: str) -> Iterable[str]:
    for token in text.split(" "):
        if token:
            yield token + " "

