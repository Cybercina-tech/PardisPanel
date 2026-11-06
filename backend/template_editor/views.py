import json
import logging
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View
from PIL import Image, ImageDraw

from .forms import TemplateForm
from .models import Template


class TemplateListView(LoginRequiredMixin, ListView):
    """List all templates."""
    model = Template
    template_name = 'template_editor/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20


class TemplateCreateView(LoginRequiredMixin, CreateView):
    """Create a new template."""
    model = Template
    form_class = TemplateForm
    template_name = 'template_editor/template_form.html'
    success_url = reverse_lazy('template_editor_frontend:list')

    def form_valid(self, form):
        messages.success(self.request, f'Template "{form.instance.name}" created successfully. You can now edit it to add text fields.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        # Add available fonts list
        from .utils import get_available_fonts
        context['available_fonts'] = get_available_fonts()
        return context


class TemplateEditView(LoginRequiredMixin, UpdateView):
    """Edit template with visual editor."""
    model = Template
    form_class = TemplateForm
    template_name = 'template_editor/template_editor.html'
    context_object_name = 'template'

    def get_success_url(self):
        return reverse_lazy('template_editor_frontend:edit', kwargs={'pk': self.object.pk})

    def post(self, request, *args, **kwargs):
        """Handle saving template configuration."""
        self.object = self.get_object()
        
        # Handle image upload
        if 'image' in request.FILES:
            form = self.get_form()
            if form.is_valid():
                self.object = form.save()
                messages.success(request, 'Template image updated successfully.')
                return redirect(self.get_success_url())
        
        # Handle config save
        if 'config' in request.POST:
            try:
                config_data = json.loads(request.POST.get('config', '{}'))
                self.object.config = config_data
                self.object.save()
                messages.success(request, 'Template configuration saved successfully.')
                return JsonResponse({'success': True, 'message': 'Configuration saved successfully.'})
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON configuration.')
                return JsonResponse({'success': False, 'message': 'Invalid JSON configuration.'}, status=400)
        
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        # Security: Pass config dict directly - json_script filter will handle JSON encoding safely
        context['config'] = self.object.config if self.object.config else {}
        # Add available fonts list
        from .utils import get_available_fonts
        context['available_fonts'] = get_available_fonts()
        return context


class TemplateDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a template."""
    model = Template
    template_name = 'template_editor/template_confirm_delete.html'
    success_url = reverse_lazy('template_editor_frontend:list')
    context_object_name = 'template'

    def delete(self, request, *args, **kwargs):
        messages.success(request, f'Template "{self.get_object().name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class PreviewView(LoginRequiredMixin, View):
    """Generate live preview of template with current configuration."""
    
    logger = logging.getLogger(__name__)
    
    def get(self, request, pk):
        return self._render_preview(request, pk)
    
    def post(self, request, pk):
        return self._render_preview(request, pk)
    
    def _render_preview(self, request, pk):
        template = get_object_or_404(Template, pk=pk)

        try:
            # Resolve config: from request body (API or POST) or saved config
            config_data = None
            if request.method == 'POST':
                if hasattr(request, 'data') and request.data:
                    config_data = request.data.get('config')
                if config_data is None and request.POST.get('config'):
                    try:
                        config_data = json.loads(request.POST.get('config', '{}'))
                    except json.JSONDecodeError:
                        pass
            if config_data is None:
                config_data = template.config or {}

            config = config_data if isinstance(config_data, dict) else (template.config or {})
            themes = config.get('themes')

            config_json = getattr(template, 'config_json', None) or {}
            if request.method == 'POST':
                if hasattr(request, 'data') and request.data:
                    cj_override = request.data.get('config_json')
                    if isinstance(cj_override, dict):
                        config_json = cj_override
            widgets_list = config_json.get('widgets') if isinstance(config_json, dict) else None
            # render_template_from_config_json paints its own background when the template has
            # no uploaded image, so canvas-only templates (and brand-new empty ones) preview
            # here instead of failing the legacy path's hard image requirement.
            has_widgets = isinstance(widgets_list, list) and len(widgets_list) > 0
            if not themes and (has_widgets or not template.image):
                from .render_config_json import render_template_from_config_json

                sample_data = {}
                for w in (widgets_list if has_widgets else []):
                    if not isinstance(w, dict):
                        continue
                    st = w.get('style') if isinstance(w.get('style'), dict) else {}
                    pt_raw = st.get('priceTypeId') or st.get('price_type_id')
                    if pt_raw not in (None, ''):
                        try:
                            pt_key = f"price_type__{int(pt_raw)}"
                            if pt_key not in sample_data:
                                from .variables import get_default_sample_value

                                sample_data[pt_key] = get_default_sample_value(pt_key)
                        except (TypeError, ValueError):
                            pass
                    for key in (
                        w.get('bindingKey'),
                        w.get('binding_key'),
                        st.get('bindingKey'),
                        st.get('binding_key'),
                    ):
                        if key and str(key).strip() and str(key) not in sample_data:
                            from .variables import get_default_sample_value

                            sample_data[str(key).strip()] = get_default_sample_value(
                                str(key).strip()
                            )
                img = render_template_from_config_json(
                    template, sample_data, config_json_override=config_json
                )
                buffer = BytesIO()
                img_rgb = img.convert('RGB')
                img_rgb.save(buffer, format='PNG')
                buffer.seek(0)
                img.close()
                img_rgb.close()
                return HttpResponse(buffer.getvalue(), content_type='image/png')

            # New schema: themes with layers — use render_price_template
            if themes:
                theme_name = None
                if request.method == 'POST':
                    if hasattr(request, 'data') and request.data:
                        theme_name = request.data.get('theme_name')
                    if theme_name is None and request.POST.get('theme_name'):
                        theme_name = request.POST.get('theme_name')
                if not theme_name:
                    theme_name = next(iter(themes), None)
                from .render import _get_layers_sorted, render_price_template
                from .variables import get_default_sample_value
                layers = _get_layers_sorted(config, theme_name) if theme_name else []
                sample_data = {}
                for layer in layers:
                    key = layer.get('variable_key') or layer.get('key')
                    if key:
                        sample_data[key] = get_default_sample_value(key)
                img = render_price_template(
                    template,
                    '',
                    sample_data,
                    theme_name_override=theme_name,
                    config_override=config,
                )
                buffer = BytesIO()
                img_rgb = img.convert('RGB')
                img_rgb.save(buffer, format='PNG')
                buffer.seek(0)
                img.close()
                img_rgb.close()
                return HttpResponse(buffer.getvalue(), content_type='image/png')

            # Legacy schema: config['fields'] — draws onto the uploaded background.
            if not template.image:
                return JsonResponse({'error': 'Template has no image.'}, status=400)
            bg_path = template.image.path
            img = Image.open(bg_path).convert('RGBA')
            draw = ImageDraw.Draw(img)

            config_fields = config.get('fields', {})
            self.logger.debug(f"Preview config has {len(config_fields)} fields: {list(config_fields.keys())}")

            from .utils import draw_text_field

            for field_name, field_config in config_fields.items():
                if not isinstance(field_config, dict):
                    continue

                x = field_config.get('x', 0)
                y = field_config.get('y', 0)
                size = field_config.get('size', 32)
                color = field_config.get('color', '#000000')
                align = field_config.get('align', 'left')
                max_width = field_config.get('max_width')
                font_filename = field_config.get('font')

                sample_text = field_config.get('sample_text', field_name.replace('_', ' ').title())
                if not sample_text or not str(sample_text).strip():
                    sample_text = field_name.replace('_', ' ').title()
                if not sample_text:
                    continue

                draw_text_field(
                    draw, x, y, str(sample_text),
                    size=size, color=color, align=align, max_width=max_width,
                    font_filename=font_filename,
                )

            img_rgb = img.convert('RGB')
            buffer = BytesIO()
            img_rgb.save(buffer, format='PNG')
            buffer.seek(0)
            img.close()
            img_rgb.close()
            return HttpResponse(buffer.getvalue(), content_type='image/png')

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"Preview error: {error_details}")
            return JsonResponse({'error': str(e), 'details': error_details}, status=500)
