import unittest
from unittest.mock import Mock, patch

import pandas as pd

from services import data_access_service


class DataAccessServiceTests(unittest.TestCase):
    def test_detect_column_is_case_insensitive(self):
        columns = ["Snapped_At", "Price", "Volume"]

        self.assertEqual(
            data_access_service.detect_column(columns, ["date", "snapped_at"]),
            "Snapped_At",
        )

    def test_load_asset_events_combines_and_deduplicates_sources(self):
        btc_events = pd.DataFrame(
            {
                "event_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
                "event_title": ["ETF approval", "ETF approval"],
                "event_category": ["BTC", "BTC"],
                "event_description": ["desc", "desc"],
                "event_source_table": ["bitcoin_historical_events", "bitcoin_historical_events"],
            }
        )
        world_events = pd.DataFrame(
            {
                "event_date": pd.to_datetime(["2023-01-01"]),
                "event_title": ["Macro shock"],
                "event_category": ["World"],
                "event_description": ["desc"],
                "event_source_table": ["world_historical_events"],
            }
        )

        def loader(table_name, start_date=None, end_date=None):
            if table_name == "bitcoin_historical_events":
                return btc_events
            return world_events

        result = data_access_service.load_asset_events(loader)

        self.assertEqual(len(result), 2)
        self.assertEqual(result["event_title"].tolist(), ["Macro shock", "ETF approval"])

    @patch("services.data_access_service.pd.read_sql")
    def test_load_asset_data_normalizes_date_and_close(self, read_sql):
        read_sql.return_value = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-01", None],
                "price": ["102.5", "100.0", "999.0"],
            }
        )

        result = data_access_service.load_asset_data(
            engine=object(),
            assets_config={"TEST": {"table_name": "test_prices"}},
            asset_key="TEST",
            get_table_columns_func=lambda table: ["date", "price"],
        )

        self.assertEqual(result["snapped_at"].tolist(), [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")])
        self.assertEqual(result["close"].tolist(), [100.0, 102.5])

    @patch("services.data_access_service.pd.read_sql")
    def test_load_asset_data_keeps_one_complete_row_per_timestamp(self, read_sql):
        read_sql.return_value = pd.DataFrame(
            {
                "snapped_at": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "price": [100.0, 100.0, 102.0],
                "open": [None, 99.0, 101.0],
                "high": [None, 101.0, 103.0],
                "low": [None, 98.0, 100.0],
                "close": [None, 100.0, 102.0],
            }
        )

        result = data_access_service.load_asset_data(
            engine=object(),
            assets_config={"TEST": {"table_name": "test_prices"}},
            asset_key="TEST",
            get_table_columns_func=lambda table: [
                "snapped_at",
                "price",
                "open",
                "high",
                "low",
                "close",
            ],
        )

        self.assertEqual(len(result), 2)
        self.assertTrue(result["snapped_at"].is_unique)
        self.assertEqual(result.iloc[0]["open"], 99.0)

    def test_market_observations_are_normalized_to_one_daily_key(self):
        frame = pd.DataFrame(
            {
                "snapped_at": [
                    "2024-01-01 00:00:00",
                    "2024-01-01 23:30:00",
                ],
                "price": [100.0, 101.0],
            }
        )

        result = data_access_service.deduplicate_market_observations(frame)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["snapped_at"], pd.Timestamp("2024-01-01"))
        self.assertEqual(result.iloc[0]["price"], 101.0)

    @patch("services.data_access_service.pd.read_sql")
    def test_load_world_historical_events_formats_expected_columns(self, read_sql):
        read_sql.return_value = pd.DataFrame(
            {
                "year": [2020, 2021],
                "event": ["Pandemic shock", "Inflation pressure"],
                "macro_impact": ["Risk-off", "Rates higher"],
                "affected_markets": ["Equities", "Bonds"],
            }
        )

        result = data_access_service.load_events_from_table(
            engine=object(),
            table_name="world_historical_events",
            start_date="2021-01-01",
            table_exists_func=lambda table: True,
            get_table_columns_func=lambda table: ["year", "event", "macro_impact", "affected_markets"],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["event_date"], pd.Timestamp("2021-01-01"))
        self.assertEqual(result.iloc[0]["event_source_table"], "world_historical_events")
        self.assertEqual(result.iloc[0]["date_precision"], "year")

    def test_macro_pair_loader_preserves_alignment_options(self):
        align_macro = Mock(return_value=pd.DataFrame({"x": [1]}))
        engine = object()

        result = data_access_service.load_fed_macro_pair(
            engine=engine,
            align_macro_func=align_macro,
            macro_key="FEDFUNDS",
            market_asset="SP500",
            start_date="2020-01-01",
            end_date="2024-01-01",
        )

        self.assertEqual(result["x"].tolist(), [1])
        align_macro.assert_called_once_with(
            macro_key="FEDFUNDS",
            market_asset="SP500",
            engine=engine,
            start_date="2020-01-01",
            end_date="2024-01-01",
            how="outer",
            forward_fill=True,
        )


if __name__ == "__main__":
    unittest.main()
