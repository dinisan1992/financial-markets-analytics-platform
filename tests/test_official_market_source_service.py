from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.market_data_sync_service import read_market_csv
from services.official_market_source_service import (
    H15_US2Y_SERIES,
    prepare_h15_market_frame,
    validate_h15_market_frame,
    write_standard_market_csv,
)


H15_FIXTURE = """\
"Series Description","Two year yield"
"Unit:","Percent:_Per_Year"
"Multiplier:","1"
"Currency:","NA"
"Unique Identifier:","H15/H15/RIFLGFCY02_N.B"
"Time Period","RIFLGFCY02_N.B"
1976-06-01,7.26
1976-06-02,ND
1976-06-03,7.23
1976-06-03,7.24
"""


class OfficialMarketSourceServiceTests(unittest.TestCase):
    def test_h15_parser_selects_real_two_year_series(self):
        frame = prepare_h15_market_frame(StringIO(H15_FIXTURE), H15_US2Y_SERIES)
        summary = validate_h15_market_frame(frame)

        self.assertEqual(2, summary["rows"])
        self.assertEqual(2, summary["unique_dates"])
        self.assertEqual(0, summary["native_ohlc_rows"])
        self.assertEqual(7.24, frame.iloc[-1]["price"])
        self.assertTrue(frame[["open", "high", "low", "close"]].isna().all().all())

    def test_standard_csv_round_trip_preserves_synthetic_ohlc_contract(self):
        frame = prepare_h15_market_frame(StringIO(H15_FIXTURE))
        with TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "us2y_data_clean.csv"
            write_standard_market_csv(frame, destination)
            prepared = read_market_csv(destination)

        self.assertEqual(2, len(prepared.frame))
        self.assertEqual(0, prepared.invalid_rows)
        self.assertTrue(
            prepared.frame[["open", "high", "low", "close"]].isna().all().all()
        )


if __name__ == "__main__":
    unittest.main()
