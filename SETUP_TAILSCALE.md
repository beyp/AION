# AION Voice — Configuration Tailscale

## 1. Mémoriser l URL Tailscale dans AION

Dans la console AION :
```
AION> remember aion_public_url=http://100.102.139.40:8000
```

Cela permet à AION de générer des URLs avec ton IP Tailscale
au lieu de 127.0.0.1 — accessibles depuis l iPhone partout.

## 2. Tester depuis iPhone Safari
```
http://100.102.139.40:8000/api/ping
```
Doit répondre : {"status": "ok", "message": "AION répond !"}

## 3. Raccourci iPhone — URL à utiliser
```
http://100.102.139.40:8000/api/voice
```

## 4. Si l appel ne marche toujours pas

Vérifier que uvicorn écoute sur 0.0.0.0 :
```powershell
# Dans startaion.bat ou manuellement :
uvicorn aion.dashboard.server:app --host 0.0.0.0 --port 8000

# Vérifier avec netstat
netstat -an | findstr :8000
# Doit montrer 0.0.0.0:8000 (pas 127.0.0.1:8000)
```

## 5. Avantage Tailscale vs WiFi local

| | WiFi local | Tailscale |
|---|---|---|
| Portée | Maison seulement | Partout dans le monde |
| Configuration | IP change | IP fixe 100.x.x.x |
| Sécurité | Réseau local | Chiffré WireGuard |
| iPhone absent | ❌ | ✅ |
