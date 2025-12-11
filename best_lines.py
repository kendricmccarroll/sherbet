import requests
import json
import argparse
import os
import sys

# ====================================================================
# CONFIGURATION CONSTANTS
# ====================================================================
CACHE_FILE = "arb_data_cache.json"
KEY_FILE = "my_key.txt"

# --- SPORT CONFIGURATION ---
SPORT_CONFIG = {
    # Format: "User_Name": ("API_Key", "Emoji_Icon")
    "nfl": ("americanfootball_nfl", "🏈"),
    "nba": ("basketball_nba", "🏀"),
    "mlb": ("baseball_mlb", "⚾️"),
    "nhl": ("icehockey_nhl", "🏒"),
    "ncaaf": ("americanfootball_ncaaf", "📣 🏈"),
    "ncaab": ("basketball_ncaab", "📣 🏀"),
    "epl": ("soccer_epl", "⚽️")
}
SUPPORTED_SPORTS = list(SPORT_CONFIG.keys())

# Core markets to fetch in a single API call
FEATURED_MARKETS = {
    "h2h": "Moneyline (Winner)",
    "spreads": "Point Spread",
    "totals": "Game Total O/U"
}
# ====================================================================


class BestOddsFinder:
    def __init__(self, api_key, sport_key, sport_emoji):
        self.api_key = api_key
        self.sport_key = sport_key
        self.sport_emoji = sport_emoji
        self.base_odds_url = f"https://api.the-odds-api.com/v4/sports/{self.sport_key}/odds"

    def _get_api_response(self, url, params):
        """Internal function to handle API calls and error checking."""
        params.update({"apiKey": self.api_key, "regions": "us", "oddsFormat": "decimal"})
        
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            
            print("="*50)
            print(f"!!! API REQUEST FAILED - CODE {response.status_code} for {self.sport_key.upper()} !!!")
            print(f"Response Body: {response.text[:100]}...")
            print("="*50)
            return None
        
        except requests.exceptions.RequestException as e:
            print(f"\n!!! NETWORK ERROR: Could not connect to API for {self.sport_key}: {e}")
            return None

    def fetch_or_load_data(self, force_new_call):
        """Loads data from cache or fetches new data from API."""
        sport_cache_file = f"{self.sport_key}_{CACHE_FILE}" 

        if os.path.exists(sport_cache_file) and not force_new_call:
            print(f"{self.sport_emoji} Loading data for {self.sport_key.upper()} from local cache: {sport_cache_file}")
            try:
                with open(sport_cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading cache file {sport_cache_file}. Forcing new call.")
                force_new_call = True

        if force_new_call:
            print(f"⚡️ Fetching NEW data for {self.sport_key.upper()} from API...")
            params = {"markets": ",".join(FEATURED_MARKETS.keys())}
            
            data = self._get_api_response(self.base_odds_url, params=params)
            
            if data:
                with open(sport_cache_file, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"💾 Data saved to cache: {sport_cache_file}")
            
            return data
        
        return None 

    def find_best_odds(self, market_data):
        """Finds the single highest odds for each opposing outcome across all books."""
        best_outcome_a = {"price": 0, "book": "", "name": ""}
        best_outcome_b = {"price": 0, "book": "", "name": ""}

        outcome_names = set()
        for book in market_data['bookmakers']:
            for market in book['markets']:
                for outcome in market['outcomes']:
                    outcome_names.add(outcome['name'])
        
        if len(outcome_names) != 2: return None, None 

        name_a, name_b = sorted(list(outcome_names)) 

        for book in market_data['bookmakers']:
            for market in book['markets']:
                for outcome in market['outcomes']:
                    price = outcome['price']
                    
                    if outcome['name'] == name_a and price > best_outcome_a['price']:
                        best_outcome_a.update({"price": price, "book": book['title'], "name": name_a})
                    
                    elif outcome['name'] == name_b and price > best_outcome_b['price']:
                        best_outcome_b.update({"price": price, "book": book['title'], "name": name_b})

        return best_outcome_a, best_outcome_b

    # --- SIMPLIFIED SCAN METHOD ---
    def scan_game_markets(self, game, markets):
        """Processes all requested markets for a single game and collects best odds."""
        game_results = {
            "game": f"{game['away_team']} @ {game['home_team']}",
            "markets": {}
        }
        
        for market_key, market_name in markets.items():
            market_data = {'bookmakers': []}
            
            for book in game['bookmakers']:
                market_entry = next((m for m in book['markets'] if m['key'] == market_key), None)
                if market_entry:
                    market_data['bookmakers'].append({
                        'title': book['title'],
                        'markets': [market_entry]
                    })
            
            if not market_data['bookmakers']:
                continue

            best_a, best_b = self.find_best_odds(market_data)
            
            if not best_a or not best_b or best_a['price'] == 0:
                continue

            # Instead of storing arb result, we just store the best odds found
            game_results["markets"][market_name] = {
                "best_a": best_a,
                "best_b": best_b,
                # Arbitrage calculation is skipped entirely
            }
        
        return game_results

    # --- SIMPLIFIED RUN METHOD ---
    def run_scanner(self, args):
        """Main method to run the scanner and print best odds."""
        
        game_data = self.fetch_or_load_data(args.newcall)
        
        if not game_data:
            print(f"Scanner stopped for {self.sport_key.upper()}. No game data available.")
            return

        print(f"\n======== {self.sport_emoji} BEST ODDS FOUND FOR {self.sport_key.upper()} ========")

        for game in game_data:
            game_result = self.scan_game_markets(game, FEATURED_MARKETS)
            
            if not game_result["markets"]:
                continue
            
            # Print Game Header
            print("\n" + "—"*50)
            print(f"{self.sport_emoji} GAME: {game_result['game']}")
            print("—"*50)
            
            for market_name, data in game_result["markets"].items():
                best_a = data["best_a"]
                best_b = data["best_b"]
                
                print(f"\n--- Market: {market_name} ---")
                
                # --- CORE OUTPUT: BEST ODDS FOR EACH OUTCOME ---
                print(f"  -> {best_a['name']}: **{best_a['book']}** @ {best_a['price']:.3f}")
                print(f"  -> {best_b['name']}: **{best_b['book']}** @ {best_b['price']:.3f}")


# --- EXECUTION / ENTRY POINT ---
def load_api_key(filename):
    if not os.path.exists(filename):
        print(f"Fatal Error: API key file '{filename}' not found.")
        sys.exit(1)
    try:
        with open(filename, 'r') as f:
            key = f.read().strip()
            if not key: sys.exit(1)
            return key
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-League Best Odds Finder (Stripped Down Version).",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    sport_list_help = "Specify one or more sports to scan.\n" + \
                      "Supported values:\n" + \
                      "\n".join(f"  - {s} (e.g., nfl, nba)" for s in SUPPORTED_SPORTS)
                      
    parser.add_argument(
        '--sports',
        nargs='+',
        required=True,
        choices=SUPPORTED_SPORTS,
        help=sport_list_help
    )
    parser.add_argument(
        '--newcall', 
        action='store_true', 
        help='Force a new API call for ALL configured leagues and overwrite the cache files.'
    )
    # The --arb-only argument is removed as arbitrage is no longer calculated
    args = parser.parse_args()

    YOUR_API_KEY = load_api_key(KEY_FILE)
    
    # Total Budget is no longer needed but kept for completeness if you decide to re-add arb
    GAME_BUDGET = 500
    
    for sport_alias in args.sports:
        if sport_alias in SPORT_CONFIG:
            api_key, emoji = SPORT_CONFIG[sport_alias]
            
            print("\n" + "*"*80)
            print(f"*** {emoji} STARTING BEST ODDS SCAN FOR LEAGUE: {sport_alias.upper()} ***")
            print("*"*80)
            
            # Class name changed to reflect new focus
            bot = BestOddsFinder(YOUR_API_KEY, api_key, emoji)
            bot.run_scanner(args)
        else:
<<<<<<< HEAD
            print(f"Warning: Sport alias '{sport_alias}' not recognized and will be skipped.")
=======
            print(f"Warning: Sport alias '{sport_alias}' not recognized and will be skipped.")
>>>>>>> 461e9c0 (reinit)
