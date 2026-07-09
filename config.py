"""Configuration and the SOXX + SMH ticker universe.

The app tries to fetch live ETF holdings from Finnhub at startup. If that
endpoint is premium-gated (common on the free tier), it falls back to this
seed list, which is the union of SOXX and SMH constituents as of mid-2026.
Company names are used only for display and for the filter list.
"""

import os

FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "").strip()

# Poll windows are 08:00 and 13:00 Europe/London.
SCHEDULE_HOURS = [8, 13]
TIMEZONE = "Europe/London"

# How many days of history to keep / show.
LOOKBACK_DAYS = 7

# The two ETFs whose holdings define the tracked universe.
ETFS = ["SOXX", "SMH"]

# Fallback seed: union of SOXX (iShares) + SMH (VanEck) holdings.
# ticker -> display name
SEED_UNIVERSE = {
    "NVDA": "NVIDIA Corp",
    "AMD": "Advanced Micro Devices",
    "AVGO": "Broadcom Inc",
    "MU": "Micron Technology",
    "INTC": "Intel Corp",
    "TSM": "Taiwan Semiconductor (ADR)",
    "QCOM": "Qualcomm Inc",
    "TXN": "Texas Instruments",
    "AMAT": "Applied Materials",
    "LRCX": "Lam Research",
    "KLAC": "KLA Corp",
    "ADI": "Analog Devices",
    "MRVL": "Marvell Technology",
    "NXPI": "NXP Semiconductors",
    "MCHP": "Microchip Technology",
    "MPWR": "Monolithic Power Systems",
    "ON": "ON Semiconductor",
    "STM": "STMicroelectronics",
    "ASML": "ASML Holding",
    "TER": "Teradyne",
    "ENTG": "Entegris",
    "SWKS": "Skyworks Solutions",
    "QRVO": "Qorvo Inc",
    "LSCC": "Lattice Semiconductor",
    "COHR": "Coherent Corp",
    "GFS": "GlobalFoundries",
    "ARM": "Arm Holdings",
    "AMKR": "Amkor Technology",
    "ALGM": "Allegro MicroSystems",
    "RMBS": "Rambus Inc",
}

DB_PATH = os.environ.get("SEMIDASH_DB", os.path.join(os.path.dirname(__file__), "semidash.db"))
