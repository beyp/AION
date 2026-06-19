# AION Voice — Diagnostic timeout iPhone

## Test rapide depuis iPhone Safari

Ouvre cette URL dans Safari sur iPhone :
```
http://192.168.1.XX:8000/api/ping
```
Remplace XX par ton IP locale.

Si ça répond → le serveur est accessible ✅
Si ça timeout → problème réseau ou serveur sur 127.0.0.1

## Causes possibles du timeout

### 1. Serveur sur 127.0.0.1 (CAUSE LA PLUS FRÉQUENTE)
Vérifier que uvicorn tourne avec --host 0.0.0.0 :
```powershell
# Arrêter et relancer
taskkill /f /im python.exe
uvicorn aion.dashboard.server:app --host 0.0.0.0 --port 8000
```

### 2. Pare-feu Windows bloque le port 8000
```powershell
# Ouvrir le port 8000
netsh advfirewall firewall add rule name="AION Port 8000" protocol=TCP dir=in localport=8000 action=allow
```

### 3. URL retournée = 127.0.0.1 au lieu de l IP réseau
Corrigé dans cette version : l URL retournée utilise maintenant l IP de la requête.

### 4. iPhone et PC sur des réseaux WiFi différents
S assurer que les deux sont sur le même réseau WiFi.

## Séquence de test complète

```powershell
# 1. Trouver l IP
ipconfig | findstr IPv4

# 2. Tester depuis PC
curl http://localhost:8000/api/ping

# 3. Tester depuis PC vers IP réseau
curl http://192.168.1.XX:8000/api/ping

# 4. Si 3 fonctionne → tester depuis iPhone Safari
# → http://192.168.1.XX:8000/api/ping
```
