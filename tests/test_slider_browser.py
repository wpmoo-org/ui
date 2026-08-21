from __future__ import annotations

import unittest

from playwright.sync_api import expect as _expect_marker

from tests.test_slider import _SliderBrowserMixin


class SliderBrowserTests(_SliderBrowserMixin, unittest.TestCase):
    pass


__all__ = ["SliderBrowserTests"]
