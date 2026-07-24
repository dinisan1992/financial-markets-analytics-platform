import pandas as pd

from indicators import calcular_rsi, calcular_atr


# =========================
# MANIPULATION / ANOMALY DETECTION
# =========================
def identificar_possivel_manipulacao_forte(df):
    """
    Identifies heuristic signals of possible manipulation/anomaly.

    Importante:
    - These signals do NOT prove manipulation.
    - They only indicate abnormal volume, price, candle, RSI and ATR patterns.
    """

    flags = []

    df = df.copy().reset_index(drop=True)

    required_columns = [
        "snapped_at",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Required column missing for risk_detection: {col}")

    # =========================
    # RSI / ATR
    # =========================
    if "rsi" not in df.columns:
        df["rsi"] = calcular_rsi(df["close"])

    if "atr" not in df.columns:
        df["atr"] = calcular_atr(
            df["high"],
            df["low"],
            df["close"]
        )

    # =========================
    # REFERENCE AVERAGES
    # =========================
    vol_mean = df["volume"].rolling(window=20).mean()
    vol_std = df["volume"].rolling(window=20).std()

    atr_medio = df["atr"].rolling(window=20).mean()

    # =========================
    # LOOP PRINCIPAL
    # =========================
    for i in range(1, len(df)):
        preco_current = df.loc[i, "close"]
        preco_anterior = df.loc[i - 1, "close"]
        volume_current = df.loc[i, "volume"]

        vol_mean_current = vol_mean.iloc[i]
        vol_std_current = vol_std.iloc[i]

        # Ignorar rows sem data suficientes
        if (
            pd.isna(preco_current)
            or pd.isna(preco_anterior)
            or pd.isna(volume_current)
            or pd.isna(vol_mean_current)
            or pd.isna(vol_std_current)
            or preco_anterior == 0
        ):
            continue

        corpo_candle = abs(
            preco_current - df.loc[i, "open"]
        )

        corpo_total = (
            df.loc[i, "high"]
            -
            df.loc[i, "low"]
        )

        if pd.isna(corpo_total) or corpo_total == 0:
            continue

        variacao_pct = (
            abs(preco_current - preco_anterior)
            /
            preco_anterior
            * 100
        )

        candle_ratio = corpo_candle / corpo_total

        volume_anormal = (
            volume_current >
            vol_mean_current + 2.5 * vol_std_current
        )

        motivo = ""

        # =========================
        # PUMP / DUMP E SPOOFING
        # =========================
        if volume_anormal:
            if candle_ratio > 0.5 and variacao_pct > 5:
                motivo = "Pump/Dump likely"

            elif candle_ratio < 0.3 and variacao_pct < 0.5:
                motivo = "Spoofing likely"

        # =========================
        # RSI EXTREMO
        # =========================
        if motivo:
            rsi_current = df.loc[i, "rsi"]

            if not pd.isna(rsi_current):
                if rsi_current > 80:
                    motivo += " | RSI muito alto"

                elif rsi_current < 20:
                    motivo += " | RSI muito baixo"

        # =========================
        # ATR ALTO
        # =========================
        if motivo:
            atr_current = df.loc[i, "atr"]
            atr_medio_current = atr_medio.iloc[i]

            if (
                not pd.isna(atr_current)
                and not pd.isna(atr_medio_current)
                and atr_medio_current > 0
                and atr_current > 1.5 * atr_medio_current
            ):
                motivo += " | ATR alto"

        # =========================
        # GUARDAR FLAG
        # =========================
        if motivo:
            flags.append(
                (
                    df.loc[i, "snapped_at"],
                    motivo
                )
            )

    return flags
