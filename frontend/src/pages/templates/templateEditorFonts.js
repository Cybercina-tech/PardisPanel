/** Map font filename to a safe CSS font-family token (matches injected @font-face). */
export function editorFontFamilyToken(filename) {
  if (!filename || typeof filename !== 'string') return ''
  const safe = filename.replace(/[^a-zA-Z0-9_-]/g, '_')
  return `TE_${safe}`
}

/**
 * Absolute URL path for a font binary. Uses signed query ?t=... because @font-face cannot
 * send Authorization: Bearer (JWT). Tokens come from GET /api/template-editor/fonts/.
 */
export function templateEditorFontFaceUrl(filename, faceToken) {
  if (!filename || typeof filename !== 'string') return ''
  if (!faceToken || typeof faceToken !== 'string') return ''
  const enc = encodeURIComponent(filename)
  const t = encodeURIComponent(faceToken)
  return `/api/template-editor/fonts/file/${enc}/?t=${t}`
}

/**
 * Inject @font-face rules for template editor preview (fonts API file endpoint).
 * Call once after fetching GET /api/template-editor/fonts/.
 */
export function injectTemplateEditorFontFaces(fontList) {
  if (!Array.isArray(fontList) || !fontList.length) return
  const id = 'template-editor-font-faces'
  let el = document.getElementById(id)
  if (!el) {
    el = document.createElement('style')
    el.id = id
    document.head.appendChild(el)
  }
  const rules = fontList
    .filter((f) => f && f.filename && f.face_token)
    .map((f) => {
      const token = editorFontFamilyToken(f.filename)
      const url = templateEditorFontFaceUrl(f.filename, f.face_token).replace(/'/g, "\\'")
      const fmt = String(f.filename).toLowerCase().endsWith('.otf') ? 'opentype' : 'truetype'
      return `@font-face{font-family:'${token}';src:url('${url}') format('${fmt}');font-display:swap;}`
    })
  el.textContent = rules.join('\n')
}
