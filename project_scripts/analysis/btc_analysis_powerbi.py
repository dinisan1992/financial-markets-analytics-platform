from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# =====================================================
# ⚙️ 1. DATABASE CONNECTION
# =====================================================
DB_URL = get_sqlalchemy_database_url()
engine = create_engine(DB_URL)

# =====================================================
# 🧩 2. READ MYSQL TABLES
# =====================================================
btc_df = pd.read_sql("SELECT * FROM btc_analysis", engine)
btc_events = pd.read_sql("SELECT * FROM bitcoin_historical_events", engine)
world_events = pd.read_sql("SELECT * FROM world_historical_events", engine)

btc_df['snapped_at'] = pd.to_datetime(btc_df['snapped_at'])
btc_df['year'] = btc_df['snapped_at'].dt.year
btc_events['event_date'] = pd.to_datetime(btc_events['event_date'], errors='coerce')
world_events['year'] = world_events['year'].astype(int)

# =====================================================
# 🧮 3. CALCULATE FINANCIAL METRICS
# =====================================================
btc_df = btc_df.sort_values(by="snapped_at").reset_index(drop=True)

# --- Returns percentuais ---
btc_df['return_1d'] = btc_df['price'].pct_change(1) * 100
btc_df['return_7d'] = btc_df['price'].pct_change(7) * 100
btc_df['return_30d'] = btc_df['price'].pct_change(30) * 100
btc_df['return_60d'] = btc_df['price'].pct_change(60) * 100
btc_df['return_90d'] = btc_df['price'].pct_change(90) * 100
btc_df['return_360d'] = btc_df['price'].pct_change(360) * 100

# --- Volatilidade e drawdown ---
btc_df['rolling_volatility_30d'] = btc_df['price'].pct_change().rolling(30).std() * np.sqrt(30) * 100
btc_df['rolling_max'] = btc_df['price'].cummax()
btc_df['drawdown_pct'] = ((btc_df['price'] - btc_df['rolling_max']) / btc_df['rolling_max']) * 100
btc_df['max_drawdown_pct'] = btc_df['drawdown_pct'].expanding().min()

# --- Trend and volatility ---
btc_df['price_vs_ema_200'] = (btc_df['price'] / btc_df['ema_200'] - 1) * 100
btc_df['volatility_flag'] = btc_df['rolling_volatility_30d'] > btc_df['rolling_volatility_30d'].mean() * 2

# --- Market Cap ajustado ---
btc_df['market_cap_adj'] = (
    (btc_df['market_cap'] - btc_df['market_cap'].min()) /
    (btc_df['market_cap'].max() - btc_df['market_cap'].min())
)

# --- Logarithmic price ---
btc_df['price_usd_log'] = np.log(btc_df['price'])

# --- Trend strength index (RSI + ADX) ---
btc_df['trend_strength_index'] = (btc_df['adx'] / 50) + (btc_df['rsi'] / 100)

# =====================================================
# 📊 4. SHARPE, SORTINO, CAGR
# =====================================================
eps = 1e-9
btc_df['daily_return'] = btc_df['price'].pct_change()

for window in [30, 90, 360]:
    mean_ret = btc_df['daily_return'].rolling(window).mean()
    std_ret = btc_df['daily_return'].rolling(window).std()
    btc_df[f'sharpe_ratio_{window}d'] = (mean_ret / (std_ret + eps)) * np.sqrt(365)

    # Sortino Ratio
    negative_ret = btc_df['daily_return'].copy()
    negative_ret[negative_ret > 0] = 0
    std_neg = negative_ret.rolling(window).std()
    btc_df[f'sortino_ratio_{window}d'] = (mean_ret / (std_neg + eps)) * np.sqrt(365)

# CAGR
btc_df['days_since_start'] = (btc_df['snapped_at'] - btc_df['snapped_at'].iloc[0]).dt.days
btc_df['cagr'] = ((btc_df['price'] / btc_df['price'].iloc[0]) ** (1 / (btc_df['days_since_start'] / 365 + eps)) - 1) * 100

# --- Turnover Ratio ---
btc_df['turnover_ratio'] = (
    btc_df['total_volume'].rolling(30).mean() /
    btc_df['market_cap'].replace(0, np.nan)
)
btc_df['turnover_ratio'] = btc_df['turnover_ratio'].fillna(0)

# =====================================================
# 🌍 5. CROSS EVENTS WITH DAILY IMPACT (MAIN CHANGE)
# =====================================================

# Inicializar columns de events e impacto como None/NaN
for col in [
    'btc_event_flag', 'btc_event_title', 'btc_event_impact', 'btc_event_category',
    'impact_score_market_adj', 'world_event_flag', 'world_event_title',
    'world_event_impact', 'affected_markets', 'impact_score_world_adj'
]:
    btc_df[col] = None

