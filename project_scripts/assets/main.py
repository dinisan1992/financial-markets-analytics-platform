from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd

from config import CSV_PATH, DB_CONFIG

from database import (
    conectar_bd,
    importar_csv_e_update_mysql,
    update_indicadores_sql,
    update_manipulacao_sql
)

from indicators import calcular_indicadores

from risk_detection import identificar_possivel_manipulacao_forte

from charts import gerar_dashboard


# =========================
# MAIN FUNCTION
# =========================
def main():
    conn = None
    cursor = None

    try:
        # =========================
        # DATABASE CONNECTION
        # =========================
        conn, cursor = conectar_bd(DB_CONFIG)

        # =========================
        # IMPORTAR CSV NOVO
        # =========================
        importar_csv_e_update_mysql(
            csv_path=CSV_PATH,
            conn=conn,
            cursor=cursor
        )

        # =========================
        # LER DADOS DO MYSQL
        # =========================
        df = pd.read_sql(
            """
            SELECT
                snapped_at,
                price,
                total_volume
            FROM btc_analysis
            ORDER BY snapped_at ASC
            """,
            conn
        )

        if df.empty:
            print("❌ No data available.")
            return

        # =========================
        # FORMATAR DATAS
        # =========================
        df["snapped_at"] = pd.to_datetime(
            df["snapped_at"]
            .astype(str)
            .str.replace(" UTC", "", regex=False),
            errors="coerce"
        )

        df = df.dropna(subset=["snapped_at"])

        # =========================
        # VOLUME
        # =========================
        df["volume"] = df["total_volume"]

        # =========================
        # CRIAR CANDLESTICK REALISTA
        # =========================
        df["open"] = df["price"].shift(1)
        df["close"] = df["price"]

        df["high"] = (
            df[["open", "close"]]
            .max(axis=1)
            * 1.01
        )

        df["low"] = (
            df[["open", "close"]]
            .min(axis=1)
            * 0.99
        )

        # Remove primeira linha com NaN no open
        df = df.dropna().reset_index(drop=True)

        if df.empty:
            print("❌ Insufficient data after candle creation.")
            return

        # =========================
        # CALCULAR INDICADORES
        # =========================
        df = calcular_indicadores(df)

        # =========================
        # ATUALIZAR INDICADORES NO SQL
        # Only legacy indicators that already exist in the table.
        # =========================
        update_indicadores_sql(
            df=df,
            cursor=cursor,
            conn=conn
        )

        # =========================
        # MANIPULATION DETECTION
        # =========================
        df["manipulation"] = None

        flags = identificar_possivel_manipulacao_forte(df)

        for data_flag, motivo in flags:
            df.loc[
                df["snapped_at"] == data_flag,
                "manipulation"
            ] = motivo

        # =========================
        # UPDATE MANIPULATION FLAGS IN SQL
        # =========================
        update_manipulacao_sql(
            df=df,
            cursor=cursor,
            conn=conn
        )

        # =========================
        # DASHBOARD
        # =========================
        gerar_dashboard(df)

        # =========================
        # MANIPULATION LOG
        # =========================
        if flags:
            print("\n⚠️ Possible manipulation signals detected:")

            for data, motivo in flags:
                print(f"{data}: {motivo}")

        else:
            print("\n✅ No clear manipulation signal identified.")

        print("✅ Processing completed.")

    except Exception as e:
        print(f"❌ Error during processing: {e}")

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None:
            conn.close()


# =========================
# EXECUTION
# =========================
if __name__ == "__main__":
    main()
