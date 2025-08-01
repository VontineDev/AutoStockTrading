import unittest
import pandas as pd
from unittest.mock import MagicMock
from src.data.stock_data_manager import StockDataManager

class TestStockDataManager(unittest.TestCase):
    def setUp(self):
        # StockDataManager 인스턴스 생성 (DB 접근은 Mock)
        self.manager = StockDataManager(db_path=":memory:")
        # fetchdf 메서드 Mock
        self.manager.db.fetchdf = MagicMock()

    def test_get_available_symbols_for_backtest(self):
        # 가짜 데이터프레임 생성
        data = {
            'symbol': ['005930', '000660'],
            'name': ['삼성전자', 'SK하이닉스'],
            'market': ['KOSPI', 'KOSPI'],
            'data_count': [35, 40],
            'earliest_date': ['2023-01-01', '2023-01-01'],
            'latest_date': ['2023-02-05', '2023-02-10']
        }
        df_mock = pd.DataFrame(data)
        self.manager.db.fetchdf.return_value = df_mock

        result = self.manager.get_available_symbols_for_backtest(min_data_days=30)
        self.assertFalse(result.empty)
        self.assertIn('symbol', result.columns)
        self.assertIn('data_count', result.columns)
        self.assertTrue((result['data_count'] >= 30).all())
        self.assertIn('display_name', result.columns)
        # display_name 포맷 확인
        for idx, row in result.iterrows():
            self.assertIn(row['symbol'], row['display_name'])
            self.assertIn(row['name'], row['display_name'])

if __name__ == "__main__":
    unittest.main() 