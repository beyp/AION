# AION Voice — Guide Raccourcis iPhone

## 1. Raccourci Principal — "AION"
Commandes vocales + réponse vocale + page web de détails

Actions :
1. Dicter du texte (Langue: FR)
2. Obtenir contenu URL → POST http://TON-IP:8000/api/voice
   Corps: {"text": "[Texte dicté]", "lang": "fr"}
3. Obtenir valeur dictionnaire → clé: "response" → Parler du texte
4. Obtenir valeur dictionnaire → clé: "url"
5. Ouvrir URL (Safari s'ouvre automatiquement)

---

## 2. Raccourci "Recherche AION"
Recherche un mot-clé dans ADO + QuickMind simultanément

Actions :
1. Demander une entrée → "Que chercher ?"
2. Obtenir contenu URL → POST http://TON-IP:8000/api/voice
   Corps: {"text": "cherche [Entrée saisie]", "lang": "fr"}
3. Obtenir valeur → clé: "url"
4. Ouvrir URL

Ou en vocal :
1. Dicter du texte
2. → même configuration que raccourci principal

---

## Commandes vocales — Ce qui fonctionne maintenant

### Réseau
- "IP" / "mon IP" / "adresse IP"
- "réseau" / "état réseau"
- "ping"

### Système
- "CPU" / "mémoire" / "RAM"
- "disques" / "stockage"
- "uptime" / "depuis combien de temps"

### QuickMind
- "ajoute [titre]" / "nouvelle tâche [titre]"
- "mes tâches" / "liste tâches"

### ADO (toutes ces formulations fonctionnent)
- "mes items" / "mes tickets" / "mon backlog"
- "en cours" / "in progress"
- "mes bugs" / "bugs actifs"
- "azure" / "devops" / "azur" → reconnu automatiquement

### Recherche universelle ADO + QuickMind
- "cherche [mot]" → cherche dans ADO ET QuickMind
- "trouve [mot]" → idem
- "y a-t-il quelque chose sur [mot]" → idem
- "recherche [mot]" → idem

### Timer
- "timer [durée]" / "minuteur [durée]"
- "pomodoro" → timer 25 minutes
- "pause 10 minutes"

---

## Remplacer l'URL

Trouver ton IP locale :
```
ipconfig | findstr IPv4
→ 192.168.1.XX
```

URL à utiliser dans le raccourci :
`http://192.168.1.XX:8000/api/voice`
