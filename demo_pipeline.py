"""Deterministic, entirely synthetic overtime example for the public dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from tree_audit import leaf_catalog

SEED = 20261020
PEOPLE = 180
UNITS = ("Unidade A", "Unidade B", "Unidade C")
ROLES = ("Operação", "Manutenção", "Logística")
FEATURES = (
    "horas_ciclo_anterior",
    "horas_2_ciclos_atras",
    "media_3_ciclos",
    "media_6_ciclos",
    "horas_folga_anterior",
    "horas_trabalho_anterior",
    "media_equipe_anterior",
    "tempo_casa_meses",
    "dias_uteis_ciclo",
    "mes_sin",
    "mes_cos",
    *(f"unidade_{i}" for i in range(len(UNITS))),
    *(f"funcao_{i}" for i in range(len(ROLES))),
)


def cycle_label(period: pd.Period) -> str:
    start = (period - 1).to_timestamp() + pd.Timedelta(days=15)
    end = period.to_timestamp() + pd.Timedelta(days=14)
    return f"{start:%d/%m/%Y} a {end:%d/%m/%Y}"


def feature_frame(period, units, roles, tenure, past) -> pd.DataFrame:
    """Create features from past cycles only; row order is the fictional cohort."""
    previous = past[-1] if past else np.zeros(len(units))
    angle = 2 * np.pi * period.month / 12
    days = pd.date_range(
        (period - 1).to_timestamp() + pd.Timedelta(days=15),
        period.to_timestamp() + pd.Timedelta(days=14),
    )
    frame = pd.DataFrame(
        {
            "ciclo": str(period),
            "unidade": [UNITS[i] for i in units],
            "funcao": [ROLES[i] for i in roles],
            "horas_ciclo_anterior": previous,
            "horas_2_ciclos_atras": past[-2] if len(past) > 1 else np.zeros(len(units)),
            "media_3_ciclos": np.mean(past[-3:], axis=0) if past else np.zeros(len(units)),
            "media_6_ciclos": np.mean(past[-6:], axis=0) if past else np.zeros(len(units)),
            "horas_folga_anterior": previous * np.take([0.25, 0.35, 0.20], roles),
            "tempo_casa_meses": tenure,
            "dias_uteis_ciclo": int((days.dayofweek < 5).sum()),
            "mes_sin": np.sin(angle),
            "mes_cos": np.cos(angle),
        }
    )
    frame["horas_trabalho_anterior"] = previous - frame.horas_folga_anterior
    frame["media_equipe_anterior"] = frame.groupby(["unidade", "funcao"])[
        "horas_ciclo_anterior"
    ].transform("mean")
    for i in range(len(UNITS)):
        frame[f"unidade_{i}"] = (units == i).astype(int)
    for i in range(len(ROLES)):
        frame[f"funcao_{i}"] = (roles == i).astype(int)
    return frame


def synthetic_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return person-cycle examples and one future feature row per fictional person."""
    rng = np.random.default_rng(SEED)
    units = rng.integers(0, len(UNITS), PEOPLE)
    roles = rng.integers(0, len(ROLES), PEOPLE)
    propensity = rng.normal(0, 1.1, PEOPLE)
    initial_tenure = rng.integers(0, 120, PEOPLE)
    past: list[np.ndarray] = []
    frames = []
    periods = pd.period_range("2020-01", "2026-10", freq="M")

    for step, period in enumerate(periods):
        previous = past[-1] if past else np.zeros(PEOPLE)
        angle = 2 * np.pi * period.month / 12
        frame = feature_frame(period, units, roles, initial_tenure + step, past)

        if period == periods[-1]:
            return pd.concat(frames, ignore_index=True), frame

        seasonal = 1.2 * np.sin(angle) + 0.8 * np.cos(angle)
        expected = (
            3.7
            + np.take([0.4, 1.7, -0.5], units)
            + np.take([1.5, 0.9, -0.2], roles)
            + propensity
            + seasonal
            + 0.27 * previous
        )
        hours = np.maximum(0, rng.normal(expected, 1.9))
        hours[rng.random(PEOPLE) < 0.11] = 0
        frame["horas"] = hours
        frames.append(frame)
        past.append(hours)

    raise AssertionError("The calendar must contain a future cycle.")


