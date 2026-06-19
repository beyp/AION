# AION Voice API — Configuration iPhone

## Problème : Request timeout

**Cause** : uvicorn écoute sur `127.0.0.1` (seulement le PC local).
L'iPhone ne peut pas joindre `127.0.0.1` même sur le même WiFi.

## Fix 1 : startaion.bat (déjà dans ce ZIP)

Remplacer :
```
--host 127.0.0.1
```
Par :
```
--host 0.0.0.0
```

Ou relancer manuellement :
```powershell
uvicorn aion.dashboard.server:app --host 0.0.0.0 --port 8000
```

## Fix 2 : aion/core/app.py

Dans la méthode `_start_api()`, changer :
```python
"--host", "127.0.0.1",
```
En :
```python
"--host", "0.0.0.0",
```

## Trouver ton IP locale Windows

```powershell
ipconfig | findstr IPv4
```
→ Ex: `192.168.1.45`

## URL iPhone Raccourci

```
http://192.168.1.45:8000/api/voice
```
(remplacer `192.168.1.45` par ton IP réelle)

## Swagger /docs

La route `/api/voice` est visible sur :
```
http://127.0.0.1:8000/docs
```
ou depuis le réseau :
```
http://192.168.1.45:8000/docs
```

Si elle n'apparaît pas, c'est que le serveur n'a pas été relancé après le dernier git pull.
Redémarre uvicorn pour voir la route.

## Test rapide depuis PowerShell

```powershell
# Test local
Invoke-RestMethod -Uri "http://localhost:8000/api/voice" -Method POST -Body '{"text":"quel est mon IP ?"}' -ContentType "application/json"

# Test depuis réseau (même URL que l iPhone)
Invoke-RestMethod -Uri "http://192.168.1.45:8000/api/voice" -Method POST -Body '{"text":"quel est mon IP ?"}' -ContentType "application/json"
```

## Configuration Raccourci iPhone

Dans l'app Raccourcis :
1. **Dicter du texte** → Langue FR
2. **Obtenir contenu URL** :
   - URL : `http://192.168.1.45:8000/api/voice`
   - Méthode : POST
   - En-têtes : `Content-Type: application/json`
   - Corps : `{"text": "[Texte dicté]", "lang": "fr"}`
3. **Obtenir valeur** → Clé : `response`
4. **Parler du texte** → Voix Amélie

## Timeout

Si tu as encore des timeouts :
- Augmenter le timeout dans Raccourcis (60s minimum recommandé)
- Le premier appel Groq peut prendre 3-5 secondes
