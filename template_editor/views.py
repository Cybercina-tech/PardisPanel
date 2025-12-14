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
        
        if not template.image:
            return JsonResponse({'error': 'Template has no image.'}, status=400)
        
        try:
            # Load template image
            bg_path = template.image.path
            img = Image.open(bg_path).convert('RGBA')
            draw = ImageDraw.Draw(img)
            
            # Get configuration - use POST data if available (for live preview), otherwise use saved config
            if request.method == 'POST' and 'config' in request.POST:
                try:
                    config_data = json.loads(request.POST.get('config', '{}'))
                    config = config_data.get('fields', {})
                except json.JSONDecodeError:
                    config = (template.config or {}).get('fields', {})
            else:
                config = (template.config or {}).get('fields', {})
            
            self.logger.debug(f"Preview config has {len(config)} fields: {list(config.keys())}")
            
            # Import font utility to avoid code duplication
            from .utils import DEFAULT_FONT_CANDIDATES
            font_candidates = [f for f in DEFAULT_FONT_CANDIDATES if f]
            
            # Draw each text field
            for field_name, field_config in config.items():
                if not isinstance(field_config, dict):
                    continue
                
                x = field_config.get('x', 0)
                y = field_config.get('y', 0)
                size = field_config.get('size', 32)
                color = field_config.get('color', '#000000')
                align = field_config.get('align', 'left')
                max_width = field_config.get('max_width')
                
                # Get sample text (use field name as preview)
                sample_text = field_config.get('sample_text', field_name.replace('_', ' ').title())
                if not sample_text or not str(sample_text).strip():
                    sample_text = field_name.replace('_', ' ').title()
                    if not sample_text:
                        continue
                
                # Check if text is RTL (Persian/Arabic)
                text_to_draw = str(sample_text)
                try:
                    is_rtl = self._is_rtl(text_to_draw)
                    direction = "rtl" if is_rtl else None
                except Exception:
                    direction = None
                
                # Load font using utility function
                from .utils import _get_font
                font = _get_font(size)
                
                # Parse color
                try:
                    color_rgb = self._parse_color(color)
                except Exception:
                    color_rgb = (0, 0, 0)
                
                # Draw text
                try:
                    if max_width:
                        # Wrap text if max_width is specified
                        lines = self._wrap_text(text_to_draw, font, max_width, draw)
                        try:
                            line_height = font.getbbox("Ay")[3] if hasattr(font, 'getbbox') else font.getsize("Ay")[1]
                        except Exception:
                            line_height = size + 4  # Fallback line height
                        for i, line in enumerate(lines):
                            line_y = y + i * (line_height + 4)
                            try:
                                draw.text((x, line_y), line, font=font, fill=color_rgb, direction=direction)
                            except Exception as line_error:
                                # Try without direction if it fails
                                try:
                                    draw.text((x, line_y), line, font=font, fill=color_rgb)
                                except Exception:
                                    self.logger.warning(f"Failed to draw line '{line}' for field '{field_name}': {line_error}")
                    else:
                        try:
                            draw.text((x, y), text_to_draw, font=font, fill=color_rgb, direction=direction)
                        except Exception:
                            # Try without direction if it fails
                            draw.text((x, y), text_to_draw, font=font, fill=color_rgb)
                except Exception as draw_error:
                    self.logger.warning(f"Failed to draw text for field '{field_name}': {draw_error}")
                    # Try to draw without direction as fallback
                    try:
                        draw.text((x, y), str(sample_text), font=font, fill=color_rgb)
                    except Exception:
                        pass
            
            # Convert to RGB for JPEG compatibility
            img_rgb = img.convert('RGB')
            
            # Save to BytesIO
            buffer = BytesIO()
            img_rgb.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Close image to free memory
            img.close()
            img_rgb.close()
            
            # Return as HTTP response
            response = HttpResponse(buffer.getvalue(), content_type='image/png')
            return response
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"Preview error: {error_details}")
            return JsonResponse({'error': str(e), 'details': error_details}, status=500)
    
    def _parse_color(self, color_str):
        """Parse color string to RGB tuple."""
        from .utils import _parse_color as parse_color
        return parse_color(color_str)
    
    def _is_rtl(self, text: str) -> bool:
        """Check if text is right-to-left (Persian/Arabic)."""
        from .utils import _is_rtl
        return _is_rtl(text)
    
    def _wrap_text(self, text, font, max_width, draw):
        """Wrap text to fit within max_width."""
        from .utils import _wrap_text
        return _wrap_text(text, font, max_width, draw)