def _matrix(frame: pd.DataFrame, feature_names=None) -> xgb.DMatrix:
    names = list(FEATURES if feature_names is None else feature_names)
    missing = set(names).difference(frame.columns)
    if missing:
        raise ValueError("Os dados não contêm todas as variáveis esperadas pelo modelo.")
    return xgb.DMatrix(frame[names].astype("float32"))


def build_demo(output: Path, rounds: int = 1229) -> dict:
    """Fit only synthetic records and write the small artifacts used by the app."""
    if rounds < 1:
        raise ValueError("rounds must be positive")
    panel, future = synthetic_panel()
    train = panel.loc[panel.ciclo.lt("2024-01")]
    validation = panel.loc[panel.ciclo.between("2024-01", "2024-12")].copy()
    test = panel.loc[panel.ciclo.between("2025-01", "2026-09")].copy()
    dtrain = _matrix(train)
    dtrain.set_label(train.horas.to_numpy())
    booster = xgb.train(
        {
            "objective": "reg:absoluteerror",
            "tree_method": "hist",
            "max_depth": 3,
            "eta": 0.025,
            "min_child_weight": 6,
            "subsample": 0.85,
            "colsample_bytree": 0.9,
            "lambda": 2,
            "seed": SEED,
            "nthread": 2,
        },
        dtrain,
        num_boost_round=rounds,
    )
    validation["bruta"] = np.maximum(booster.predict(_matrix(validation)), 0)
    global_factor = float(validation.horas.sum() / validation.bruta.sum())
    by_role = (
        validation.groupby("funcao", observed=True)[["horas", "bruta"]]
        .sum()
        .assign(factor=lambda frame: frame.horas / frame.bruta)
    )
    factors = {
        role: float(np.clip(0.6 * row.factor + 0.4 * global_factor, 0.75, 1.35))
        for role, row in by_role.iterrows()
    }

    test["previstas"] = np.maximum(booster.predict(_matrix(test)), 0) * test.funcao.map(factors)
    monthly = (
        test.groupby("ciclo", as_index=False)[["horas", "previstas"]]
        .sum()
        .rename(columns={"horas": "realizadas"})
    )
    errors = (monthly.previstas - monthly.realizadas).abs()
    mape = float((errors / monthly.realizadas).mean() * 100)
    wape = float(errors.sum() / monthly.realizadas.sum() * 100)
    forecast_raw = np.maximum(booster.predict(_matrix(future)), 0)
    future_total = float(np.dot(forecast_raw, future.funcao.map(factors).to_numpy()))
    units = future[[f"unidade_{i}" for i in range(len(UNITS))]].to_numpy().argmax(axis=1)
    roles = future[[f"funcao_{i}" for i in range(len(ROLES))]].to_numpy().argmax(axis=1)
    past = [group.horas.to_numpy() for _, group in panel.groupby("ciclo", sort=True)][-6:]
    forecasts, future_frames = [], []
    for step, period in enumerate(pd.period_range("2026-10", periods=12, freq="M")):
        frame = feature_frame(period, units, roles, future.tempo_casa_meses.to_numpy() + step, past)
        calibrated = np.maximum(booster.predict(_matrix(frame)), 0) * frame.funcao.map(factors)
        forecasts.append(
            {
                "ciclo": str(period),
                "periodo": cycle_label(period),
                "horas_previstas": float(calibrated.sum()),
                "pessoas_elegiveis": PEOPLE,
            }
        )
        future_frames.append(frame)
        past.append(calibrated.to_numpy())
    metadata = {
        "data_origin": "synthetic",
        "seed": SEED,
        "people": PEOPLE,
        "training_cycles": ["2020-01", "2023-12"],
        "calibration_cycles": ["2024-01", "2024-12"],
        "test_cycles": ["2025-01", "2026-09"],
        "future_cycle": "2026-10",
        "tree_count": rounds,
        "tree_count_policy": "fixed_for_demonstration",
        "features": list(FEATURES),
        "calibration_factors": factors,
        "mape_pct": mape,
        "wape_pct": wape,
        "mae_hours": float(errors.mean()),
        "future_hours": future_total,
    }
    output.mkdir(parents=True, exist_ok=True)
    booster.save_model(output / "demo_model.json")
    monthly.to_csv(output / "monthly.csv", index=False, float_format="%.10f")
    future.to_csv(output / "future_features.csv", index=False, float_format="%.10f")
    pd.concat(future_frames).to_csv(
        output / "projection_features.csv", index=False, float_format="%.10f"
    )
    pd.DataFrame(forecasts).to_csv(output / "forecast.csv", index=False, float_format="%.10f")
    panel.groupby("ciclo", as_index=False).horas.sum().to_csv(
        output / "history.csv", index=False, float_format="%.10f"
    )
    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def audit_demo(booster: xgb.Booster, future: pd.DataFrame, factors: dict[str, float]) -> dict:
    """Reconcile the public forecast with the reached leaves of every demo tree."""
    names = booster.feature_names
    if not names:
        raise ValueError("O modelo não contém os nomes das variáveis da auditoria.")
    matrix = _matrix(future, names)
    raw = booster.predict(matrix).astype("float64")
    scale = future.funcao.map(factors).to_numpy(dtype="float64")
    effective = np.where(raw > 0, scale, 0)
    reached = booster.predict(matrix, pred_leaf=True).astype("int32")
    if reached.ndim == 1:
        reached = reached.reshape(-1, 1)
    nodes = booster.trees_to_dataframe()
    leaves = nodes.loc[nodes.Feature.eq("Leaf"), ["Tree", "Node", "Gain"]]
    values = np.full((reached.shape[1], int(nodes.Node.max()) + 1), np.nan)
    values[leaves.Tree.to_numpy(dtype=int), leaves.Node.to_numpy(dtype=int)] = leaves.Gain.to_numpy(
        dtype="float64"
    )
    selected = values[np.arange(reached.shape[1])[None, :], reached]
    if not np.isfinite(selected).all():
        raise ValueError("A reached leaf was not found in the model.")
    effects = (selected * effective[:, None]).sum(axis=0)
    base = float(np.dot(raw - selected.sum(axis=1), effective))
    score_text = json.loads(booster.save_config())["learner"]["learner_model_param"]["base_score"]
    base_score = float(np.asarray(json.loads(score_text)).reshape(-1)[0])
    total = float(np.dot(np.maximum(raw, 0), scale))
    if not np.isclose(base + effects.sum(), total, atol=0.01):
        raise ValueError("Tree effects do not reconcile with the forecast.")
    summary = (
        nodes.groupby("Tree")
        .agg(
            perguntas=("Feature", lambda values: int((values != "Leaf").sum())),
            folhas=("Feature", lambda values: int((values == "Leaf").sum())),
        )
        .reset_index()
    )
    summary["arvore"] = summary.Tree + 1
    summary["efeito_horas"] = effects
    routes = leaf_catalog(nodes)
    width = values.shape[1]
    keys = (np.arange(reached.shape[1])[None, :] * width + reached).ravel()
    indexes = (routes.arvore.to_numpy() - 1) * width + routes.no_folha.to_numpy()
    routes["pessoas"] = np.bincount(keys, minlength=values.size)[indexes]
    routes["previsoes_positivas"] = np.bincount(
        keys, weights=np.repeat(raw > 0, reached.shape[1]), minlength=values.size
    )[indexes].astype(int)
    routes["efeito_horas"] = np.bincount(
        keys, weights=(selected * effective[:, None]).ravel(), minlength=values.size
    )[indexes]
    shap = booster.predict(matrix, pred_contribs=True).astype("float64")
    contributions = pd.DataFrame(
        {
            "variavel": [*names, "Base SHAP"],
            "efeito_horas": (shap * effective[:, None]).sum(axis=0),
        }
    )
    if not np.isclose(contributions.efeito_horas.sum(), total, atol=0.02, rtol=0):
        raise ValueError("SHAP contributions do not reconcile with the forecast.")
    factor_table = future[["funcao"]].assign(fator=scale, positiva=raw > 0, efetivo=effective)
    factor_table = factor_table.groupby("funcao", as_index=False).agg(
        pessoas=("fator", "size"),
        fator=("fator", "first"),
        positivas=("positiva", "sum"),
        soma_fatores=("efetivo", "sum"),
    )
    return {
        "people": len(raw),
        "positive": int((raw > 0).sum()),
        "zeroed": int((raw <= 0).sum()),
        "base_score": base_score,
        "factor_sum": float(effective.sum()),
        "base_hours": base,
        "tree_hours": float(effects.sum()),
        "total_hours": total,
        "trees": summary,
        "nodes": nodes,
        "routes": routes,
        "contributions": contributions,
        "factors": factor_table,
    }
