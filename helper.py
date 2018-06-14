#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper functions."""

import random
import asyncio

__all__ = ["wait_between"]


async def wait_between(a, b):
    length = random.uniform(a, b)
    await asyncio.sleep(length / 1000)
    return length
