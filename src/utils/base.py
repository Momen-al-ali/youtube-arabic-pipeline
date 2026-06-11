from abc import ABC, abstractmethod
from src.utils.logging_config import get_logger


class BaseExtractor(ABC):

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def extract(self) -> list[dict]:
        """
        Pull data from the source and return it as a list of dicts.
        """
        pass

    def run(self) -> list[dict]:
        self.logger.info("Starting extraction: %s", self.__class__.__name__)
        data = self.extract()
        self.logger.info(
            "Extraction complete: %s — %d records fetched",
            self.__class__.__name__,
            len(data),
        )
        return data