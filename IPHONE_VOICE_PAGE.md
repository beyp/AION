# AION Voice — Page de résultats iPhone

## Raccourci iPhone — Configuration complète

### Actions dans l'app Raccourcis (dans cet ordre)

1. **Dicter du texte** → Langue: Français, s'arrête automatiquement

2. **Obtenir le contenu de l'URL**
   - URL: `http://TON-IP:8000/api/voice`
   - Méthode: POST
   - En-têtes: Content-Type = application/json
   - Corps: {"text": "[Texte dicté]", "lang": "fr"}

3. **Obtenir valeur du dictionnaire**
   - Dictionnaire: Résultat étape 2
   - Clé: `response`
   - → Stocker dans variable "Réponse vocale"

4. **Parler du texte**
   - Texte: "Réponse vocale"
   - Voix: Amélie (français)

5. **Obtenir valeur du dictionnaire** (2e fois)
   - Dictionnaire: Résultat étape 2
   - Clé: `url`
   - → Stocker dans variable "URL résultat"

6. **Ouvrir URL**
   - URL: "URL résultat"
   → Safari s'ouvre avec la page de détails !

## Commandes ADO — alternatives vocales

Maintenant reconnu automatiquement :
| Ce que tu dis | Ce qu'AION comprend |
|---|---|
| "azure" | ADO |
| "devops" | ADO |
| "azur" | ADO |
| "mes tickets" | ado_search_items |
| "mes activites" | ado_search_items |
| "mon backlog" | ado_search_items |
| "mes bugs" | ado_search_items type=Bug |
| "minuteur" | timer |
| "pomodoro" | timer 25 minutes |
| "quick mind" | QuickMind |

## Page de résultats

La page `/voice/result/{uid}` affiche :
- Ta question
- La réponse vocale courte
- Les résultats détaillés (ADO cliquables, tâches formatées...)
- Expire après 5 minutes
