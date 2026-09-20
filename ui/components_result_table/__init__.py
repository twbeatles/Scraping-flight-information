"""Flight result table (package facade).

Split (SOLID/SRP) without breaking the public contract: `ResultTable`
is still importable from `ui.components_result_table`.
"""

from ui.components_result_table.table import ResultTable

__all__ = ["ResultTable"]
