"""MMV Reporting Tools.

Composable report-generation primitives for the MMV real estate
underwriting platform.  Each module in this package exposes a single
public ``generate_*`` function that accepts structured underwriting
output and returns a rendered document (Markdown, Excel, etc.).
"""

from mmv_reporting.tools.markdown_report import generate_report

__all__ = ["generate_report"]
