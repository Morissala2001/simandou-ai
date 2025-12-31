
"""
Gestionnaire de modèles transparent
"""
import google.generativeai as genai
#import google.genai as genai

from datetime import datetime
import re


class ModelManager:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)

        # Configuration transparente
        self.models = {
            'default': 'gemini-2.5-flash',
            'advanced': 'gemini-robotics-er-1.5-preview'
        }

        # Précharger les modèles
        self.loaded_models = {}
        self._preload_models()

        # Compteurs d'utilisation (transparents)
        self.usage_counters = {
            'default': {'minute_count': 0, 'minute_start': datetime.now()},
            'advanced': {'minute_count': 0, 'minute_start': datetime.now()}
        }

    def _preload_models(self):
        """Précharge les modèles silencieusement"""
        try:
            self.loaded_models['default'] = genai.GenerativeModel(self.models['default'])
        except Exception:
            pass

        try:
            self.loaded_models['advanced'] = genai.GenerativeModel(self.models['advanced'])
        except Exception:
            pass

    def get_default_model(self):
        """Retourne le modèle par défaut"""
        return self.loaded_models.get('default')

    def select_model(self, query, file_type=None):
        """
        Sélectionne automatiquement le meilleur modèle
        L'utilisateur n'est pas informé de la décision
        """
        # Limites RPM
        default_limit = 15  # gemini-2.5-flash
        advanced_limit = 3  # gemini-robotics-er-1.5-preview

        # Vérifier la disponibilité du modèle par défaut
        if self._check_availability('default', default_limit):
            # Vérifier si on a besoin du modèle avancé
            if self._requires_advanced_model(query, file_type):
                if self._check_availability('advanced', advanced_limit):
                    return self.loaded_models['advanced'], 'advanced'

            # Sinon utiliser le modèle par défaut
            return self.loaded_models['default'], 'default'

        # Si modèle par défaut indisponible, essayer l'avancé
        if self._check_availability('advanced', advanced_limit):
            return self.loaded_models['advanced'], 'advanced'

        # Dernier recours: forcer l'utilisation du modèle par défaut
        return self.loaded_models['default'], 'default'

    def _requires_advanced_model(self, query, file_type):
        """
        Détecte silencieusement si la requête nécessite le modèle avancé
        """
        query_lower = query.lower()

        # Critères très spécifiques pour l'utilisation du modèle avancé
        advanced_criteria = [
            # Robotique et automatisation
            lambda q: any(word in q for word in [
                'robot kinematics', 'robot dynamics', 'manipulator',
                'end effector', 'trajectory planning', 'ros ',
                'moveit', 'gazebo', 'urdf', 'sdf'
            ]),

            # Ingénierie complexe
            lambda q: any(word in q for word in [
                'finite element analysis', 'computational fluid dynamics',
                'structural mechanics', 'control theory', 'kalman filter'
            ]),

            # Équations mathématiques complexes
            lambda q: re.search(r'\\begin\{equation}|abla|∂|∫|∑|∏', q),

            # Fichiers de code technique
            lambda q: file_type == 'code' and (
                    '.urdf' in q or '.sdf' in q or
                    'ros' in q or 'moveit' in q
            ),

            # Requêtes extrêmement longues
            lambda q: len(q.split()) > 300
        ]

        # Appliquer les critères
        for criterion in advanced_criteria:
            if criterion(query_lower):
                return True

        # Par défaut, utiliser le modèle standard
        return False

    def _check_availability(self, model_type, rpm_limit):
        """Vérifie si un modèle est disponible"""
        if model_type not in self.usage_counters:
            return False

        counter = self.usage_counters[model_type]
        current_time = datetime.now()

        # Réinitialiser le compteur minute si nécessaire
        minute_diff = (current_time - counter['minute_start']).total_seconds() / 60
        if minute_diff >= 1:
            counter['minute_count'] = 0
            counter['minute_start'] = current_time

        # Vérifier la limite RPM
        return counter['minute_count'] < rpm_limit

    def update_counter(self, model_type):
        """Met à jour le compteur d'utilisation"""
        if model_type in self.usage_counters:
            self.usage_counters[model_type]['minute_count'] += 1

    def reset_daily_counters(self):
        """Réinitialise les compteurs"""
        current_date = datetime.now().date()
        for counter in self.usage_counters.values():
            counter['last_reset'] = current_date
