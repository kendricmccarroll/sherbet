
# 📈 Best Odds Finder: Multi-League Betting Line Scanner

This Python script is a streamlined command-line tool designed to quickly scan odds data from The Odds API and identify the **single best price** available across all tracked sportsbooks for the Moneyline, Point Spread, and Game Total markets for any given match.

It uses local caching to save API usage and supports scanning multiple leagues in one call.

## ⚙️ Prerequisites

You must have the following installed and set up:

1.  **Python 3:** The script requires Python 3.6 or newer.
2.  **Required Libraries:** The script relies on the `requests` library for API calls.
3.  **The Odds API Key:** An active API key from [The Odds API](https://the-odds-api.com/).

## 💾 Setup and Installation

### Step 1: Clone or Download the Script

Place the `best_lines.py` file in a dedicated project directory.

### Step 2: Install Python Dependencies

Open your terminal or command prompt in the project directory and run:

python3 -m pip install requests


### Step 3: Configure Your API Key

The script loads your API key from a plain text file for security.

1.  Create a new file named exactly `my_key.txt` in the same directory as the script.

2.  Paste your API key into this file on a single line.

    ***`my_key.txt` Example:***

    ```text
    a1b2c3d4e5f6g7h8i9j0k_examplekey
    ```

## ▶️ How to Run the Script

The script uses the `python3` command followed by the filename and the required `--sports` argument.

### Core Command Syntax

```bash
python3 prop_arb_scanner.py --sports <SPORT_ALIAS> [optional_arguments]
```

-----

### Supported Sport Aliases

Use these aliases with the `--sports` argument:

| Sport Key | Alias | API Key Used | Emoji |
| :--- | :--- | :--- | :--- |
| National Football League | `nfl` | `americanfootball_nfl` | 🏈 |
| National Basketball Association | `nba` | `basketball_nba` | 🏀 |
| Major League Baseball | `mlb` | `baseball_mlb` | ⚾️ |
| National Hockey League | `nhl` | `icehockey_nhl` | 🏒 |
| College Football | `ncaaf` | `americanfootball_ncaaf` | 📣 |
| College Basketball | `ncaab` | `basketball_ncaab` | 📣 |
| English Premier League | `epl` | `soccer_epl` | ⚽️ |

### Optional Arguments

| Argument | Description | Effect on Execution |
| :--- | :--- | :--- |
| `--sports <list>` | **Required.** Specifies one or more sport aliases to run. | e.g., `--sports nfl nba` |
| `--newcall` | Optional. Forces a fresh API request for the specified sports. | **Consumes API Credits.** Overwrites local cache. |

### Example Usage

| Goal | Command to Run |
| :--- | :--- |
| **Get best odds for NFL and NBA (using cached data)** | `python3 best_lines.py --sports nfl nba` |
| **Refresh data and get best odds for MLB and NHL** | `python3 best_lines.py --sports mlb nhl --newcall` |
| **Get best odds for all major US leagues** | `python3 best_lines.py --sports nfl nba mlb nhl` |

## 📊 Sample Output

The output is formatted for clarity, listing the best odds and the specific sportsbook that offers them for each market:

```
********************************************************************************
*** 🏈 STARTING BEST ODDS SCAN FOR LEAGUE: NFL ***
********************************************************************************
✅ Loading data for AMERICANFOOTBALL_NFL from local cache: americanfootball_nfl_arb_data_cache.json

======== 🏈 BEST ODDS FOUND FOR AMERICANFOOTBALL_NFL ========

——————————
🏈 GAME: Dallas Cowboys @ Philadelphia Eagles
——————————

--- Market: Moneyline (Winner) ---
  -> Dallas Cowboys: **Bet365** @ 2.100
  -> Philadelphia Eagles: **FanDuel** @ 1.850

--- Market: Point Spread ---
  -> Dallas Cowboys: **DraftKings** @ 1.950
  -> Philadelphia Eagles: **BetMGM** @ 2.050

--- Market: Game Total O/U ---
  -> Over: **Caesars** @ 2.020
  -> Under: **WynnBet** @ 2.020
```

## 🛠️ Data & Markets

  * **API Used:** The Odds API - `/v4/sports/{sport_key}/odds` endpoint.
  * **Region:** United States (`regions=us`).
  * **Odds Format:** Decimal (`oddsFormat=decimal`).
  * **Markets Checked (Core Featured):**
      * `h2h` (Moneyline)
      * `spreads` (Point Spread)
      * `totals` (Game Total O/U)

The script is currently configured for a **Best Odds Finder** experience and has removed the original arbitrage calculation logic.

```
```
