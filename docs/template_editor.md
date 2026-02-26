# Template Manager System

A complete template management system for generating price images with dynamic text fields.

## Features

- **Template Management**: Create, edit, and delete templates with background images
- **Visual Editor**: Intuitive interface for positioning text fields
- **Live Preview**: Real-time preview of template with current configuration
- **JSON Configuration**: Flexible JSON-based field configuration
- **Dynamic Rendering**: Generate final images with dynamic data

## Usage

### 1. Creating a Template

1. Navigate to `/template-editor/`
2. Click "Create New Template"
3. Fill in:
   - **Name**: Unique template name (e.g., "USDT Price Template")
   - **Category**: Optional category (e.g., "USDT", "Special Price")
   - **Image**: Upload background image

### 2. Editing a Template

1. Click "Edit" on any template
2. Use the form to add text fields:
   - **Field Name**: Key used in `dynamic_data_dict` (e.g., `english_date`, `buy_price`)
   - **X, Y Coordinates**: Position on image (pixels from top-left)
   - **Font Size**: Text size (8-200)
   - **Color**: Text color (hex format)
   - **Alignment**: Left, Center, or Right
   - **Max Width**: Optional text wrapping width
   - **Font Weight**: Normal, bold, etc.

3. Fields are displayed in the list below
4. Adjust field properties directly in the list
5. Preview updates automatically as you make changes
6. Click "Save Template" when done

### 3. Rendering Final Images

Use the `render_template()` function from `template_editor.utils`:

```python
from template_editor.utils import render_template
from template_editor.models import Template
from PIL import Image

# Get template
template = Template.objects.get(name="USDT Price Template")

# Prepare dynamic data
dynamic_data = {
    'english_date': '2024-01-15',
    'persian_date': '1402/10/25',
    'buy_price': '1,234.56',
    'sell_price': '1,235.00',
    'category_price_1': '1,200.00',
    'category_price_2': '1,300.00',
    'category_price_3': '1,400.00',
}

# Render template
rendered_image = render_template(template, dynamic_data)

# Save or use the image
rendered_image.save('output.png')
# Or send to Telegram, etc.
```

### 4. Example JSON Configuration

The template's `config` field stores JSON like this:

```json
{
  "fields": {
    "english_date": {
      "x": 40,
      "y": 80,
      "size": 32,
      "color": "#000000",
      "align": "left",
      "font_weight": "normal"
    },
    "persian_date": {
      "x": 10,
      "y": 20,
      "size": 28,
      "color": "#333333",
      "align": "right",
      "font_weight": "bold"
    },
    "buy_price": {
      "x": 100,
      "y": 150,
      "size": 48,
      "color": "#00AA00",
      "align": "center",
      "max_width": 300,
      "font_weight": "bold"
    },
    "sell_price": {
      "x": 100,
      "y": 220,
      "size": 48,
      "color": "#AA0000",
      "align": "center",
      "max_width": 300,
      "font_weight": "bold"
    },
    "category_price_1": {
      "x": 50,
      "y": 300,
      "size": 36,
      "color": "#000000",
      "align": "left"
    },
    "category_price_2": {
      "x": 50,
      "y": 350,
      "size": 36,
      "color": "#000000",
      "align": "left"
    },
    "category_price_3": {
      "x": 50,
      "y": 400,
      "size": 36,
      "color": "#000000",
      "align": "left"
    }
  }
}
```

## Field Configuration Options

Each field in the `fields` object supports:

- **x** (integer, required): X coordinate in pixels
- **y** (integer, required): Y coordinate in pixels
- **size** (integer, required): Font size (8-200)
- **color** (string, required): Hex color code (e.g., "#000000")
- **align** (string, optional): "left", "center", or "right" (default: "left")
- **max_width** (integer, optional): Maximum width for text wrapping
- **font_weight** (string, optional): Font weight (e.g., "normal", "bold")

## Integration with Telegram Bot

Example integration:

```python
from template_editor.utils import render_template
from template_editor.models import Template
from io import BytesIO
from telegram_app.services.telegram_service import TelegramService

# Get template
template = Template.objects.get(category="USDT")

# Prepare data
data = {
    'english_date': get_current_date(),
    'persian_date': get_persian_date(),
    'buy_price': format_price(buy_price),
    'sell_price': format_price(sell_price),
}

# Render
image = render_template(template, data)

# Convert to bytes
buffer = BytesIO()
image.convert('RGB').save(buffer, format='PNG')
buffer.seek(0)

# Send to Telegram
telegram_service = TelegramService()
telegram_service.send_photo(channel_id, buffer, caption="Price Update")
```

## Extending for Other Categories

To add support for new categories:

1. **Create a new template** with category name (e.g., "Gold", "Crypto")
2. **Define field names** that match your data structure
3. **Use the visual editor** to position fields
4. **Call `render_template()`** with your category-specific data

Example for a "Gold" category:

```python
template = Template.objects.get(category="Gold")
data = {
    'gold_price_24k': '2,500.00',
    'gold_price_18k': '1,875.00',
    'gold_price_14k': '1,458.33',
    'date': '2024-01-15',
}
image = render_template(template, data)
```

## Notes

- Templates are stored with unique names
- Background images are uploaded to `media/templates/`
- Configuration is stored as JSON in the `config` field
- The system supports RTL text (Persian/Arabic) automatically
- Font path is configured in `settings.TEMPLATE_EDITOR_DEFAULT_FONT`

## API Endpoints

- `GET /template-editor/` - List all templates
- `GET /template-editor/create/` - Create new template
- `GET /template-editor/<id>/edit/` - Edit template
- `POST /template-editor/<id>/edit/` - Save template configuration
- `GET /template-editor/<id>/preview/` - Preview with saved config
- `POST /template-editor/<id>/preview/` - Preview with live config
- `GET /template-editor/<id>/delete/` - Delete template

