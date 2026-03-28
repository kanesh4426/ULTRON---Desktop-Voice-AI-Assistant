from typing import Callable, Iterable


class StreamHandler:
    def __init__(self, on_token: Callable[[str], None]):
        self.on_token = on_token

    def consume(self, token_stream: Iterable[str]) -> None:
        for token in token_stream:
            self.on_token(token)

