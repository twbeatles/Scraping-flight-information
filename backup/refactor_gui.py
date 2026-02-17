
import os

gui_path = r"d:\google antigravity\Scraping-flight-information-main\gui_v2.py"
refactored_path = r"d:\google antigravity\Scraping-flight-information-main\gui_v2.py"
backup_path = r"d:\google antigravity\Scraping-flight-information-main\gui_v2.py.bak"

# Imports to insert
new_imports = """
# --- Styling ---
from ui.styles import DARK_THEME, LIGHT_THEME
from ui.components import (
    NoWheelSpinBox, NoWheelComboBox, NoWheelDateEdit, NoWheelTabWidget,
    FilterPanel, ResultTable, LogViewer, SearchPanel
)
from ui.workers import SearchWorker, MultiSearchWorker, DateRangeWorker
from ui.dialogs import (
    CalendarViewDialog, CombinationSelectorDialog, MultiDestDialog,
    MultiDestResultDialog, DateRangeDialog, DateRangeResultDialog,
    ShortcutsDialog, PriceAlertDialog, SettingsDialog
)

# 기본 테마 (호환성)
MODERN_THEME = DARK_THEME

"""

try:
    with open(gui_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Backup
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    # Construct new content
    # Python slices are 0-based.
    # Line 1 is index 0.
    # We want lines 1-50 -> index 0-50 (exclusive 50? No, 0-49 is 50 lines. slice [0:50])
    part1 = lines[0:50]
    
    # SessionManager: Line 1162 starts it. Index 1161.
    # Ends before Line 1219 (CalendarViewDialog). Index 1218.
    # So slice [1161:1219]
    part2 = lines[1161:1219]
    
    # MainWindow: Line 3386 starts it (# --- Main Window ---). Index 3385.
    # To end.
    part3 = lines[3385:]
    
    with open(refactored_path, 'w', encoding='utf-8') as f:
        f.writelines(part1)
        f.write(new_imports)
        f.writelines(part2)
        f.write("\n") # Ensure separation
        f.writelines(part3)
        
    print("Refactoring successful!")

except Exception as e:
    print(f"Error: {e}")
