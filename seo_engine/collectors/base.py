# -*- coding: utf-8 -*-
"""Collector interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from seo_engine.models import CollectionBundle


class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> CollectionBundle:
        raise NotImplementedError
