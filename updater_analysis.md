### **`updater.py` 상세 기능 분석 (매개변수 및 반환값 명시)**

#### **1. `StockDataUpdater` 클래스**

이 파일의 중심이 되는 클래스로, 데이터 업데이트와 관련된 모든 메서드를 포함합니다.

##### **`__init__(self, db_path: str = None, config_path: str = None)` (생성자)**

*   **역할:** `StockDataUpdater` 객체를 초기화합니다.
*   **매개변수:**
    *   `db_path` (str, Optional): SQLite 데이터베이스 파일의 경로. 기본값은 `PROJECT_ROOT/data/trading.db`입니다.
    *   `config_path` (str, Optional): 설정 파일(`config.yaml`)의 경로. 기본값은 `PROJECT_ROOT/config.yaml`입니다.
*   **반환값:** 없음 (`None`).
*   **세부 동작:**
    1.  **경로 설정:** 데이터베이스와 설정 파일 경로를 설정합니다.
    2.  **설정 로드 (`_load_config`):** `config.yaml` 파일을 로드하여 데이터 수집 관련 설정을 가져옵니다.
    3.  **DB 초기화 (`_init_database`):** 필요한 테이블(예: `api_usage`)을 생성합니다.
    4.  **API 사용량 추적:** `pykrx` 호출 횟수를 추적하는 변수(`api_calls_today`)를 DB에서 로드하여 초기화합니다.

##### **`_load_config(self) -> Dict`**

*   **역할:** `config.yaml` 설정 파일을 로드합니다.
*   **매개변수:** 없음.
*   **반환값:**
    *   `Dict`: 파일에서 로드한 설정 정보를 담은 딕셔너리. 파일이 없거나 오류 발생 시 기본 설정을 반환합니다.
*   **세부 동작:** YAML 파서를 이용해 설정 파일을 읽고 파이썬 딕셔너리로 변환합니다.

##### **`_init_database(self)`**

*   **역할:** 데이터베이스 파일과 필요한 테이블 스키마를 초기화합니다.
*   **매개변수:** 없음.
*   **반환값:** 없음 (`None`).
*   **세부 동작:** `os.makedirs`로 DB 파일이 저장될 디렉토리를 확인/생성하고, `sqlite3`를 이용해 `stock_info` (market_cap 컬럼 포함) 및 `stock_ohlcv` 테이블이 없으면 생성하는 SQL을 실행합니다.

##### **`save_symbol_info(self, symbol_info: Dict)`**

*   **역할:** 단일 종목의 정보를 `stock_info` 테이블에 저장하거나 업데이트합니다.
*   **매개변수:**
    *   `symbol_info` (Dict): 저장할 종목 정보를 담은 딕셔너리. (키: `symbol`, `name`, `market` 등)
*   **반환값:** 없음 (`None`).
*   **세부 동작:** `INSERT OR REPLACE` SQL 구문을 사용하여 DB에 데이터를 저장합니다.

##### **`update_all_symbol_info_with_krx(self, kospi_csv: str = "krx_sector_kospi.csv", kosdaq_csv: str = "krx_sector_kosdaq.csv") -> Optional[pd.DataFrame]`**

*   **역할:** 전체 상장 종목의 기본 정보(종목코드, 종목명, 시장, 섹터)를 최신 상태로 업데이트합니다.
*   **매개변수:**
    *   `kospi_csv` (str): 코스피 업종 정보가 담긴 CSV 파일 경로.
    *   `kosdaq_csv` (str): 코스닥 업종 정보가 담긴 CSV 파일 경로.
*   **반환값:**
    *   `pd.DataFrame` (Optional): 성공적으로 병합된 전체 종목 정보 데이터프레임. 실패 시 `None`을 반환할 수 있습니다.
*   **세부 동작:**
    1.  `pykrx`에서 전체 종목 코드와 이름을 가져옵니다.
    2.  두 개의 CSV 파일에서 업종 정보를 읽어옵니다.
    3.  `pykrx` 정보와 CSV 정보를 '종목코드' 기준으로 병합합니다.
    4.  병합된 데이터를 `stock_info` 테이블에 저장합니다.

##### **`update_daily_market_data(self, date_str: str)`**

*   **역할:** 특정 **하루**의 **시장 전체** OHLCV 데이터를 업데이트합니다.
*   **매개변수:**
    *   `date_str` (str): 데이터를 가져올 날짜 (형식: 'YYYYMMDD').
*   **반환값:** 없음 (`None`).
*   **세부 동작:** `pykrx.stock.get_market_ohlcv(date, market="ALL")`을 호출하여 데이터를 가져온 뒤, DB에 저장하는 로직을 수행합니다. (현재 코드에서는 DB 저장 로직이 TODO로 남아있음)

##### **`update_specific_stock_data(self, ticker: str, start_date_str: str, end_date_str: str)`**

*   **역할:** 특정 **하나의 종목**에 대한 **지정된 기간**의 OHLCV 데이터를 업데이트합니다.
*   **매개변수:**
    *   `ticker` (str): 종목 코드.
    *   `start_date_str` (str): 시작 날짜 ('YYYYMMDD').
    *   `end_date_str` (str): 종료 날짜 ('YYYYMMDD').
*   **반환값:** 없음 (`None`).
*   **세부 동작:** `pykrx.stock.get_market_ohlcv(start, end, ticker)`를 호출하여 데이터를 가져온 뒤, DB에 저장합니다. (현재 코드에서는 DB 저장 로직이 TODO로 남아있음)

##### **`update_all_historical_data(self, start_date_str: str, end_date_str: str)`**

*   **역할:** **시장 전체 종목**에 대해 **지정된 기간**의 OHLCV 데이터를 업데이트합니다.
*   **매개변수:**
    *   `start_date_str` (str): 시작 날짜 ('YYYYMMDD').
    *   `end_date_str` (str): 종료 날짜 ('YYYYMMDD').
*   **반환값:** 없음 (`None`).
*   **세부 동작:** 모든 종목 코드를 가져온 뒤, 각 종목에 대해 `update_specific_stock_data`를 반복 호출합니다.

##### **`update_market_cap_data(self, date_str: str = None)`**

*   **역할:** 특정일의 전체 시장 시가총액 데이터를 `stock_info` 테이블에 업데이트합니다.
*   **매개변수:**
    *   `date_str` (str, Optional): 데이터를 가져올 날짜 (형식: 'YYYYMMDD'). 기본값은 `None`이며, 이 경우 오늘 날짜를 사용합니다.
*   **반환값:** 없음 (`None`).
*   **세부 동작:**
    1.  `pykrx.stock.get_market_cap` API를 호출하여 특정일의 전체 시장 시가총액 데이터를 가져옵니다.
    2.  가져온 데이터를 순회하며 각 종목의 시가총액 정보를 `stock_info` 테이블의 `market_cap` 컬럼에 업데이트합니다.

#### **2. `main()` 함수**

*   **역할:** `python src/data/updater.py`와 같이 이 파일을 직접 실행했을 때 동작하는 진입점입니다.
*   **매개변수:** 없음.
*   **반환값:** 없음 (`None`).
*   **세부 동작:** `StockDataUpdater` 객체를 생성하고, 주석 처리된 예시 코드들을 통해 개발자가 직접 특정 기능을 테스트할 수 있도록 합니다. 기본적으로는 `update_all_symbol_info_with_krx`를 호출합니다.