"""Service fs_search - recherche de fichiers par mots-cles dans un repertoire."""
from pathlib import Path
from typing import Any

from aion.services.base_service import BaseService


class FsSearchService(BaseService):
    """
    Recherche des fichiers par mots-cles dans un repertoire.

    Payload :
        keywords   : str  - mots-cles separes par espaces (ex: "rapport 2026")
        directory  : str  - chemin direct (optionnel)
        memory_key : str  - cle memoire contenant le repertoire (defaut: search_dir)
    """

    name        = "fs_search"
    description = "Recherche des fichiers par mots-cles dans un repertoire (recursif)"
    permissions = ["filesystem"]
    domain      = "fs"

    IGNORED_EXTENSIONS = {
        ".exe", ".dll", ".sys", ".tmp", ".pyc", ".pyo", ".pyd",
        ".db", ".sqlite", ".ico", ".cur", ".lnk",
    }

    def execute(self, payload: dict[str, Any]) -> str:
        keywords_raw = payload.get("keywords", "").strip()
        directory    = payload.get("directory", "").strip()
        memory_key   = payload.get("memory_key", "search_dir")

        if not keywords_raw:
            return (
                "fs_search : aucun mot-cle fourni.\n"
                "Usage : run fs_search avec payload {keywords: \"mot1 mot2\", memory_key: \"docs\"}"
            )

        keywords = [kw.lower() for kw in keywords_raw.split() if kw]

        if not directory:
            directory = self._get_dir_from_memory(memory_key)

        if not directory:
            return (
                f"fs_search : repertoire non trouve pour la cle \"{memory_key}\".\n"
                f"  Memorise un repertoire : remember path {memory_key}=C:\\ton\\dossier"
            )

        search_path = Path(directory)
        if not search_path.exists():
            return f"fs_search : repertoire introuvable : {directory}"
        if not search_path.is_dir():
            return f"fs_search : ce chemin n est pas un repertoire : {directory}"

        matches = self._search(search_path, keywords)

        kw_str = " + ".join(keywords)
        if not matches:
            return (
                f"fs_search : aucun fichier trouve\n"
                f"  Repertoire : {directory}\n"
                f"  Mots-cles  : {kw_str}"
            )

        lines = [
            f"fs_search : {len(matches)} fichier(s) trouve(s)",
            f"  Repertoire : {directory}",
            f"  Mots-cles  : {kw_str}",
            f"  {'─' * 50}",
        ]
        sorted_matches = sorted(matches)

        # Sauvegarder les chemins pour "fs open <n>" en console
        try:
            import json as _json
            paths_json = _json.dumps([str(p) for p in sorted_matches])
            self._save_last_results(paths_json)
        except Exception:
            pass

        for idx, filepath in enumerate(sorted_matches, start=1):
            rel = filepath.relative_to(search_path)
            lines.append(f"  OPEN:{filepath}|{rel}|{idx}")

        return "\n".join(lines)

    def _get_dir_from_memory(self, key: str) -> str:
        try:
            from aion.memory.memory_manager import MemoryManager
            return MemoryManager().recall(key) or ""
        except Exception:
            return ""

    def _save_last_results(self, paths_json: str) -> None:
        """Sauvegarde les derniers resultats pour fs open <n>."""
        try:
            from aion.memory.memory_manager import MemoryManager
            MemoryManager().remember_temp("_fs_last_results", paths_json)
        except Exception:
            pass

    def _search(self, root: Path, keywords: list[str]) -> list[Path]:
        matches = []
        try:
            for filepath in root.rglob("*"):
                if not filepath.is_file():
                    continue
                if filepath.suffix.lower() in self.IGNORED_EXTENSIONS:
                    continue
                name_lower = filepath.name.lower()
                if all(kw in name_lower for kw in keywords):
                    matches.append(filepath)
        except PermissionError:
            pass
        return matches
