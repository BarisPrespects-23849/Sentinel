"""Trains the ML half of the hybrid risk engine on synthetic scenarios.

There's no real incident history to learn from -- near-misses are exactly
what this system exists to prevent before they happen. So instead we
generate labeled scenarios directly in feature space:

  - "normal":       all present sensor types near baseline (label 0)
  - "single_spike": exactly one sensor type spikes, others calm (label 0
                     -- this is the important negative class: it teaches
                     the model that ONE anomalous sensor is not, by
                     itself, a compound risk)
  - "compound":      two or more sensor types spike simultaneously
                     (label 1)

Run with:
    python -m app.risk.train_model
"""

import random
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from app.risk.features import FEATURE_NAMES, SENSOR_TYPES, build_feature_vector

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
SAMPLES_PER_CLASS = 4000


def _normal_signal():
    return {"z": random.gauss(0, 1), "rate_z": random.gauss(0, 0.3)}


def _spiked_signal():
    # A hazard can be RISING (a developing leak) or PLATEAUED (a leak that
    # has stabilized at a dangerous level). The original generator only
    # produced rising spikes (rate_z 0.5-2.5), which taught the model
    # "dangerous means rising" -- steady-state elevation then scored ~0%.
    # Surfaced by the what-if simulator, whose sliders imply rate_z = 0.
    # The z range is also widened (2.5-15) so extreme readings, which the
    # sliders can produce, sit inside the training distribution.
    rising = random.random() < 0.6
    return {
        "z": random.uniform(2.5, 15.0),
        "rate_z": random.uniform(0.5, 2.5) if rising else random.gauss(0, 0.2),
    }


def _random_present_types() -> list[str]:
    """Mimics real zone compositions: our seeded zones each have 2 or 3
    of the 3 possible sensor types."""
    k = random.choice([2, 3])
    return random.sample(SENSOR_TYPES, k)


def generate_dataset(samples_per_class: int = SAMPLES_PER_CLASS):
    X, y = [], []

    for _ in range(samples_per_class):
        present = _random_present_types()
        signals = {t: _normal_signal() for t in present}
        X.append(build_feature_vector(signals))
        y.append(0)

    for _ in range(samples_per_class):
        present = _random_present_types()
        spiking = random.choice(present)
        signals = {t: (_spiked_signal() if t == spiking else _normal_signal()) for t in present}
        X.append(build_feature_vector(signals))
        y.append(0)

    for _ in range(samples_per_class):
        present = _random_present_types()
        n_spiking = random.randint(2, len(present))
        spiking = set(random.sample(present, n_spiking))
        signals = {t: (_spiked_signal() if t in spiking else _normal_signal()) for t in present}
        X.append(build_feature_vector(signals))
        y.append(1)

    return np.array(X), np.array(y)


def train_and_save() -> dict:
    X, y = generate_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(random_state=42)
    model.fit(X_train, y_train)

    accuracy = accuracy_score(y_test, model.predict(X_test))
    report = classification_report(y_test, model.predict(X_test))

    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, MODEL_PATH)

    return {"accuracy": accuracy, "report": report, "model_path": str(MODEL_PATH)}


if __name__ == "__main__":
    result = train_and_save()
    print(f"Test accuracy: {result['accuracy']:.3f}")
    print(result["report"])
    print(f"Saved model to {result['model_path']}")
