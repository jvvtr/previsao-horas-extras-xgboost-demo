"""Deterministic, entirely synthetic overtime example for the public dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

SEED = 20261020
PEOPLE = 180
UNITS = ("Unidade A", "Unidade B", "Unidade C")
ROLES = ("Operação", "Manutenção", "Logística")
FEATURES = (
    "horas_ciclo_anterior",
    "media_3_ciclos",
    "mes_sin",
    "mes_cos",
    *(f"unidade_{i}" for i in range(len(UNITS))),
    *(f"funcao_{i}" for i in range(len(ROLES))),
)


def synthetic_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return person-cycle examples and one future feature row per fictional person."""
    rng = np.random.default_rng(SEED)
    units = rng.integers(0, len(UNITS), PEOPLE)
    roles = rng.integers(0, len(ROLES), PEOPLE)
    propensity = rng.normal(0, 1.1, PEOPLE)
    past: list[np.ndarray] = []
    frames = []
    periods = pd.period_range("2020-01", "2026-10", freq="M")

    for period in periods:
        previous = past[-1] if past else np.zeros(PEOPLE)
        average = np.mean(past[-3:], axis=0) if past else np.zeros(PEOPLE)
        angle = 2 * np.pi * period.month / 12
        frame = pd.DataFrame(
            {
                "ciclo": str(period),
                "unidade": [UNITS[i] for i in units],
                "funcao": [ROLES[i] for i in roles],
                "horas_ciclo_anterior": previous,
                "media_3_ciclos": average,
                "mes_sin": np.full(PEOPLE, np.sin(angle)),
                "mes_cos": np.full(PEOPLE, np.cos(angle)),
            }
        )
        for i in range(len(UNITS)):
            frame[f"unidade_{i}"] = (units == i).astype(int)
        for i in range(len(ROLES)):
            frame[f"funcao_{i}"] = (roles == i).astype(int)

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


def _matrix(frame: pd.DataFrame) -> xgb.DMatrix:
    return xgb.DMatrix(frame[list(FEATURES)].astype("float32"))


def build_demo(output: Path, rounds: int = 120) -> dict:
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
            "eta": 0.06,
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

    test["previstas"] = np.maximum(booster.predict(_matrix(test)), 0) * test.funcao.map(
        factors
    )
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
    metadata = {
        "data_origin": "synthetic",
        "seed": SEED,
        "people": PEOPLE,
        "training_cycles": ["2020-01", "2023-12"],
        "calibration_cycles": ["2024-01", "2024-12"],
        "test_cycles": ["2025-01", "2026-09"],
        "future_cycle": "2026-10",
        "tree_count": rounds,
        "features": list(FEATURES),
        "calibration_factors": factors,
        "mape_pct": mape,
        "wape_pct": wape,
        "future_hours": future_total,
    }
    output.mkdir(parents=True, exist_ok=True)
    booster.save_model(output / "demo_model.json")
    monthly.to_csv(output / "monthly.csv", index=False, float_format="%.10f")
    future.to_csv(output / "future_features.csv", index=False, float_format="%.10f")
    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def audit_demo(
    booster: xgb.Booster, future: pd.DataFrame, factors: dict[str, float]
) -> dict:
    """Reconcile the public forecast with the reached leaves of every demo tree."""
    matrix = _matrix(future)
    raw = booster.predict(matrix).astype("float64")
    scale = future.funcao.map(factors).to_numpy(dtype="float64")
    effective = np.where(raw > 0, scale, 0)
    reached = booster.predict(matrix, pred_leaf=True).astype("int32")
    if reached.ndim == 1:
        reached = reached.reshape(-1, 1)
    nodes = booster.trees_to_dataframe()
    leaves = nodes.loc[nodes.Feature.eq("Leaf"), ["Tree", "Node", "Gain"]]
    values = np.full((reached.shape[1], int(nodes.Node.max()) + 1), np.nan)
    values[leaves.Tree.to_numpy(dtype=int), leaves.Node.to_numpy(dtype=int)] = (
        leaves.Gain.to_numpy(dtype="float64")
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
    }
