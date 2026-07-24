# Portfolio Summary

## Project Name

Macro-Financial Risk & Market Behaviour Analytics Platform

## Short Description

A Python/MySQL analytics platform designed to study multi-asset market behaviour, technical indicators, volatility, anomaly signals, macro-financial context and historical/news events.

The project combines market data, technical analysis, risk heuristics, macroeconomic datasets and event enrichment to support exploratory financial risk analysis.

---

# 1. Project Objective

The main objective of this project is to build a structured analytical framework capable of studying how different markets behave across different regimes.

The project aims to analyze:

- crypto markets;
- equity indices;
- currencies;
- commodities;
- macroeconomic indicators;
- historical events;
- news-driven market context;
- potential abnormal market behaviour.

The long-term goal is to evolve the platform into a broader market intelligence system with intermarket analysis, Streamlit dashboards and machine learning-based anomaly/regime detection.

---

# 2. Assets Covered

The current version covers the following assets:

```text
Bitcoin
SP500
STOXX600
FTSE100
Gold
DXY / US Dollar Index
Euro
Chinese Yuan
British Pound
SSE Composite

Each asset has its own SQL table, technical indicator pipeline and Plotly dashboard.


3. Current Technical Stack

The project currently uses:

Python
Pandas
NumPy
MySQL
SQLAlchemy
mysql-connector-python
Plotly
Requests
Power BI

Planned future tools include:

Streamlit
Scikit-learn
Machine Learning models
Intermarket analytics
4. Current Features

The current system includes:

CSV data ingestion;
MySQL storage;
multi-asset processing;
synthetic OHLC construction;
technical indicator calculation;
anomaly/risk signal detection;
Plotly dashboards;
Power BI reporting table;
historical event enrichment;
news data ingestion;
documentation and methodology files.
5. Technical Indicators

The project calculates several technical indicators, including:

RSI
Stochastic RSI
EMA 9
EMA 12
EMA 26
EMA 50
EMA 100
EMA 200
Bollinger Bands
MACD
MACD Signal
MACD Percent
Momentum
ATR
ADX
CCI
OBV

Additional behavioural indicators include:

volume_zscore
realized_volatility_30d
volatility_of_volatility
liquidity_stress
drawdown_duration
market_entropy
6. Risk and Anomaly Detection

The current risk detection layer uses heuristic rules to identify possible abnormal market behaviour.

Signals include:

Pump/Dump-like movement
Spoofing-like abnormal volume
RSI extreme context
ATR high-volatility context

These signals are not interpreted as proof of manipulation. They are used as exploratory risk flags to identify periods that deserve further investigation.

7. Data Architecture

The project uses a MySQL database called:

btc_data

Despite the original name, the database now stores broader multi-asset and macro-financial data.

The database includes:

market asset tables;
Power BI reporting tables;
historical event tables;
news tables;
FED macroeconomic tables;
EU/ECB macroeconomic tables.
8. Visualization

The current visualization layer uses Plotly to generate TradingView-style dashboards.

Each asset dashboard includes:

price/candlestick chart;
moving averages;
Bollinger Bands;
volume;
RSI and Stochastic RSI;
MACD;
anomaly/risk markers.

Future visualization work will focus on Streamlit.

9. Current Project Status

Current version:

v0.2.1 — Multi-Asset Script Stabilization

Current status:

10 assets functional
core indicator logic modularized
risk detection modularized
chart generation modularized
asset configuration prepared
documentation improved
generic asset processor planned
Streamlit not yet implemented
ML not yet implemented
10. Future Roadmap

Planned improvements include:

generic asset_processor.py;
reduced script duplication;
standardized macro data processing;
Streamlit interface;
intermarket correlation analysis;
rolling risk regime analysis;
event impact analysis;
news/event overlays;
machine learning anomaly detection;
regime classification;
feature importance analysis;
improved GitHub presentation.
11. Portfolio Value

This project demonstrates practical skills in:

data cleaning;
data engineering;
SQL database design;
financial data analysis;
technical indicators;
anomaly detection logic;
dashboarding;
Python automation;
modular code organization;
analytical documentation;
risk-oriented thinking;
business intelligence preparation.

It is especially relevant for roles involving:

Data Analysis
Business Intelligence
Risk Analytics
Financial Analysis
Fraud/Risk Detection
Operations Analytics
Compliance Analytics
Data-driven decision support
12. One-Paragraph CV Version

Developed a Python/MySQL multi-asset analytics platform to analyze financial market behaviour across crypto, equity indices, currencies and commodities. The project includes CSV ingestion, SQL storage, technical indicator calculation, anomaly/risk signal detection, Plotly dashboards, historical/news event enrichment and Power BI reporting preparation. Current work focuses on modularizing the architecture, preparing Streamlit dashboards and developing future intermarket and machine learning-based risk analysis.

13. LinkedIn Version

I am currently developing a macro-financial analytics platform using Python, MySQL and Plotly to study multi-asset market behaviour across Bitcoin, equity indices, currencies and commodities.

The project combines technical indicators, volatility metrics, anomaly/risk detection heuristics, historical events, news data and macro-financial datasets to explore how markets behave under different regimes.

The current version includes multi-asset dashboards, SQL-based data storage, risk signal logic and documentation for future Streamlit and machine learning development.

14. Disclaimer

This project is for educational, analytical and portfolio purposes only.

It does not provide financial advice.

The anomaly and manipulation-related signals are heuristic risk indicators and should not be interpreted as definitive evidence of market manipulation or unlawful activity.
