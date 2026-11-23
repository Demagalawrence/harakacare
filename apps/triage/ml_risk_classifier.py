"""
ML Risk Classification Module - Phase 3 AI Upgrade

Implements machine learning risk prediction for triage assessments.
Supports Logistic Regression, Decision Tree, Random Forest, and XGBoost models.

EXPERIMENTAL PROTOTYPE - This uses clinician-authored scenarios for training
since real clinical data is not available. Results must NOT be used for
actual clinical decisions without proper validation.

All models include feature importance for explainability.
"""

import logging
import json
import os
import pickle
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Try to import sklearn - available in development
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        precision_score, recall_score, f1_score,
        confusion_matrix, classification_report
    )
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - ML risk classification disabled")

# Try to import XGBoost
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# Try to import SHAP for explainability
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


@dataclass
class MLRiskResult:
    """ML risk prediction result"""
    risk_level: str  # 'low', 'medium', 'high'
    confidence: float  # 0.0 to 1.0
    model_name: str
    model_version: str
    inference_time_ms: int
    feature_importance: Dict[str, float]
    contributing_features: List[str]
    missing_info: List[str]
    explanation: str
    calibration_score: Optional[float] = None
    is_experimental: bool = True


class MLModelRegistry:
    """
    Registry for ML models with versioning.
    Only trained models are used for predictions.
    """
    
    MODELS_DIR = os.path.join(os.path.dirname(__file__), 'ml_models')
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.model_versions: Dict[str, str] = {}
        self.model_metadata: Dict[str, Dict] = {}
        self.scalers: Dict[str, Any] = {}
        self.label_encoders: Dict[str, Any] = {}
        self.feature_names: Dict[str, List[str]] = {}
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models from disk"""
        if not os.path.exists(self.MODELS_DIR):
            os.makedirs(self.MODELS_DIR, exist_ok=True)
            logger.info(f"Created models directory: {self.MODELS_DIR}")
        
        # Try to load existing models
        for model_file in os.listdir(self.MODELS_DIR):
            if model_file.endswith('.pkl'):
                model_name = model_file.replace('.pkl', '')
                try:
                    with open(os.path.join(self.MODELS_DIR, model_file), 'rb') as f:
                        model_data = pickle.load(f)
                    self.models[model_name] = model_data.get('model')
                    self.model_versions[model_name] = model_data.get('version', '1.0.0')
                    self.model_metadata[model_name] = model_data.get('metadata', {})
                    self.scalers[model_name] = model_data.get('scaler')
                    self.label_encoders[model_name] = model_data.get('label_encoder')
                    self.feature_names[model_name] = model_data.get('feature_names', [])
                    logger.info(f"Loaded model: {model_name} v{self.model_versions[model_name]}")
                except Exception as e:
                    logger.error(f"Failed to load model {model_name}: {e}")
    
    def save_model(self, name: str, model: Any, version: str, metadata: Dict,
                   scaler: Any = None, label_encoder: Any = None,
                   feature_names: List[str] = None):
        """Save a trained model to disk"""
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        
        model_data = {
            'model': model,
            'version': version,
            'metadata': metadata,
            'scaler': scaler,
            'label_encoder': label_encoder,
            'feature_names': feature_names or [],
            'saved_at': datetime.utcnow().isoformat(),
        }
        
        path = os.path.join(self.MODELS_DIR, f'{name}.pkl')
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        self.models[name] = model
        self.model_versions[name] = version
        self.model_metadata[name] = metadata
        self.scalers[name] = scaler
        self.label_encoders[name] = label_encoder
        self.feature_names[name] = feature_names or []
        
        logger.info(f"Saved model: {name} v{version}")
    
    def get_model(self, name: str) -> Optional[Tuple[Any, str]]:
        """Get a model by name, returns (model, version) or None"""
        if name in self.models:
            return self.models[name], self.model_versions.get(name, '1.0.0')
        return None
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models"""
        return [
            {
                'name': name,
                'version': self.model_versions.get(name, '1.0.0'),
                'metadata': self.model_metadata.get(name, {}),
                'is_experimental': self.model_metadata.get(name, {}).get('is_experimental', True),
            }
            for name in self.models
        ]


