from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NewsItem:
    source: str
    title: str
    url: str
    content: str = ""
    published_at: str = ""
    stock_code: str = ""
    stock_name: str = ""
    category: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.published_at:
            self.published_at = datetime.now().isoformat()


class BaseCollector(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def collect(self) -> list[NewsItem]:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass
