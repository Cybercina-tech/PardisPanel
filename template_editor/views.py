import json
import logging
from io import BytesIO
from pathlib import Path
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings

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
        context['config'] = json.dumps(self.object.config if self.object.config else {})
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
            
            # Debug: log config
            logger = logging.getLogger(__name__)
            logger.debug(f"Preview config has {len(config)} fields: {list(config.keys())}")
            
            # Default font path - prioritize Persian fonts
            STATIC_ROOT_DIR = Path(settings.BASE_DIR) / "static"
            FONT_ROOT = Path(getattr(settings, "PRICE_RENDERER_FONT_ROOT", STATIC_ROOT_DIR / "fonts"))
            
            font_candidates = [
                getattr(settings, 'TEMPLATE_EDITOR_DEFAULT_FONT', None),
                str(FONT_ROOT / "YekanBakh.ttf"),  # Persian font
                str(FONT_ROOT / "Morabba.ttf"),    # Persian font
            ]
            
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
                    # If no sample text, use field name as fallback
                    sample_text = field_name.replace('_', ' ').title()
                    if not sample_text:
                        continue
                
                    # Check if text is RTL (Persian/Arabic)
                    try:
                        is_rtl = self._is_rtl(str(sample_text))
                        direction = "rtl" if is_rtl else None
                        text_to_draw = str(sample_text)
                    except Exception:
                        text_to_draw = str(sample_text)
                        direction = None
                
                # Load font - try Persian fonts first
                font = None
                for font_path in font_candidates:
                    if not font_path:
                        continue
                    try:
                        font_file = Path(font_path)
                        if font_file.exists():
                            font = ImageFont.truetype(str(font_file), size=size)
                            break
                    except (OSError, IOError, TypeError) as e:
                        logger = logging.getLogger(__name__)
                        logger.debug(f"Failed to load font '{font_path}': {e}")
                        continue
                
                if font is None:
                    try:
                        font = ImageFont.load_default()
                    except Exception as e:
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to load default font: {e}")
                        # Don't skip - try to draw anyway
                        font = ImageFont.load_default()
                
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
                                    logger = logging.getLogger(__name__)
                                    logger.warning(f"Failed to draw line '{line}' for field '{field_name}': {line_error}")
                    else:
                        try:
                            draw.text((x, y), text_to_draw, font=font, fill=color_rgb, direction=direction)
                        except Exception:
                            # Try without direction if it fails
                            draw.text((x, y), text_to_draw, font=font, fill=color_rgb)
                except Exception as draw_error:
                    # Log drawing error but continue with other fields
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to draw text for field '{field_name}': {draw_error}")
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
            logger = logging.getLogger(__name__)
            logger.error(f"Preview error: {error_details}")
            return JsonResponse({'error': str(e), 'details': error_details}, status=500)
    
    def _parse_color(self, color_str):
        """Parse color string to RGB tuple."""
        if not color_str:
            return (0, 0, 0)
        color_str = color_str.strip()
        if color_str.startswith('#'):
            color_str = color_str[1:]
        if len(color_str) == 3:
            color_str = ''.join(c * 2 for c in color_str)
        try:
            return tuple(int(color_str[i:i+2], 16) for i in range(0, 6, 2))
        except ValueError:
            return (0, 0, 0)
    
    def _is_rtl(self, text: str) -> bool:
        """Check if text is right-to-left (Persian/Arabic)."""
        for char in text:
            if "\u0600" <= char <= "\u06FF" or "\u0750" <= char <= "\u077F":
                return True
        return False
    
    def _wrap_text(self, text, font, max_width, draw):
        """Wrap text to fit within max_width."""
        if not text:
            return ['']
        words = text.split()
        if not words:
            return [text]
        
        lines = []
        current_line = words[0]
        
        for word in words[1:]:
            trial_line = f"{current_line} {word}"
            if hasattr(draw, 'textlength'):
                width = draw.textlength(trial_line, font=font)
            elif hasattr(font, 'getlength'):
                width = font.getlength(trial_line)
            else:
                width = font.getsize(trial_line)[0]
            
            if width <= max_width:
                current_line = trial_line
            else:
                lines.append(current_line)
                current_line = word
        
        lines.append(current_line)
        return lines
