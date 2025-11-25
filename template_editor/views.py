import json
from io import BytesIO
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
            with Image.open(bg_path).convert('RGBA') as img:
                draw = ImageDraw.Draw(img)
                
                # Get configuration - use POST data if available (for live preview), otherwise use saved config
                if request.method == 'POST' and 'config' in request.POST:
                    try:
                        config_data = json.loads(request.POST.get('config', '{}'))
                        config = config_data.get('fields', {})
                    except json.JSONDecodeError:
                        config = template.config.get('fields', {})
                else:
                    config = template.config.get('fields', {})
                
                # Default font path
                font_path = getattr(settings, 'TEMPLATE_EDITOR_DEFAULT_FONT', None)
                
                # Draw each text field
                for field_name, field_config in config.items():
                    x = field_config.get('x', 0)
                    y = field_config.get('y', 0)
                    size = field_config.get('size', 32)
                    color = field_config.get('color', '#000000')
                    align = field_config.get('align', 'left')
                    max_width = field_config.get('max_width')
                    
                    # Get sample text (use field name as preview)
                    sample_text = field_config.get('sample_text', field_name.replace('_', ' ').title())
                    
                    # Load font
                    try:
                        if font_path:
                            font = ImageFont.truetype(font_path, size=size)
                        else:
                            font = ImageFont.load_default()
                    except (OSError, IOError):
                        font = ImageFont.load_default()
                    
                    # Parse color
                    color_rgb = self._parse_color(color)
                    
                    # Draw text
                    if max_width:
                        # Wrap text if max_width is specified
                        lines = self._wrap_text(sample_text, font, max_width, draw)
                        line_height = font.getbbox("Ay")[3] if hasattr(font, 'getbbox') else font.getsize("Ay")[1]
                        for i, line in enumerate(lines):
                            line_y = y + i * (line_height + 4)
                            draw.text((x, line_y), line, font=font, fill=color_rgb)
                    else:
                        draw.text((x, y), sample_text, font=font, fill=color_rgb)
                
                # Convert to RGB for JPEG compatibility
                img_rgb = img.convert('RGB')
                
                # Save to BytesIO
                buffer = BytesIO()
                img_rgb.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Return as HTTP response
                response = HttpResponse(buffer.getvalue(), content_type='image/png')
                return response
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
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
