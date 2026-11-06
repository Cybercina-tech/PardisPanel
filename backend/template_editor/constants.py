"""
Usage types for template-based price banner rendering.
Used to select the appropriate theme from config.usage_theme_map.
"""

# Usage type when rendering a category price board (e.g. GBP)
CATEGORY_BOARD = "category_board"

# Usage type when rendering a tether/USDT category board
TETHER_BOARD = "tether_board"

# Usage type when rendering a special offer board (generic)
SPECIAL_OFFER = "special_offer"

# Optional: more specific special offer types for different themes
SPECIAL_BUY = "special_buy"
SPECIAL_SELL = "special_sell"

ALL_USAGE_TYPES = (
    CATEGORY_BOARD,
    TETHER_BOARD,
    SPECIAL_OFFER,
    SPECIAL_BUY,
    SPECIAL_SELL,
)
