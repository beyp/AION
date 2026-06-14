"""
Routes ADO a ajouter dans aion/dashboard/server.py
Colle ces routes a la fin du fichier.
"""

# @app.get("/section/ado", response_class=HTMLResponse)
# async def section_ado(request: Request):
#     return templates.TemplateResponse(
#         request=request,
#         name="sections/ado.html",
#         context={},
#     )
#
#
# @app.post("/ado/get", response_class=HTMLResponse)
# async def ado_get(request: Request):
#     import html as h
#     body = await request.json()
#     result = executor.execute("ado_get_item", body)
#     return HTMLResponse(f'<pre class="ado-result">{h.escape(result)}</pre>')
#
#
# @app.post("/ado/update", response_class=HTMLResponse)
# async def ado_update(request: Request):
#     import html as h
#     body = await request.json()
#     result = executor.execute("ado_update_item", body)
#     ok = "✅" in result
#     color = "var(--green)" if ok else "var(--red)"
#     return HTMLResponse(
#         f'<pre class="ado-result" style="color:{color};">{h.escape(result)}</pre>'
#     )
#
#
# @app.post("/ado/search", response_class=HTMLResponse)
# async def ado_search(request: Request):
#     import html as h
#     body = await request.json()
#     result = executor.execute("ado_search_items", body)
#
#     lines = result.splitlines()
#     html_parts = []
#     type_icons = {
#         "Bug":"🔴","Task":"✅","User Story":"📖","Feature":"⭐","Epic":"🚀"
#     }
#     state_classes = {
#         "Active":"state-active","In Progress":"state-inprogress",
#         "Done":"state-done","Closed":"state-done",
#         "New":"state-new","ToDo":"state-new",
#         "Removed":"state-removed",
#     }
#
#     for line in lines:
#         stripped = line.strip()
#         if not stripped:
#             continue
#         if stripped.startswith("ado_search_items") or stripped.startswith("Filtre"):
#             html_parts.append(
#                 f'<div class="stat-row">'
#                 f'<span style="color:var(--text-dim);font-size:0.82rem;">{h.escape(stripped)}</span>'
#                 f'</div>'
#             )
#         elif stripped.startswith("─"):
#             html_parts.append('<hr style="border-color:var(--border);margin:8px 0;">')
#         elif stripped.startswith(("🔴","✅","📖","⭐","🚀","📌")):
#             # Ligne item : icon #id [state] title
#             import re
#             m = re.match(r'(\S+)\s+#(\d+)\s+\[([^\]]+)\]\s+(.*)', stripped)
#             if m:
#                 icon, wi_id, state, title = m.groups()
#                 state_cls = state_classes.get(state, "state-new")
#                 safe_title = h.escape(title[:60])
#                 html_parts.append(
#                     f'<div class="ado-item-row" onclick="document.getElementById(\'ado-update-id\').value=\'{wi_id}\';adoTab(\'update\');adoLoadItem();" style="cursor:pointer;">'
#                     f'  <span class="ado-id">#{wi_id}</span>'
#                     f'  <span class="ado-state {state_cls}">{h.escape(state)}</span>'
#                     f'  <span class="ado-title">{icon} {safe_title}</span>'
#                     f'  <span style="color:var(--text-dim);font-size:0.75rem;">✏️</span>'
#                     f'</div>'
#                 )
#             else:
#                 html_parts.append(f'<div class="ado-result">{h.escape(stripped)}</div>')
#         elif "aucun item" in stripped.lower():
#             html_parts.append(
#                 f'<div style="color:var(--text-dim);padding:16px;text-align:center;">'
#                 f'😶 {h.escape(stripped)}</div>'
#             )
#
#     return HTMLResponse("\n".join(html_parts) if html_parts else
#                         f'<pre class="ado-result">{h.escape(result)}</pre>')
