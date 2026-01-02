# ✈️ Flight Bot V2.3 - Pro

Flight Bot is a powerful, modern desktop application for real-time flight search and comparison using **Playwright** and **PyQt6**. It supports both domestic and international flights with advanced features like batch search, Excel export, and price history tracking.

## ✨ Key Features

### 🔍 Search Capabilities
- **Real-time Scraping:** Fetches live data from Interpark Tours (and extensible to others).
- **Domestic & International:** Optimized logic for both flight types.
    - *Domestic:* Smart scraping with outbound/return flight matching.
    - *International:* Comprehensive round-trip search.
- **Batch Search:** Import search conditions from Excel to search multiple routes/dates at once.
- **Flight Types:** Round-trip and One-way support.

### 📊 Data Management
- **Excel/CSV Export:** Right-click on results to export data with detailed price breakdowns.
- **Input Persistence:** Automatically saves and restores your last search settings (Origin, Dest, Dates, Passengers).
- **Price History:** Tracks price trends for specific routes over time.
- **Favorites:** Save interesting flights to watch later.

### 🎨 Modern UI/UX
- **Dark Theme:** Sleek, eye-friendly design.
- **Interactive Tables:** Sortable columns, adjustable widths, and color-coded prices.
- **Split Price Display:** clearly shows `Total (Outbound + Return)` prices.
- **Log Viewer:** Real-time status updates within the app.

## 🛠️ Installation

1. **Prerequisites**
   - Python 3.9+
   - Chrome/Chromium browser

2. **Install Dependencies**
   ```bash
   pip install PyQt6 playwright openpyxl matplotlib
   playwright install
   ```

## 🚀 Usage

1. **Run the Application**
   ```bash
   python gui_v2.py
   ```

2. **Search**
   - Select Origin/Destination, Dates, and Passengers.
   - Click **Search**.

3. **Export & Manage**
   - **Right-click** on any result row to copy info or export to Excel/CSV.
   - Go to **Settings > Data** to import batch search conditions.

## 📁 Project Structure

- `gui_v2.py`: Main application entry point and GUI implementation.
- `scraper_v2.py`: Core scraping logic using Playwright.
- `database.py`: SQLite database manager for history and favorites.
- `config.py`: Configuration settings (Airports, Airlines, etc.).

## 📦 Building (PyInstaller)

To create a standalone executable:

```bash
pyinstaller flight_bot.spec
```

The output will be in the `dist` folder.

## 📝 License
MIT License
