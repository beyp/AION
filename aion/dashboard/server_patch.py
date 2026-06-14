"""
PATCH server.py - Routes a ajouter dans aion/dashboard/server.py

Colle ces routes a la fin de server.py (avant la fin du fichier).
"""

# ── Section Help ──────────────────────────────────────────────────────────────
# @app.get("/section/help", response_class=HTMLResponse)
# async def section_help(request: Request):
#     from aion.core.help_builder import build_help_html
#     return templates.TemplateResponse(
#         request=request,
#         name="sections/help.html",
#         context={"help_html": build_help_html(registry)},
#     )
#
# ── Routes FS ─────────────────────────────────────────────────────────────────
# from fastapi.responses import JSONResponse
#
# @app.post("/fs/search", response_class=HTMLResponse)
# async def fs_search(request: Request):
#     import html as h
#     body = await request.json()
#     keywords   = body.get("keywords", "")
#     directory  = body.get("directory", "")
#     memory_key = body.get("memory_key", "search_dir")
#
#     result = executor.execute("fs_search", {
#         "keywords":   keywords,
#         "directory":  directory,
#         "memory_key": memory_key,
#     })
#
#     lines = result.splitlines()
#     html_parts = []
#     for line in lines:
#         if line.startswith("  OPEN:"):
#             rest = line.replace("  OPEN:", "", 1)
#             fullpath, relpath = rest.split("|", 1)
#             ext = fullpath.rsplit(".", 1)[-1].lower() if "." in fullpath else ""
#             icons = {"pdf":"📕","doc":"📘","docx":"📘","xls":"📗","xlsx":"📗",
#                      "ppt":"📙","pptx":"📙","txt":"📄","py":"🐍","zip":"📦",
#                      "jpg":"🖼","jpeg":"🖼","png":"🖼","mp4":"🎬","mp3":"🎵"}
#             icon = icons.get(ext, "📄")
#             safe_path    = h.escape(fullpath).replace("\", "\\")
#             safe_relpath = h.escape(relpath)
#             html_parts.append(
#                 f'<div class="fs-result-item">'
#                 f'  <span class="fs-icon">{icon}</span>'
#                 f'  <span class="fs-name">{safe_relpath}</span>'
#                 f'  <button class="fs-open-btn" onclick="openFile(\'{safe_path}\', this)">'
#                 f'    ↗ Ouvrir</button>'
#                 f'</div>'
#             )
#         elif line.startswith("  ─"):
#             html_parts.append('<hr style="border-color:var(--border); margin:8px 0;">')
#         elif "aucun fichier" in line.lower():
#             html_parts.append(
#                 f'<div style="color:var(--text-dim); padding:16px; text-align:center;">'
#                 f'😶 {h.escape(line)}</div>'
#             )
#         elif line.strip():
#             html_parts.append(
#                 f'<div class="stat-row">'
#                 f'<span style="color:var(--text-dim); font-size:0.82rem;">{h.escape(line)}</span>'
#                 f'</div>'
#             )
#     return HTMLResponse("\n".join(html_parts) if html_parts else
#                         f'<pre class="cmd-result">{h.escape(result)}</pre>')
#
#
# @app.post("/fs/open")
# async def fs_open(request: Request):
#     body = await request.json()
#     path = body.get("path", "")
#     try:
#         import os
#         os.startfile(path)
#         return JSONResponse({"ok": True})
#     except Exception as exc:
#         return JSONResponse({"ok": False, "error": str(exc)})
