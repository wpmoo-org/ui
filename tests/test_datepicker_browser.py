from __future__ import annotations

import unittest

from playwright.sync_api import expect as _expect_marker

from tests.test_datepicker import _DatepickerBrowserMixin


class DatepickerBrowserTests(_DatepickerBrowserMixin, unittest.TestCase):
    pass


__all__ = ["DatepickerBrowserTests"]
