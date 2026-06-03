# AION V0.3.1 - Memory UX

Cette brique améliore l'utilisation de la mémoire permanente depuis la console.

## Commandes

```text
memory
memory list
memory list <type>
memory show <clé>
memory search <texte>
memory stats
remember clé=valeur
remember path clé=chemin
recall clé
forget clé
```

## Exemples

```text
remember prenom=Pascal
remember path projet_aion=C:\code\python\AION
memory list
memory list path
memory show projet_aion
memory search aion
memory stats
recall prenom
forget prenom
```

## Types de mémoire

Pour l'instant :

- `info` : information texte simple ;
- `path` : chemin local existant.

Plus tard :

- `file` : fichier copié dans l'espace AION ;
- `secret_ref` : référence vers un secret externe ;
- `device` : appareil domotique ou réseau ;
- `service_config` : configuration liée à un service.
