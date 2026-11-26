import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # aiogram дуже детально логує HTTP-запити; залишаємо тільки попередження
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)