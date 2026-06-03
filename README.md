# AION

**AI Agent Orchestrator Node**

AION est un orchestrateur IA local personnel destiné à piloter des services Python, des scripts, des automatisations et, à terme, des connecteurs IA, domotiques et professionnels.

## Objectif V0.1

Cette première version pose les fondations :

- application console ;
- configuration centralisée ;
- registre de services ;
- exécution de services ;
- journalisation ;
- services de démonstration.

## Lancer AION

Créer l'environnement virtuel :

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Lancer :

```powershell
python main.py
```

Commandes disponibles :

```text
help
services
run hello
run system_info
quit
```

## Philosophie

Tout est un service.

Chaque service doit pouvoir être enregistré, découvert et exécuté par le noyau AION.
