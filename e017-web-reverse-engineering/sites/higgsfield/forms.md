# higgsfield.ai — Form Structure

## Image Generation Form (`/ai/image`)

### Fields

| Field | Type | Parameter | Values |
|-------|------|-----------|--------|
| Prompt | textbox | prompt | Free text |
| Model | button (dropdown) | model | See models.md |
| Resolution | button (dropdown) | width, height | 1K (512), 2K (1024), 4K (2048) |
| Aspect Ratio | button (dropdown) | aspect_ratio | 1:1, 3:4, 4:3, 9:16, 16:9, 2:3, 3:2, 21:9 |
| Batch Size | slider + buttons | batch_size | 1-4 (Decrement/Increment) |
| Unlimited | switch | use_unlim | true/false |
| Upload | file input | input_images | Image files |
| Draw | button | - | Opens drawing mode |

### How Each Control Maps to API

**Model selector** (button with model name):
- Click opens dialog with Featured + All models
- Each model is a button with text like "Seedream 4.5 UNLIMITED"
- Clicking selects the model → sets `model` parameter

**Resolution** (button showing "2K"):
- Click opens dropdown: 1K, 2K, 4K
- Sets `width` and `height` parameters

**Aspect Ratio** (button showing "3:4"):
- Click opens dropdown with ratios
- Sets `aspect_ratio` parameter

**Batch Size** (slider + Decrement/Increment):
- Shows current count (e.g., "1/4")
- Decrement/Increment buttons change batch_size
- Sets `batch_size` parameter

**Unlimited** (switch):
- Toggle on/off
- Sets `use_unlim` parameter
- Also changes Generate button text to "Unlimited"

**Generate/Unlimited** (submit button):
- Text changes based on Unlimited state
- Submits form with all parameters

### Form Data Model

The form has `data-model` attribute on the fieldset:
```html
<fieldset data-model="seedream_v4_5">
```

### Submit Button Name

```html
<button name="hf:image-form-submit">Generate 1</button>
```

### Prompt Input Name

```html
<textarea name="hf:tour-image-prompt">...</textarea>
```

## Video Generation Form (`/ai/video`)

### Fields

| Field | Type | Parameter | Values |
|-------|------|-----------|--------|
| Prompt | textbox | prompt | Free text |
| Upload | area | input_images | Image/Video/Audio |
| Model | button | model | See video models |
| Duration | slider | duration | 4-15 seconds |
| Ratio | button | aspect_ratio | Auto, 16:9, 9:16, etc. |
| Resolution | button | resolution | Depends on model |
| Bitrate | button | bitrate | Depends on model |

## Notes

- Some buttons don't have `name` attributes — they modify internal state
- The actual parameters sent to server are in the request body, not form attributes
- To discover exact parameters, capture a HAR while submitting the form
