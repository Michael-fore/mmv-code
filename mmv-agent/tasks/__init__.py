"""MMV Agent Tasks — discrete units of work the agent executor can dispatch.

Each module in this package exposes a ``run()`` function that performs a
self-contained task (data fetch, analysis step, report generation) and
persists its output to a well-known location.
"""
