"""ML classifier for GRIFFIN -- H2O primary, sklearn fallback."""

import os
import logging
import pickle

import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODEL_DIR = _PROJECT_ROOT / "models"
_TRAINING_DATA = _PROJECT_ROOT / "data" / "training" / "workday_features.csv"
_SKLEARN_MODEL_PATH = _MODEL_DIR / "sklearn_gbm_fallback.pkl"

# The 15 feature columns in training order
FEATURE_COLS = [
    'budget_mentioned', 'supervises_staff', 'receives_supervision',
    'supervision_count', 'education_level', 'years_experience',
    'text_length', 'leadership_keywords', 'technical_keywords',
    'research_keywords', 'healthcare_keywords', 'facilities_keywords',
    'finance_keywords', 'is_exempt', 'is_salaried'
]

TARGET_COL = 'occ_family'

# ── H2O model cache (JVM boots once, model stays in memory) ──────────
_h2o_model = None
_h2o_available = None  # None = untested, True/False = tested


def _get_h2o_model():
    """Load H2O and the GBM model once, cache for all subsequent predictions."""
    global _h2o_model, _h2o_available

    # Already tested and failed — skip JVM retry
    if _h2o_available is False:
        return None

    # Already loaded — return cached model
    if _h2o_model is not None:
        return _h2o_model

    try:
        import h2o
        h2o.init(nthreads=1, max_mem_size="512M", verbose=False)
        model_path = str(
            _MODEL_DIR
            / "GBM_lr_annealing_selection_AutoML_1_20260408_205246_select_model"
        )
        _h2o_model = h2o.load_model(model_path)
        _h2o_available = True
        logger.info("H2O model loaded and cached.")
        return _h2o_model
    except Exception as e:
        logger.warning("H2O init/load failed: %s. Will use sklearn fallback.", e)
        _h2o_available = False
        return None


def _try_h2o_predict(features_df):
    """Attempt prediction with the cached H2O GBM model."""
    import h2o as h2o_mod

    model = _get_h2o_model()
    if model is None:
        return None

    try:
        h2o_frame = h2o_mod.H2OFrame(features_df)
        pred = model.predict(h2o_frame)
        result = pred.as_data_frame()

        predicted_class = result['predict'].iloc[0]
        prob_cols = [c for c in result.columns if c != 'predict']
        probs = {col: round(result[col].iloc[0] * 100, 1) for col in prob_cols}

        return {
            'method': 'H2O AutoML (GBM)',
            'prediction': predicted_class,
            'probabilities': probs,
            'model_id': 'GBM_lr_annealing_selection_AutoML_1',
        }
    except Exception as e:
        logger.warning("H2O prediction failed: %s. Falling back to sklearn.", e)
        return None


def _ensure_sklearn_model():
    """Train and save a sklearn GBM if it doesn't exist yet."""
    if _SKLEARN_MODEL_PATH.exists():
        with open(_SKLEARN_MODEL_PATH, 'rb') as f:
            return pickle.load(f)

    if not _TRAINING_DATA.exists():
        logger.error("Training data not found: %s", _TRAINING_DATA)
        return None

    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import LabelEncoder

    df = pd.read_csv(_TRAINING_DATA)
    # Drop Unknown class (same as H2O notebook)
    df = df[df[TARGET_COL] != 'Unknown']

    X = df[FEATURE_COLS]
    le = LabelEncoder()
    y = le.fit_transform(df[TARGET_COL])

    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1,
        random_state=42
    )
    model.fit(X, y)

    # Save model + label encoder
    _SKLEARN_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SKLEARN_MODEL_PATH, 'wb') as f:
        pickle.dump({'model': model, 'label_encoder': le}, f)

    logger.info("sklearn fallback model trained and saved.")
    return {'model': model, 'label_encoder': le}


def _sklearn_predict(features_df):
    """Predict with sklearn GBM fallback."""
    try:
        bundle = _ensure_sklearn_model()
        if bundle is None:
            return None

        model = bundle['model']
        le = bundle['label_encoder']

        X = features_df[FEATURE_COLS]
        proba = model.predict_proba(X)[0]
        classes = le.classes_

        predicted_idx = proba.argmax()
        predicted_class = classes[predicted_idx]
        probs = {cls: round(p * 100, 1) for cls, p in zip(classes, proba)}

        return {
            'method': 'sklearn GBM (fallback)',
            'prediction': predicted_class,
            'probabilities': probs,
            'model_id': 'sklearn_GBM_fallback',
        }
    except Exception as e:
        logger.error("sklearn prediction also failed: %s", e)
        return None


def predict_occupational_family(features_dict):
    """Predict occupational family from extracted features.

    Tries H2O first, falls back to sklearn.

    Args:
        features_dict: dict with the 15 feature values

    Returns:
        dict with 'method', 'prediction', 'probabilities', 'model_id'
        or None if both methods fail
    """
    features_df = pd.DataFrame([features_dict])[FEATURE_COLS]

    # Try H2O first (the real course model)
    result = _try_h2o_predict(features_df)
    if result is not None:
        return result

    # Fallback to sklearn
    return _sklearn_predict(features_df)
