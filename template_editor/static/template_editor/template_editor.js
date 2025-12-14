/**
 * Template Editor JavaScript
 * Handles field management and live preview updates
 */

(function() {
    'use strict';

    // Get template ID and initial config
    // Security: Read from json_script element (safer than hidden input with |safe)
    const templateId = document.getElementById('templateId').value;
    const configElement = document.getElementById('template-config-data');
    const initialConfig = configElement ? JSON.parse(configElement.textContent) : {};
    
    // State
    let fields = initialConfig.fields || {};
    let previewTimeout = null;
    
    /**
     * Debounce preview refresh to avoid too many requests
     */
    function debouncePreview() {
        if (previewTimeout) {
            clearTimeout(previewTimeout);
        }
        previewTimeout = setTimeout(refreshPreview, 300); // Wait 300ms after last change
    }

    // DOM Elements
    const addFieldForm = document.getElementById('addFieldForm');
    const fieldsList = document.getElementById('fieldsList');
    const previewImage = document.getElementById('previewImage');
    const refreshPreviewBtn = document.getElementById('refreshPreview');
    const saveBtn = document.getElementById('saveBtn');

    /**
     * Initialize the editor
     */
    function init() {
        // Load existing fields
        renderFieldsList();
        
        // Set up event listeners
        addFieldForm.addEventListener('submit', handleAddField);
        refreshPreviewBtn.addEventListener('click', refreshPreview);
        saveBtn.addEventListener('click', handleSave);
        
        // Auto-refresh preview when fields change
        setupAutoPreview();
    }

    /**
     * Handle adding a new field
     */
    function handleAddField(e) {
        e.preventDefault();
        
        const fieldName = document.getElementById('fieldName').value.trim();
        
        if (!fieldName) {
            alert('Please enter a field name');
            return;
        }
        
        if (fields[fieldName]) {
            if (!confirm(`Field "${fieldName}" already exists. Do you want to update it?`)) {
                return;
            }
        }
        
        // Get field configuration
        const fieldConfig = {
            x: parseInt(document.getElementById('fieldX').value) || 0,
            y: parseInt(document.getElementById('fieldY').value) || 0,
            size: parseInt(document.getElementById('fieldSize').value) || 32,
            color: document.getElementById('fieldColor').value || '#000000',
            align: document.getElementById('fieldAlign').value || 'left',
            font_weight: document.getElementById('fieldWeight').value || 'normal',
        };
        
        const maxWidth = document.getElementById('fieldMaxWidth').value;
        if (maxWidth) {
            fieldConfig.max_width = parseInt(maxWidth);
        }
        
        // Add field
        fields[fieldName] = fieldConfig;
        
        // Clear form
        addFieldForm.reset();
        document.getElementById('fieldX').value = '0';
        document.getElementById('fieldY').value = '0';
        document.getElementById('fieldSize').value = '32';
        document.getElementById('fieldColor').value = '#000000';
        document.getElementById('fieldAlign').value = 'left';
        document.getElementById('fieldWeight').value = 'normal';
        
        // Update UI
        renderFieldsList();
        debouncePreview();
    }

    /**
     * Render the fields list
     */
    function renderFieldsList() {
        if (Object.keys(fields).length === 0) {
            fieldsList.innerHTML = '<p class="text-white-50 text-center">No fields added yet. Add a field above to get started.</p>';
            return;
        }
        
        let html = '';
        for (const [fieldName, config] of Object.entries(fields)) {
            html += `
                <div class="field-item" data-field-name="${fieldName}">
                    <h6>
                        <i class="fas fa-font me-2"></i>
                        ${escapeHtml(fieldName)}
                        <button type="button" class="btn btn-sm btn-danger float-end btn-remove-field" onclick="removeField('${fieldName}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </h6>
                    <div class="field-controls">
                        <div>
                            <label>X:</label>
                            <input type="number" class="form-control form-control-sm" value="${config.x || 0}" 
                                   onchange="updateField('${fieldName}', 'x', this.value)">
                        </div>
                        <div>
                            <label>Y:</label>
                            <input type="number" class="form-control form-control-sm" value="${config.y || 0}" 
                                   onchange="updateField('${fieldName}', 'y', this.value)">
                        </div>
                        <div>
                            <label>Size:</label>
                            <input type="number" class="form-control form-control-sm" value="${config.size || 32}" 
                                   onchange="updateField('${fieldName}', 'size', this.value)" min="8" max="200">
                        </div>
                        <div>
                            <label>Color:</label>
                            <input type="color" class="form-control form-control-sm" value="${config.color || '#000000'}" 
                                   onchange="updateField('${fieldName}', 'color', this.value)" style="height: 32px;">
                        </div>
                        <div>
                            <label>Align:</label>
                            <select class="form-select form-select-sm" onchange="updateField('${fieldName}', 'align', this.value)">
                                <option value="left" ${config.align === 'left' ? 'selected' : ''}>Left</option>
                                <option value="center" ${config.align === 'center' ? 'selected' : ''}>Center</option>
                                <option value="right" ${config.align === 'right' ? 'selected' : ''}>Right</option>
                            </select>
                        </div>
                        <div>
                            <label>Max Width:</label>
                            <input type="number" class="form-control form-control-sm" value="${config.max_width || ''}" 
                                   onchange="updateField('${fieldName}', 'max_width', this.value)" placeholder="Auto">
                        </div>
                    </div>
                </div>
            `;
        }
        
        fieldsList.innerHTML = html;
    }

    /**
     * Update a field configuration
     */
    window.updateField = function(fieldName, key, value) {
        if (!fields[fieldName]) {
            return;
        }
        
        // Convert numeric values
        if (['x', 'y', 'size', 'max_width'].includes(key)) {
            value = value ? parseInt(value) : null;
            if (key === 'max_width' && !value) {
                delete fields[fieldName].max_width;
                // Debounce preview refresh
                debouncePreview();
                return;
            }
        }
        
        fields[fieldName][key] = value;
        // Debounce preview refresh
        debouncePreview();
    };

    /**
     * Remove a field
     */
    window.removeField = function(fieldName) {
        if (!confirm(`Are you sure you want to remove field "${fieldName}"?`)) {
            return;
        }
        
        delete fields[fieldName];
        renderFieldsList();
        debouncePreview();
    };

    /**
     * Refresh preview image
     */
    function refreshPreview() {
        // Send current config to preview endpoint for live preview
        const config = {
            fields: fields
        };
        
        const formData = new FormData();
        formData.append('config', JSON.stringify(config));
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
        
        // Show loading state
        previewImage.style.opacity = '0.5';
        
        fetch(`/template-editor/${templateId}/preview/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => {
            if (response.ok) {
                // Update image source with blob URL
                return response.blob();
            } else {
                throw new Error('Failed to generate preview');
            }
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            previewImage.src = url;
            previewImage.style.opacity = '1';
            // Revoke old URL after a delay to free memory
            setTimeout(() => {
                if (previewImage.src.startsWith('blob:')) {
                    URL.revokeObjectURL(previewImage.src);
                }
            }, 1000);
        })
        .catch(error => {
            console.error('Error refreshing preview:', error);
            previewImage.style.opacity = '1';
            // Fallback to saved config preview
            const timestamp = new Date().getTime();
            previewImage.src = `/template-editor/${templateId}/preview/?t=${timestamp}`;
        });
    }

    /**
     * Setup auto-preview (debounced)
     */
    function setupAutoPreview() {
        // Preview will refresh automatically when fields are updated
        // via the updateField function
    }

    /**
     * Handle save
     */
    function handleSave() {
        const config = {
            fields: fields
        };
        
        // Show loading state
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
        
        // Send to server
        const formData = new FormData();
        formData.append('config', JSON.stringify(config));
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
        
        fetch(`/template-editor/${templateId}/edit/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Template saved successfully!');
                saveBtn.classList.remove('btn-gold');
                saveBtn.classList.add('btn-success');
                saveBtn.innerHTML = '<i class="fas fa-check me-2"></i>Saved!';
                setTimeout(() => {
                    saveBtn.classList.remove('btn-success');
                    saveBtn.classList.add('btn-gold');
                    saveBtn.innerHTML = '<i class="fas fa-save me-2"></i>Save Template';
                }, 2000);
            } else {
                alert('Error: ' + (data.message || 'Failed to save template'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving template. Please try again.');
        })
        .finally(() => {
            saveBtn.disabled = false;
        });
    }

    /**
     * Utility: Escape HTML
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Utility: Get CSRF token from cookie
     */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

