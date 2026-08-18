"""
Indicateurs de volume et de volatilité, basés sur ce qu'on a vu dans le
programme de mentorat (Phase 1-2) : volume relatif, OBV, CMF, ATR.
"""
import pandas as pd
import numpy as np


def add_volume_ma(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df["volume_ma"] = df["volume"].rolling(period).mean()
    return df


def add_relative_volume(df: pd.DataFrame) -> pd.DataFrame:
    """RVOL = volume du jour / moyenne mobile du volume."""
    df["rvol"] = df["volume"] / df["volume_ma"]
    return df


def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    """On-Balance Volume : cumul du volume selon le sens de clôture."""
    direction = np.sign(df["close"].diff()).fillna(0)
    df["obv"] = (direction * df["volume"]).cumsum()
    return df


def add_cmf(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """Chaikin Money Flow."""
    mf_multiplier = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / \
                     (df["high"] - df["low"]).replace(0, np.nan)
    mf_volume = mf_multiplier * df["volume"]
    df["cmf"] = mf_volume.rolling(period).sum() / df["volume"].rolling(period).sum()
    df["cmf"] = df["cmf"].fillna(0)
    return df


def add_atr(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """Average True Range, utile pour calibrer stop et déplacement impulsif."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = true_range.rolling(period).mean()
    return df


def obv_trend(df: pd.DataFrame, lookback: int) -> str:
    """
    Renvoie 'up', 'down' ou 'flat' selon la pente récente de l'OBV,
    utilisé pour détecter une divergence prix/OBV.
    """
    recent = df["obv"].tail(lookback)
    if len(recent) < 2:
        return "flat"
    slope = recent.iloc[-1] - recent.iloc[0]
    threshold = recent.abs().mean() * 0.05 if recent.abs().mean() > 0 else 0
    if slope > threshold:
        return "up"
    elif slope < -threshold:
        return "down"
    return "flat"


def compute_all(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Calcule tous les indicateurs et renvoie le DataFrame enrichi."""
    df = add_volume_ma(df, cfg.VOLUME_MA_PERIOD)
    df = add_relative_volume(df)
    df = add_obv(df)
    df = add_cmf(df, cfg.CMF_PERIOD)
    df = add_atr(df, cfg.ATR_PERIOD)
    return df