# --- Eventos BTC (por data) ---
for _, event in btc_events.iterrows():
    event_date = event['event_date']
    if pd.isna(event_date):
        continue

    # Filtrar o dia do evento
    mask = btc_df['snapped_at'] == event_date
    if mask.sum() == 0:
        continue

    # Calculate daily impact for that day
    avg_change = btc_df.loc[mask, 'return_1d'].values[0]  # return do dia do evento
    vol = btc_df.loc[mask, 'rolling_volatility_30d'].values[0]
    market_adj = btc_df.loc[mask, 'market_cap_adj'].values[0]

    impact_score = (avg_change / (vol + 1e-6)) * market_adj
    impact_score = np.clip(impact_score, -100, 100)

    # Preencher columns naquele dia
    btc_df.loc[mask, ['btc_event_flag', 'btc_event_title', 'btc_event_impact', 'btc_event_category', 'impact_score_market_adj']] = [
        True, event['event_title'], event['impact'], event['category'], impact_score
    ]

# --- World Events (by year; adjust it if specific dates are required) ---
for _, event in world_events.iterrows():
    year = event['year']

    # Filtrar os dias daquele ano
    mask = btc_df['year'] == year
    if mask.sum() == 0:
        continue

    # For daily impact, assign each day of that year the impact calculated on that day
    # Aqui, vou calcular por dia:
    # Average do return_1d por dia para esses dias (in practice it is the day's own value)
    # It is already at daily level, so apply the formula row by row.

    # Apply formula row by row:
    def calc_impact(row):
        avg_change = row['return_1d']
        vol = row['rolling_volatility_30d']
        market_adj = row['market_cap_adj']
        impact = (avg_change / (vol + 1e-6)) * market_adj
        return np.clip(impact, -100, 100)

    btc_df.loc[mask, 'impact_score_world_adj'] = btc_df.loc[mask].apply(calc_impact, axis=1)
    btc_df.loc[mask, ['world_event_flag', 'world_event_title', 'world_event_impact', 'affected_markets']] = [
        True, event['event'], event['macro_impact'], event['affected_markets']
    ]

# --- Automatic impact type (positive/negative) ---
btc_df['impact_type_market'] = np.where(
    btc_df['impact_score_market_adj'].astype(float) > 0, 'Positive',
    np.where(btc_df['impact_score_market_adj'].astype(float) < 0, 'Negative', 'Neutral')
)
btc_df['impact_type_world'] = np.where(
    btc_df['impact_score_world_adj'].astype(float) > 0, 'Positive',
    np.where(btc_df['impact_score_world_adj'].astype(float) < 0, 'Negative', 'Neutral')
)

# =====================================================
# ⚠️ 6. RISK REGIME
# =====================================================
btc_df['risk_regime'] = np.select(
    [
        (btc_df['rolling_volatility_30d'] > btc_df['rolling_volatility_30d'].mean() * 1.5),
        (btc_df['drawdown_pct'] < -30),
    ],
    ['High Volatility', 'Bearish Regime'],
    default='Stable'
)

# =====================================================
# 📦 7. EXPORT TO POWER BI
# =====================================================
cols_final = [
    'snapped_at', 'price', 'market_cap', 'total_volume', 'price_change_pct', 'manipulation',
    'rsi', 'ema_9', 'ema_12', 'ema_26', 'ema_50', 'ema_100', 'ema_200', 'volume_sma_9',
    'bb_middle', 'bb_upper', 'bb_lower', 'stoch_rsi', 'macd', 'macd_signal', 'macd_percent',
    'momentum_10', 'atr', 'adx', 'cci', 'obv',
    'return_1d', 'return_7d', 'return_30d', 'return_60d', 'return_90d', 'return_360d',
    'rolling_volatility_30d', 'drawdown_pct', 'max_drawdown_pct',
    'sharpe_ratio_30d', 'sharpe_ratio_90d', 'sharpe_ratio_360d',
    'sortino_ratio_30d', 'sortino_ratio_90d', 'sortino_ratio_360d',
    'turnover_ratio', 'price_vs_ema_200', 'volatility_flag',
    'market_cap_adj', 'impact_score_market_adj', 'impact_score_world_adj',
    'btc_event_flag', 'btc_event_title', 'btc_event_impact', 'btc_event_category',
    'world_event_flag', 'world_event_title', 'world_event_impact', 'affected_markets',
    'price_usd_log', 'trend_strength_index', 'cagr',
    'impact_type_market', 'impact_type_world', 'risk_regime'
]

final_df = btc_df[[c for c in cols_final if c in btc_df.columns]].copy()
final_df = final_df.rename(columns={'snapped_at': 'date'})
final_df['market'] = 'BTC'

print("🛠️ Creating table btc_analysis_powerbi in MySQL...")
final_df.to_sql(
    'btc_analysis_powerbi',
    con=engine,
    if_exists='replace',
    index=False,
    chunksize=1000,
    method='multi'
)
print(f"✅ Table btc_analysis_powerbi created with {len(final_df)} records, including new risk indices, CAGR, Sortino Ratio and impact classifications.")

