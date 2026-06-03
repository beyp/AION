# Architecture AION V0.1

## Principe

AION repose sur une logique simple :

```text
Console
  ↓
AionApp
  ↓
ServiceRegistry
  ↓
ServiceExecutor
  ↓
Services
```

## Noyau

Le noyau charge :

- la configuration ;
- le logger ;
- le registre de services ;
- l'exécuteur.

## Services

Un service est une classe Python qui hérite de `BaseService`.

Chaque service expose :

- `name`
- `description`
- `permissions`
- `execute(payload)`

## Prochaine étape

V0.2 pourra ajouter :

- un vrai routeur d'intentions ;
- une mémoire locale JSON ;
- un client Mistral ;
- un chargement dynamique des services.
