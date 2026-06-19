# AION Voice — Raccourci iPhone

## Configuration

### 1. Trouver l IP de ton PC
Dans AION console :
    AION> net status
    → IP locale : 192.168.1.XX

### 2. Créer le raccourci dans l app Raccourcis (Shortcuts)

**Actions à ajouter dans cet ordre :**

1. **Dicter du texte**
   - Langue : Français
   - S arrete automatiquement : Oui

2. **Obtenir le contenu de l URL**
   - URL : `http://192.168.1.XX:8000/api/voice`
   - Méthode : POST
   - En-têtes : Content-Type = application/json
   - Corps (JSON) :
     ```json
     {
       "text": "[Texte dicté]",
       "lang": "fr"
     }
     ```

3. **Obtenir la valeur du dictionnaire**
   - Dictionnaire : Résultat de l étape précédente
   - Clé : `response`

4. **Parler du texte**
   - Texte : Résultat de l étape précédente
   - Voix : Amélie (français)

### 3. Ajouter à Siri
   - Nom : "AION" ou "Assistant projet"
   - Appel : "Dis à Siri : AION" ou bouton raccourci

## Exemples de commandes vocales

| Vous dites | AION fait |
|---|---|
| "Quelle est mon IP publique ?" | Retourne l IP |
| "Ajoute une tâche RDV client demain urgent" | Crée dans QuickMind |
| "Montre mes tâches ADO en cours" | Liste les items ADO |
| "Lance un timer 25 minutes" | Timer Pomodoro |
| "État du réseau" | Statut réseau complet |
| "CPU et RAM" | Utilisation système |
| "Mes tâches QuickMind" | Liste les tâches |

## Raccourcis supplémentaires suggérés

### Raccourci "Tâche rapide"
Sans dictée — juste une boîte de saisie :
1. **Demander une entrée** : "Titre de la tâche ?"
2. POST /api/voice avec `{"text": "ajoute [entrée] priorité normale"}`
3. **Parler** la réponse

### Raccourci "Statut projet"
Sans interaction :
1. POST /api/voice avec `{"text": "montre mes taches ADO en cours"}`
2. **Parler** la réponse
3. Excellent pour widget écran d accueil !
