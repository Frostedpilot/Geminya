#!/usr/bin/env python3
"""Processors package for multi-media integration.

This package contains the base processor class and specific implementations
for different media sources (MAL, VNDB, manual data, etc.).
"""

from .base_processor import BaseProcessor

__all__ = ["BaseProcessor"]