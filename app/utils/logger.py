import logging
import os
from pathlib import Path

class LazyDirectoryFileHandler(logging.FileHandler):
    def _open(self):
        Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
        return super()._open()


def get_logger(name: str, log_file: str = "data/logs/assistant.log") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    fh = LazyDirectoryFileHandler(log_file, encoding="utf-8", delay=True)
    sh = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger
