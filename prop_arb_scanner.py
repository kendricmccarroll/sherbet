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

# --- UPDATED SPORT CONFIGURATION ---
# Use this dictionary to map user-friendly names to API keys and emojis
SPORT_CONFIG = {
    # Format: "User_Name": ("API_Key", "Emoji_Icon")
    "nfl": ("americanfootball_nfl", "🏈"),
    "nba": ("basketball_nba", "🏀"),
    "mlb": ("baseball_mlb", "⚾️"),
    "nhl": ("icehockey_nhl", "🏒"),
    "ncaaf": ("americanfootball_ncaaf", "📣"),
    "ncaab": ("basketball_ncaab", "📣"),
    "epl": ("soccer_epl", "⚽️")
}

# Supported leagues for the command line help message
SUPPORTED_SPORTS = list(SPORT_CONFIG.keys())

# Core markets (Moneyline, Spread, Totals) to fetch in a single API call
FEATURED_MARKETS = {
    # "h2h": "Moneyline (Winner)",
    # "spreads": "Point Spread",
    "totals": "Game Total O/U"
}
# ====================================================================


class ArbScanner:
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
            
            # --- API FAILURE PRINT ---
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
        
        # Unique cache key for each sport
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
            # --- API CALL ---
            print(f"⚡️ Fetching NEW data for {self.sport_key.upper()} from API...")
            params = {"markets": ",".join(FEATURED_MARKETS.keys())}
            
            data = self._get_api_response(self.base_odds_url, params=params)
            
            if data:
                with open(sport_cache_file, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"💾 Data saved to cache: {sport_cache_file}")
            
            return data
        
        return None 

    def calculate_stakes(self, total_budget, odds_a, odds_b):
        """Calculates arbitrage opportunity and profit."""
        if odds_a <= 1 or odds_b <= 1: return None 
        
        prob_a = 1 / odds_a
        prob_b = 1 / odds_b
        total_prob = prob_a + prob_b
        
        if total_prob >= 1:
            return None # No arbitrage possible

        # Optimal stake calculation
        stake_a = (total_budget * prob_a) / total_prob
        stake_b = (total_budget * prob_b) / total_prob
        
        profit = (stake_a * odds_a) - total_budget 
        roi = (profit / total_budget) * 100
        
        return {
            "stake_a": round(stake_a, 2),
            "stake_b": round(stake_b, 2),
            "profit": round(profit, 2),
            "roi": round(roi, 2)
        }

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

    def scan_game_markets(self, game, markets, total_budget):
        """Processes all requested markets for a single game and collects results."""
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

            arb_result = self.calculate_stakes(total_budget, best_a['price'], best_b['price'])

            game_results["markets"][market_name] = {
                "best_a": best_a,
                "best_b": best_b,
                "arb": arb_result
            }
        
        return game_results

    def run_scanner(self, args, total_budget):
        """Main method to run the scanner for the specified sport."""
        
        game_data = self.fetch_or_load_data(args.newcall)
        
        if not game_data:
            print(f"Scanner stopped for {self.sport_key.upper()}. No game data available.")
            return

        all_game_results = []
        for game in game_data:
            results = self.scan_game_markets(game, FEATURED_MARKETS, total_budget)
            if results["markets"]:
                all_game_results.append(results)

        # Sort by best arbitrage opportunity
        def sort_key(item):
            arb_found = 0
            min_prob = 2.0 
            for market in item["markets"].values():
                if market["arb"]:
                    arb_found = 1
                    prob = (1 / market["best_a"]["price"]) + (1 / market["best_b"]["price"]) 
                    if prob < min_prob:
                        min_prob = prob
            return (-arb_found, min_prob)

        all_game_results.sort(key=sort_key)
        
        # --- FINAL PRINTING OF FILTERED RESULTS ---
        found_any_arb = False
        
        print(f"\n======== {self.sport_emoji} ARBITRAGE RESULTS FOR {self.sport_key.upper()} (Budget: ${total_budget:.2f} per opportunity) ========")

        for game_result in all_game_results:
            game_has_arb = any(data["arb"] is not None for data in game_result["markets"].values())
            
            if args.arb_only and not game_has_arb:
                continue 

            print("\n" + "—"*50)
            print(f"{self.sport_emoji} GAME: {game_result['game']}")
            print("—"*50)
            
            for market_name, data in game_result["markets"].items():
                arb = data["arb"]
                
                if args.arb_only and not arb:
                    continue

                found_any_arb = True
                best_a = data["best_a"]
                best_b = data["best_b"]
                
                print(f"\n--- Market: {market_name} ---")
                
                print(f"  -> {best_a['name']}: {best_a['book']} @ {best_a['price']:.3f}")
                print(f"  -> {best_b['name']}: {best_b['book']} @ {best_b['price']:.3f}")

                if arb:
                    print("  🚨 ARBITRAGE OPPORTUNITY FOUND 🚨")
                    print(f"  - **{best_a['book']} ({best_a['name']}):** Stake ${arb['stake_a']:.2f}")
                    print(f"  - **{best_b['book']} ({best_b['name']}):** Stake ${arb['stake_b']:.2f}")
                    print(f"  - **GUARANTEED PROFIT:** ${arb['profit']:.2f} ({arb['roi']:.2f}%)")
        
        if not all_game_results:
            print(f"\nNo games or valid markets found for {self.sport_key.upper()}.")
        elif args.arb_only and not found_any_arb:
            print(f"\nNo arbitrage opportunities were found in the data for {self.sport_key.upper()}.")


# --- EXECUTION / ENTRY POINT ---
def load_api_key(filename):
    if not os.path.exists(filename):
        print(f"Fatal Error: API key file '{filename}' not found.")
        print("Please create this file and paste your API key inside.")
        sys.exit(1)
    try:
        with open(filename, 'r') as f:
            key = f.read().strip()
            if not key:
                 print(f"Fatal Error: API key file '{filename}' is empty.")
                 sys.exit(1)
            return key
    except Exception as e:
        print(f"Fatal Error reading key file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-League Arbitrage Scanner with Caching and Filtering.",
        formatter_class=argparse.RawTextHelpFormatter # Allows newline formatting for the sports list
    )
    
    # New argument to select sports
    sport_list_help = "Specify one or more sports to scan.\n" + \
                      "Supported values:\n" + \
                      "\n".join(f"  - {s} (e.g., nfl, nba)" for s in SUPPORTED_SPORTS)
                      
    parser.add_argument(
        '--sports',
        nargs='+',  # This allows one or more arguments to be passed
        required=True,
        choices=SUPPORTED_SPORTS,
        help=sport_list_help
    )
    parser.add_argument(
        '--newcall', 
        action='store_true', 
        help='Force a new API call for ALL configured leagues and overwrite the cache files.'
    )
    parser.add_argument(
        '--arb-only',
        action='store_true',
        help='Only show markets and games that contain a guaranteed arbitrage opportunity.'
    )
    args = parser.parse_args()

    YOUR_API_KEY = load_api_key(KEY_FILE)
    GAME_BUDGET = 500
    
    # Loop only through the sports specified in the command line argument
    for sport_alias in args.sports:
        if sport_alias in SPORT_CONFIG:
            api_key, emoji = SPORT_CONFIG[sport_alias]
            
            print("\n" + "*"*80)
            print(f"*** {emoji} STARTING SCAN FOR LEAGUE: {sport_alias.upper()} ({api_key}) ***")
            print("*"*80)
            
            bot = ArbScanner(YOUR_API_KEY, api_key, emoji)
            bot.run_scanner(args, GAME_BUDGET)
        else:
            # This should technically not be reached if 'choices' is used correctly, but good for robustness
            print(f"Warning: Sport alias '{sport_alias}' not recognized and will be skipped.")
