import { inject, provide } from 'vue'

export const TEMPLATE_EDITOR_INJECTION_KEY = Symbol('templateEditor')

export function provideTemplateEditor(api) {
  provide(TEMPLATE_EDITOR_INJECTION_KEY, api)
}

export function useTemplateEditorInjected() {
  const te = inject(TEMPLATE_EDITOR_INJECTION_KEY, null)
  if (!te) {
    throw new Error('useTemplateEditorInjected must be used inside TemplateEditor')
  }
  return te
}