# Global model registry
model_registry = MLModelRegistry()


class MLRiskClassifier:
    """
    ML-based risk classifier with multiple algorithm support.
    
    Falls back to rule-based classification if no trained model is available.
    """
    
    def __init__(self, model_name: str = 'random_forest'):
        self.model_name = model_name
        self.model = None
        self.model_version = 'experimental-1.0.0'
        self.scaler = None
        self.label_encoder = None
        self.feature_names = []
        self.is_trained = False
        self.is_experimental = True
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create a new untrained one"""
        result = model_registry.get_model(self.model_name)
        if result:
            self.model, self.model_version = result
            metadata = model_registry.model_metadata.get(self.model_name, {})
            self.is_experimental = metadata.get('is_experimental', True)
            self.scaler = model_registry.scalers.get(self.model_name)
            self.label_encoder = model_registry.label_encoders.get(self.model_name)
            self.feature_names = model_registry.feature_names.get(self.model_name, [])
            self.is_trained = self.model is not None
            logger.info(f"Loaded ML model: {self.model_name} v{self.model_version}")
        else:
            self._create_untrained_model()
    
    def _create_untrained_model(self):
        """Create an untrained model instance"""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available - cannot create ML model")
            return
        
        if self.model_name == 'random_forest' and SKLEARN_AVAILABLE:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced',  # Handle class imbalance
            )
        elif self.model_name == 'logistic_regression' and SKLEARN_AVAILABLE:
            self.model = LogisticRegression(
                max_iter=1000,
                class_weight='balanced',
                random_state=42,
            )
        elif self.model_name == 'decision_tree' and SKLEARN_AVAILABLE:
            self.model = DecisionTreeClassifier(
                max_depth=10,
                min_samples_split=5,
                class_weight='balanced',
                random_state=42,
            )
        elif self.model_name == 'xgboost' and XGBOOST_AVAILABLE:
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
            )
        else:
            logger.warning(f"Model {self.model_name} not available, falling back to random_forest")
            self.model_name = 'random_forest'
            if SKLEARN_AVAILABLE:
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    class_weight='balanced',
                )
        
        self.is_trained = False
        self.is_experimental = True
        logger.info(f"Created untrained ML model: {self.model_name}")
    
    def train_with_clinician_scenarios(self, scenarios: List[Dict[str, Any]],
                                       test_size: float = 0.2) -> Dict[str, float]:
        """
        Train the model using clinician-authored scenarios.
        
        Each scenario should contain:
        - age_group, sex, complaint_group, symptom_severity, symptom_duration,
          progression_status, has_chronic_conditions, is_pregnant, on_medication,
          red_flag_indicators (dict), risk_level (target)
        
        Returns evaluation metrics.
        
        WARNING: This is experimental training data, not clinically validated.
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn not available for training")
        
        if not scenarios:
            raise ValueError("No training scenarios provided")
        
        # Extract features and labels
        X, y, feature_names = self._extract_features(scenarios)
        
        # Encode labels
        self.label_encoder = LabelEncoder()
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Split train/test with patient-level separation
        # (each patient appears in only one split to prevent data leakage)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=test_size, random_state=42,
            stratify=y_encoded if len(set(y_encoded)) > 1 else None
        )
        
        # Train model
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        
        metrics = {
            'precision': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        }
        
        # Per-class metrics
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        metrics['per_class'] = report
        
        # Store feature names and training info
        self.feature_names = feature_names
        self.is_trained = True
        self.model_version = f'trained-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}'
        self.is_experimental = True  # Still experimental even after training with scenarios
        
        # Save model
        model_registry.save_model(
            name=self.model_name,
            model=self.model,
            version=self.model_version,
            metadata={
                'is_experimental': True,
                'training_scenarios': len(scenarios),
                'feature_names': feature_names,
                'metrics': metrics,
                'note': 'Trained on clinician-authored scenarios, NOT clinical data',
            },
            scaler=self.scaler,
            label_encoder=self.label_encoder,
            feature_names=feature_names,
        )
        
        logger.info(f"Model trained: {self.model_name} v{self.model_version}")
        logger.info(f"Metrics: precision={metrics['precision']:.3f}, recall={metrics['recall']:.3f}, f1={metrics['f1_score']:.3f}")
        
        return metrics
    
    def _extract_features(self, scenarios: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str], List[str]]:
        """Extract feature matrix from scenarios"""
        feature_names = [
            'age_group_encoded',
            'sex_encoded',
            'complaint_group_encoded',
            'symptom_severity_encoded',
            'symptom_duration_encoded',
            'progression_encoded',
            'has_chronic_conditions',
            'is_pregnant',
            'on_medication',
            'has_red_flags',
            'red_flag_count',
        ]
        
        # Simple encoding for categorical features
        age_map = {'newborn': 0, 'infant': 1, 'child_1_5': 2, 'child_6_12': 3,
                   'teen': 4, 'adult': 5, 'elderly': 6}
        sex_map = {'male': 0, 'female': 1, 'other': 2}
        complaint_map = {'fever': 0, 'breathing': 1, 'chest_pain': 2, 'bleeding': 3,
                        'headache': 4, 'abdominal': 5, 'injury': 6, 'pregnancy': 7,
                        'skin': 8, 'feeding': 9, 'mental_health': 10, 'other': 11}
        severity_map = {'mild': 0, 'moderate': 1, 'severe': 2, 'very_severe': 3}
        duration_map = {'less_than_1_hour': 0, '1_6_hours': 1, '6_24_hours': 2,
                       '1_3_days': 3, '4_7_days': 4, 'more_than_1_week': 5,
                       'more_than_1_month': 6}
        progression_map = {'sudden': 0, 'getting_worse': 1, 'staying_same': 2,
                          'getting_better': 3, 'comes_and_goes': 4}
        
        X = []
        y = []
        
        for scenario in scenarios:
            red_flags = scenario.get('red_flag_indicators', {})
            if isinstance(red_flags, dict):
                red_flag_count = sum(1 for v in red_flags.values() if v)
                has_red_flags = 1 if red_flag_count > 0 else 0
            else:
                red_flag_count = 0
                has_red_flags = 0
            
            features = [
                age_map.get(scenario.get('age_group', 'adult'), 5),
                sex_map.get(scenario.get('sex', 'other'), 2),
                complaint_map.get(scenario.get('complaint_group', 'other'), 11),
                severity_map.get(scenario.get('symptom_severity', 'mild'), 0),
                duration_map.get(scenario.get('symptom_duration', 'less_than_1_hour'), 0),
                progression_map.get(scenario.get('progression_status', 'staying_same'), 2),
                1 if scenario.get('has_chronic_conditions', False) else 0,
                1 if scenario.get('is_pregnant', False) else 0,
                1 if scenario.get('on_medication', False) else 0,
                has_red_flags,
                red_flag_count,
            ]
            
            X.append(features)
            y.append(scenario.get('risk_level', 'low'))
        
        return np.array(X, dtype=float), y, feature_names
    
    def predict(self, triage_data: Dict[str, Any]) -> MLRiskResult:
        """
        Make a risk prediction for a triage session.
        
        Returns MLRiskResult with risk level, confidence, and explanations.
        """
        start_time = datetime.utcnow()
        
        if not self.is_trained or self.model is None:
            # Fall back to rule-based
            return self._rule_based_fallback(triage_data, start_time)
        
        # Extract features
        features = self._encode_single(triage_data)
        
        if features is None:
            return self._rule_based_fallback(triage_data, start_time)
        
        # Scale features
        if self.scaler:
            features_scaled = self.scaler.transform([features])
        else:
            features_scaled = [features]
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        # Decode prediction
        risk_level = self.label_encoder.inverse_transform([prediction])[0]
        confidence = float(max(probabilities))
        
        # Get feature importance
        feature_importance = self._get_feature_importance(features)
        
        # Get contributing features (top 3)
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        contributing = [f[0] for f in sorted_features[:3] if f[1] > 0]
        
        # Calculate inference time
        end_time = datetime.utcnow()
        inference_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Determine missing info
        missing_info = []
        if not triage_data.get('symptom_duration'):
            missing_info.append('symptom_duration')
        if not triage_data.get('symptom_severity'):
            missing_info.append('symptom_severity')
        
        # Generate explanation
        explanation = self._generate_explanation(
            risk_level, confidence, triage_data, feature_importance, contributing
        )
        
        # Check red flags override (safety: red flags never downgraded)
        red_flags = triage_data.get('red_flag_indicators', {})
        if isinstance(red_flags, dict) and any(red_flags.values()):
            if risk_level != 'high':
                risk_level = 'high'
                confidence = max(confidence, 0.9)
                explanation += " OVERRIDE: Red flags detected - risk elevated to HIGH regardless of ML prediction."
        
        return MLRiskResult(
            risk_level=risk_level,
            confidence=confidence,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_time_ms=inference_ms,
            feature_importance=feature_importance,
            contributing_features=contributing,
            missing_info=missing_info,
            explanation=explanation,
            is_experimental=self.is_experimental,
        )
    
    def _encode_single(self, triage_data: Dict[str, Any]) -> Optional[List[float]]:
        """Encode a single triage data point into feature vector"""
        if not self.feature_names:
            return None
        
        age_map = {'newborn': 0, 'infant': 1, 'child_1_5': 2, 'child_6_12': 3,
                   'teen': 4, 'adult': 5, 'elderly': 6}
        sex_map = {'male': 0, 'female': 1, 'other': 2}
        complaint_map = {'fever': 0, 'breathing': 1, 'chest_pain': 2, 'bleeding': 3,
                        'headache': 4, 'abdominal': 5, 'injury': 6, 'pregnancy': 7,
                        'skin': 8, 'feeding': 9, 'mental_health': 10, 'other': 11}
        severity_map = {'mild': 0, 'moderate': 1, 'severe': 2, 'very_severe': 3}
        duration_map = {'less_than_1_hour': 0, '1_6_hours': 1, '6_24_hours': 2,
                       '1_3_days': 3, '4_7_days': 4, 'more_than_1_week': 5,
                       'more_than_1_month': 6}
        progression_map = {'sudden': 0, 'getting_worse': 1, 'staying_same': 2,
                          'getting_better': 3, 'comes_and_goes': 4}
        
        red_flags = triage_data.get('red_flag_indicators', {})
        if isinstance(red_flags, dict):
            red_flag_count = sum(1 for v in red_flags.values() if v)
            has_red_flags = 1 if red_flag_count > 0 else 0
        else:
            red_flag_count = 0
            has_red_flags = 0
        
        return [
            age_map.get(triage_data.get('age_group', 'adult'), 5),
            sex_map.get(triage_data.get('sex', 'other'), 2),
            complaint_map.get(triage_data.get('complaint_group', 'other'), 11),
            severity_map.get(triage_data.get('symptom_severity', 'mild'), 0),
            duration_map.get(triage_data.get('symptom_duration', 'less_than_1_hour'), 0),
            progression_map.get(triage_data.get('progression_status', 'staying_same'), 2),
            1 if triage_data.get('has_chronic_conditions', False) else 0,
            1 if triage_data.get('is_pregnant', False) else 0,
            1 if triage_data.get('on_medication', False) else 0,
            has_red_flags,
            float(red_flag_count),
        ]
    
    def _get_feature_importance(self, features: List[float]) -> Dict[str, float]:
        """Get feature importance for the current prediction"""
        if not self.feature_names or not self.is_trained:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_[0])
        else:
            return {}
        
        result = {}
        for i, name in enumerate(self.feature_names):
            if i < len(importances):
                result[name] = float(importances[i])
        
        return result
    
    def _generate_explanation(self, risk_level: str, confidence: float,
                               triage_data: Dict[str, Any],
                               feature_importance: Dict[str, float],
                               contributing: List[str]) -> str:
        """Generate a human-readable explanation of the ML prediction"""
        parts = []
        
        parts.append(f"ML-predicted risk level: {risk_level.upper()}")
        parts.append(f"Confidence: {confidence:.1%}")
        
        if contributing:
            parts.append(f"Key contributing factors: {', '.join(contributing)}")
        
        if triage_data.get('red_flag_indicators'):
            rf = triage_data['red_flag_indicators']
            if isinstance(rf, dict) and any(rf.values()):
                flags = [k for k, v in rf.items() if v]
                parts.append(f"Red flags detected: {', '.join(flags)}")
        
        if triage_data.get('age_group'):
            parts.append(f"Age group: {triage_data['age_group']}")
        
        if triage_data.get('complaint_group'):
            parts.append(f"Complaint: {triage_data['complaint_group']}")
        
        parts.append("This is an ML prediction, NOT a medical diagnosis.")
        parts.append("Always consult a qualified healthcare worker.")
        
        return ". ".join(parts)
    
    def _rule_based_fallback(self, triage_data: Dict[str, Any],
                              start_time: datetime) -> MLRiskResult:
        """Fallback to rule-based classification when ML model unavailable"""
        # Simple rule-based logic
        risk_score = 0.0
        
        complaint = triage_data.get('complaint_group', 'other')
        complaint_risks = {
            'chest_pain': 0.7, 'breathing': 0.65, 'bleeding': 0.7,
            'headache': 0.4, 'pregnancy': 0.5, 'abdominal': 0.4,
            'fever': 0.35, 'injury': 0.3, 'mental_health': 0.3,
            'skin': 0.2, 'feeding': 0.25, 'other': 0.2,
        }
        risk_score += complaint_risks.get(complaint, 0.2)
        
        severity = triage_data.get('symptom_severity', 'mild')
        severity_weights = {'mild': 0.0, 'moderate': 0.2, 'severe': 0.4, 'very_severe': 0.6}
        risk_score += severity_weights.get(severity, 0.0)
        
        age_group = triage_data.get('age_group', 'adult')
        age_multipliers = {
            'newborn': 1.8, 'infant': 1.6, 'child_1_5': 1.3,
            'child_6_12': 1.0, 'teen': 1.0, 'adult': 1.0, 'elderly': 1.5,
        }
        risk_score *= age_multipliers.get(age_group, 1.0)
        
        red_flags = triage_data.get('red_flag_indicators', {})
        if isinstance(red_flags, dict) and any(red_flags.values()):
            risk_score = max(risk_score, 0.9)  # Red flags force high risk
        
        if risk_score >= 0.7:
            risk_level = 'high'
        elif risk_score >= 0.4:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        end_time = datetime.utcnow()
        inference_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return MLRiskResult(
            risk_level=risk_level,
            confidence=min(risk_score, 0.85),
            model_name='rule-based-fallback',
            model_version='1.0.0',
            inference_time_ms=inference_ms,
            feature_importance={},
            contributing_features=[],
            missing_info=[],
            explanation=(
                f"Rule-based risk assessment: {risk_level.upper()}. "
                f"ML model not available - using rule-based fallback. "
                f"This is NOT a medical diagnosis."
            ),
            is_experimental=True,
        )
    
    def get_shap_explanation(self, triage_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate SHAP explanation for the prediction.
        
        Returns None if SHAP is not available or model is not trained.
        """
        if not SHAP_AVAILABLE or not self.is_trained or self.model is None:
            return None
        
        features = self._encode_single(triage_data)
        if features is None:
            return None
        
        if self.scaler:
            features_scaled = self.scaler.transform([features])
        else:
            features_scaled = [features]
        
        try:
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(features_scaled)
            
            # Handle multi-class output
            if isinstance(shap_values, list):
                # Take the predicted class
                pred_idx = 0  # Simplified
                shap_vals = shap_values[pred_idx][0]
            else:
                shap_vals = shap_values[0]
            
            explanation = {}
            for i, name in enumerate(self.feature_names):
                if i < len(shap_vals):
                    explanation[name] = float(shap_vals[i])
            
            return {
                'method': 'SHAP',
                'feature_contributions': explanation,
                'base_value': float(explainer.expected_value) if hasattr(explainer, 'expected_value') else 0.0,
            }
        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return None


# Global classifier instance
ml_classifier = MLRiskClassifier(model_name='random_forest')