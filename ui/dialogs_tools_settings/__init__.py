"""Settings dialog (package facade).

Split (SOLID/SRP) without breaking the public contract: `SettingsDialog`
is still importable from `ui.dialogs_tools_settings`.
"""

from ui.dialogs_tools_settings.dialog import SettingsDialog

__all__ = ["SettingsDialog"]
