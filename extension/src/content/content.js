const API_URL = 'http://localhost:8001';

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}

function initialize() {
  console.log('ApplyEase: Content script initialized');
  
  if (isApplicationPage()) {
    injectUI();
    detectFormFields();
    monitorFormSubmission();
  }
  
  chrome.runtime.onMessage.addListener(handleMessage);
}

function isApplicationPage() {
  const url = window.location.href.toLowerCase();
  const title = document.title.toLowerCase();
  const body = document.body.innerText.toLowerCase();
  
  const keywords = ['apply', 'application', 'career', 'job', 'position', 'opportunity', 'workday', 'greenhouse', 'lever', 'taleo'];
  
  return keywords.some(keyword => 
    url.includes(keyword) || title.includes(keyword) || body.includes(keyword)
  );
}

function injectUI() {
  const fab = document.createElement('div');
  fab.id = 'applyease-fab';
  fab.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
      <path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>
    </svg>
  `;
  fab.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    transition: transform 0.3s ease;
  `;
  
  fab.addEventListener('mouseenter', () => {
    fab.style.transform = 'scale(1.1)';
  });
  
  fab.addEventListener('mouseleave', () => {
    fab.style.transform = 'scale(1)';
  });
  
  fab.addEventListener('click', togglePanel);
  
  document.body.appendChild(fab);
  
  // Create side panel
  const panel = document.createElement('div');
  panel.id = 'applyease-panel';
  panel.innerHTML = `
    <div class="applyease-header">
      <h2>ApplyEase AI Assistant</h2>
      <button id="applyease-close">&times;</button>
    </div>
    <div class="applyease-content">
      <div id="applyease-status">Analyzing form...</div>
      <div id="applyease-fields"></div>
      <div id="applyease-actions">
        <button id="applyease-autofill" class="applyease-btn applyease-btn-primary">Auto-Fill Form</button>
        <button id="applyease-detect" class="applyease-btn">Re-Detect Fields</button>
        <button id="applyease-save" class="applyease-btn">Save Application</button>
      </div>
      <div id="applyease-chat" style="display: none;">
        <div id="applyease-messages"></div>
        <div class="applyease-input-group">
          <input type="text" id="applyease-chat-input" placeholder="Ask AI for help...">
          <button id="applyease-chat-send">Send</button>
        </div>
      </div>
    </div>
  `;
  panel.style.cssText = `
    position: fixed;
    top: 0;
    right: -400px;
    width: 400px;
    height: 100%;
    background: white;
    box-shadow: -2px 0 10px rgba(0,0,0,0.1);
    z-index: 10000;
    transition: right 0.3s ease;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  `;
  
  document.body.appendChild(panel);
  
  // Add styles
  const styles = document.createElement('style');
  styles.textContent = `
    #applyease-panel * {
      box-sizing: border-box;
    }
    
    .applyease-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .applyease-header h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
    
    #applyease-close {
      background: none;
      border: none;
      color: white;
      font-size: 28px;
      cursor: pointer;
      padding: 0;
      width: 30px;
      height: 30px;
      line-height: 1;
    }
    
    .applyease-content {
      padding: 20px;
      height: calc(100% - 70px);
      overflow-y: auto;
    }
    
    #applyease-status {
      padding: 12px;
      background: #f7fafc;
      border-radius: 8px;
      margin-bottom: 20px;
      font-size: 14px;
      color: #4a5568;
    }
    
    #applyease-fields {
      margin-bottom: 20px;
    }
    
    .applyease-field {
      margin-bottom: 15px;
      padding: 12px;
      background: #f7fafc;
      border-radius: 8px;
      border-left: 3px solid #667eea;
    }
    
    .applyease-field-label {
      font-weight: 600;
      color: #2d3748;
      margin-bottom: 5px;
      font-size: 14px;
    }
    
    .applyease-field-type {
      display: inline-block;
      padding: 2px 8px;
      background: #667eea;
      color: white;
      border-radius: 12px;
      font-size: 11px;
      margin-left: 8px;
    }
    
    .applyease-field-value {
      margin-top: 8px;
      padding: 8px;
      background: white;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      font-size: 13px;
      color: #4a5568;
    }
    
    #applyease-actions {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
    }
    
    .applyease-btn {
      flex: 1;
      padding: 10px 16px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      background: white;
      color: #4a5568;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .applyease-btn:hover {
      background: #f7fafc;
    }
    
    .applyease-btn-primary {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
    }
    
    .applyease-btn-primary:hover {
      opacity: 0.9;
    }
    
    #applyease-chat {
      border-top: 1px solid #e2e8f0;
      padding-top: 20px;
    }
    
    #applyease-messages {
      height: 300px;
      overflow-y: auto;
      margin-bottom: 15px;
      padding: 10px;
      background: #f7fafc;
      border-radius: 8px;
    }
    
    .applyease-message {
      margin-bottom: 12px;
      padding: 8px 12px;
      border-radius: 8px;
      max-width: 80%;
    }
    
    .applyease-message.user {
      background: #667eea;
      color: white;
      margin-left: auto;
      text-align: right;
    }
    
    .applyease-message.assistant {
      background: white;
      border: 1px solid #e2e8f0;
      color: #2d3748;
    }
    
    .applyease-input-group {
      display: flex;
      gap: 8px;
    }
    
    #applyease-chat-input {
      flex: 1;
      padding: 10px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 14px;
    }
    
    #applyease-chat-send {
      padding: 10px 20px;
      background: #667eea;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 500;
    }
    
    #applyease-chat-send:hover {
      background: #5a67d8;
    }
  `;
  
  document.head.appendChild(styles);
  
  // Add event listeners
  document.getElementById('applyease-close').addEventListener('click', togglePanel);
  document.getElementById('applyease-autofill').addEventListener('click', autoFillForm);
  document.getElementById('applyease-detect').addEventListener('click', detectFormFields);
  document.getElementById('applyease-save').addEventListener('click', saveApplication);
  document.getElementById('applyease-chat-send').addEventListener('click', sendChatMessage);
  document.getElementById('applyease-chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
  });
}

// Toggle side panel
function togglePanel() {
  const panel = document.getElementById('applyease-panel');
  if (panel.style.right === '0px') {
    panel.style.right = '-400px';
  } else {
    panel.style.right = '0px';
  }
}

// Detect form fields on the page
function detectFormFields() {
  console.log('ApplyEase: Detecting form fields...');
  
  const fields = [];
  const fieldGroups = [];
  const formElements = document.querySelectorAll('input, textarea, select');
  
  formElements.forEach((element, index) => {
    if (element.type === 'hidden' || element.type === 'submit' || element.type === 'button') {
      return;
    }
    
    const field = {
      id: element.id || `field_${index}`,
      name: element.name || '',
      type: element.type || element.tagName.toLowerCase(),
      label: getFieldLabel(element),
      placeholder: element.placeholder || '',
      required: element.required,
      value: element.value || '',
      maxLength: element.maxLength || null,
      element: element,
      // Add grouping info
      parent: element.parentElement?.className || '',
      fieldset: element.closest('fieldset')?.querySelector('legend')?.textContent || null
    };
    
    fields.push(field);
  });
  
  // Group related fields (radio buttons, checkboxes with same name)
  const groupedByName = {};
  fields.forEach(field => {
    if ((field.type === 'radio' || field.type === 'checkbox') && field.name) {
      if (!groupedByName[field.name]) {
        groupedByName[field.name] = [];
      }
      groupedByName[field.name].push(field);
    }
  });
  
  console.log('Field groups detected:', Object.keys(groupedByName).length);
  
  // Group fields by question (for radio/checkbox groups)
  const groupedFields = groupFieldsByQuestion(fields);
  
  console.log('Total fields:', fields.length);
  console.log('Grouped questions:', groupedFields.length);
  
  // Send grouped fields to background script for classification
  chrome.runtime.sendMessage({
    action: 'classifyFields',
    fields: groupedFields.map(f => ({
      id: f.id,
      name: f.name,
      type: f.type,
      label: f.label,
      placeholder: f.placeholder,
      required: f.required,
      maxLength: f.maxLength,
      isGroup: f.isGroup,
      options: f.options,
      fieldset: f.fieldset
    })),
    url: window.location.href
  }, (response) => {
    console.log('Backend response:', response);
    if (response) {
      displayClassifiedFields(response, groupedFields);
      window.applyEaseFields = groupedFields;
      window.applyEaseSuggestions = response.suggestions || {};
      
      console.log('Stored grouped fields:', window.applyEaseFields.length);
      console.log('Stored suggestions:', Object.keys(window.applyEaseSuggestions).length);
    }
  });
  
  updateStatus(`Found ${fields.length} form fields (${groupedFields.length} questions)`);
}

// Group fields by question (combine radio/checkbox with same name)
function groupFieldsByQuestion(fields) {
  const grouped = [];
  const processed = new Set();
  
  fields.forEach(field => {
    if (processed.has(field.id)) return;
    
    // Check if this is part of a radio/checkbox group
    if ((field.type === 'radio' || field.type === 'checkbox') && field.name) {
      // Find all fields with same name
      const siblings = fields.filter(f => 
        f.name === field.name && 
        (f.type === 'radio' || f.type === 'checkbox')
      );
      
      if (siblings.length > 1) {
        // This is a group - combine them
        const groupLabel = field.label || field.fieldset || field.name;
        const options = siblings.map(f => ({
          id: f.id,
          label: f.label || f.value,
          value: f.value,
          element: f.element
        }));
        
        grouped.push({
          id: `group_${field.name}`,
          name: field.name,
          type: field.type,
          label: groupLabel,
          placeholder: '',
          required: field.required,
          isGroup: true,
          options: options,
          fieldset: field.fieldset,
          elements: siblings.map(s => s.element),
          // Keep reference to first element for compatibility
          element: field.element
        });
        
        // Mark all siblings as processed
        siblings.forEach(s => processed.add(s.id));
      } else {
        // Single field
        grouped.push(field);
        processed.add(field.id);
      }
    } else {
      // Regular field (text, textarea, select, etc.)
      grouped.push(field);
      processed.add(field.id);
    }
  });
  
  return grouped;
}

// Get label for a form field
function getFieldLabel(element) {
  // Check for associated label
  const label = element.labels && element.labels[0];
  if (label) {
    return label.innerText.trim();
  }
  
  // Check for aria-label
  if (element.getAttribute('aria-label')) {
    return element.getAttribute('aria-label');
  }
  
  // Check for nearby text
  const parent = element.parentElement;
  if (parent) {
    const text = parent.innerText || parent.textContent;
    if (text && text.length < 100) {
      return text.trim().split('\n')[0];
    }
  }
  
  // Use placeholder as fallback
  return element.placeholder || element.name || '';
}

// Display classified fields in the panel
function displayClassifiedFields(classifiedFields, allFields) {
  console.log('Displaying classified fields:', classifiedFields);
  console.log('  Standard fields:', classifiedFields.standard_fields?.length || 0);
  console.log('  Unique fields:', classifiedFields.unique_fields?.length || 0);
  console.log('  Suggestions:', classifiedFields.suggestions);
  
  const container = document.getElementById('applyease-fields');
  container.innerHTML = '';
  
  const standardCount = classifiedFields.standard_fields?.length || 0;
  const uniqueCount = classifiedFields.unique_fields?.length || 0;
  
  // Show summary
  const summary = document.createElement('div');
  summary.innerHTML = `
    <div style="margin-bottom: 15px; padding: 10px; background: #edf2f7; border-radius: 6px; font-size: 13px;">
      <strong>${standardCount}</strong> standard fields (auto-fill ready)<br>
      <strong>${uniqueCount}</strong> unique fields (AI assistance needed)
    </div>
  `;
  container.appendChild(summary);
  
  // Show standard fields list
  if (standardCount > 0) {
    const standardHeader = document.createElement('div');
    standardHeader.innerHTML = '<h4 style="margin: 15px 0 10px; color: #2d3748; font-size: 14px;">Standard Fields Detected:</h4>';
    container.appendChild(standardHeader);
    
    classifiedFields.standard_fields.forEach(field => {
      const actualField = allFields.find(f => f.id === field.id);
      const suggestion = classifiedFields.suggestions[field.id];
      
      const fieldDiv = document.createElement('div');
      fieldDiv.innerHTML = `
        <div style="background: #f7fafc; padding: 8px; border-radius: 4px; margin-bottom: 6px; border-left: 3px solid #48bb78; font-size: 12px; cursor: pointer;" class="highlight-field" data-field-id="${field.id}">
          <strong>${field.label || field.name}</strong>
          <span style="background: #48bb78; color: white; padding: 2px 6px; border-radius: 10px; font-size: 10px; margin-left: 6px;">${field.classified_as}</span>
          ${suggestion ? `<div style="color: #718096; font-size: 11px; margin-top: 2px;">→ ${suggestion.substring(0, 50)}${suggestion.length > 50 ? '...' : ''}</div>` : ''}
        </div>
      `;
      container.appendChild(fieldDiv);
      
      // Add highlight on hover
      setTimeout(() => {
        const div = fieldDiv.querySelector('.highlight-field');
        if (div && actualField) {
          div.addEventListener('mouseenter', () => {
            actualField.element.style.outline = '3px solid #48bb78';
            actualField.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          });
          div.addEventListener('mouseleave', () => {
            actualField.element.style.outline = '';
          });
        }
      }, 0);
    });
  }
  
  // Auto-fill standard fields immediately if we have suggestions
  const hasSuggestions = Object.keys(classifiedFields.suggestions || {}).length > 0;
  if (hasSuggestions && standardCount > 0) {
    const autoFillNotice = document.createElement('div');
    autoFillNotice.innerHTML = `
      <div style="margin-bottom: 15px; padding: 10px; background: #c6f6d5; border-radius: 6px; font-size: 12px; color: #22543d;">
        Click "Auto-Fill Form" button below to fill all standard fields.
      </div>
    `;
    container.appendChild(autoFillNotice);
  }
  
  // Show unique fields that need attention
  if (uniqueCount > 0) {
    const uniqueHeader = document.createElement('div');
    uniqueHeader.innerHTML = '<h4 style="margin: 15px 0 10px; color: #2d3748; font-size: 14px;">Unique Fields - AI Assistance:</h4>';
    container.appendChild(uniqueHeader);
    
    classifiedFields.unique_fields.forEach(field => {
      // Find the actual field in allFields
      const actualField = allFields.find(f => f.id === field.id);
      
      const fieldDiv = document.createElement('div');
      fieldDiv.className = 'applyease-field';
      
      // Check if this is a grouped field (radio/checkbox group)
      if (field.isGroup && field.options) {
        // Display question with actual answer options + AI option
        const optionsHTML = field.options.map((opt, optIdx) => `
          <label style="display: block; padding: 8px; background: white; border: 1px solid #e2e8f0; border-radius: 4px; margin-bottom: 4px; cursor: pointer; font-size: 12px; transition: all 0.2s;">
            <input 
              type="radio" 
              name="applyease_${field.id}" 
              value="${opt.value}"
              data-field-id="${field.id}"
              data-option-index="${optIdx}"
              style="margin-right: 8px; accent-color: #667eea;">
            ${opt.label || opt.value}
          </label>
        `).join('');
        
        fieldDiv.innerHTML = `
          <div class="applyease-field-label" style="margin-bottom: 8px;">
            <strong style="color: #2d3748; font-size: 13px;">${field.label || field.name}</strong>
            <span class="applyease-field-type" style="background: #9f7aea; margin-left: 8px;">Question</span>
          </div>
          <div class="applyease-field-value" id="preview_${field.id}" style="background: #faf5ff; padding: 10px; border-radius: 6px; border: 1px solid #e9d8fd;">
            <div style="font-size: 11px; color: #6b46c1; margin-bottom: 8px; font-weight: 600;">
              Select your answer:
            </div>
            ${optionsHTML}
            <label style="display: block; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 4px; margin-top: 6px; cursor: pointer; font-size: 12px; color: white; font-weight: 600; text-align: center; transition: all 0.2s;">
              <input 
                type="radio" 
                name="applyease_${field.id}" 
                value="ai_generate"
                data-field-id="${field.id}"
                data-is-ai="true"
                style="margin-right: 8px; accent-color: white;">
              AI Response (Recommended)
            </label>
          </div>
        `;
        
        // Add change handlers and hover effects
        setTimeout(() => {
          document.querySelectorAll(`input[name="applyease_${field.id}"]`).forEach(radio => {
            const label = radio.parentElement;
            
            // Hover effect
            label.addEventListener('mouseenter', () => {
              if (!radio.dataset.isAi) {
                label.style.background = '#edf2f7';
                label.style.borderColor = '#667eea';
              } else {
                label.style.opacity = '0.9';
              }
            });
            
            label.addEventListener('mouseleave', () => {
              if (!radio.dataset.isAi) {
                label.style.background = 'white';
                label.style.borderColor = '#e2e8f0';
              } else {
                label.style.opacity = '1';
              }
            });
            
            // Change handler
            radio.addEventListener('change', (e) => {
              if (e.target.dataset.isAi === 'true') {
                // AI option selected - generate and apply
                updateStatus('Generating AI response...');
                generateAndApplyGroupResponse(field);
              } else {
                // Direct option selected - apply immediately
                applyGroupOption(field, parseInt(e.target.dataset.optionIndex));
              }
            });
          });
        }, 0);
      } else {
        // Individual field
        fieldDiv.innerHTML = `
          <div class="applyease-field-label">
            ${field.label || field.name}
            <span class="applyease-field-type">AI</span>
          </div>
          <div style="font-size: 11px; color: #a0aec0; margin: 4px 0;">
            Field: ${field.type} ${field.fieldset ? `• Group: ${field.fieldset}` : ''}
          </div>
          <div class="applyease-field-value" id="preview_${field.id}">
            <button 
              class="applyease-generate-btn applyease-highlight-field" 
              data-field-id="${field.id}"
              style="
                width: 100%;
                padding: 8px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
              ">
              Generate AI Response
            </button>
          </div>
        `;
      }
      
      container.appendChild(fieldDiv);
      
      // Add click handler for generate button
      setTimeout(() => {
        const btn = fieldDiv.querySelector('.applyease-generate-btn');
        if (btn) {
          btn.addEventListener('click', () => generateAndDisplayResponse(actualField || field));
          
          // Highlight actual field(s) on hover
          btn.addEventListener('mouseenter', () => {
            if (field.isGroup && field.elements) {
              // Highlight all elements in the group
              field.elements.forEach(el => {
                el.style.outline = '3px solid #667eea';
              });
              if (field.elements[0]) {
                field.elements[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
            } else if (actualField && actualField.element) {
              actualField.element.style.outline = '3px solid #667eea';
              actualField.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
          
          btn.addEventListener('mouseleave', () => {
            if (field.isGroup && field.elements) {
              field.elements.forEach(el => {
                el.style.outline = '';
              });
            } else if (actualField && actualField.element) {
              actualField.element.style.outline = '';
            }
          });
        }
      }, 0);
    });
  }
  
  // Enable chat for unique fields
  if (uniqueCount > 0) {
    document.getElementById('applyease-chat').style.display = 'block';
  }
}

// Auto-fill form
async function autoFillForm() {
  console.log('ApplyEase: Auto-filling form...');
  updateStatus('Auto-filling standard fields...');
  
  const fields = window.applyEaseFields || [];
  const suggestions = window.applyEaseSuggestions || {};
  
  console.log('Auto-fill starting with:');
  console.log('  Total fields:', fields.length);
  console.log('  Suggestions available:', Object.keys(suggestions).length);
  console.log('  Suggestions:', suggestions);
  
  let filledCount = 0;
  
  // Fill standard fields ONLY
  for (const field of fields) {
    if (suggestions[field.id]) {
      console.log(`Filling field "${field.label}" (${field.id}) with: ${suggestions[field.id]}`);
      
      // Check if element still exists in DOM
      if (!document.body.contains(field.element)) {
        console.warn(`Field element no longer in DOM: ${field.id}`);
        continue;
      }
      
      field.element.value = suggestions[field.id];
      field.element.dispatchEvent(new Event('input', { bubbles: true }));
      field.element.dispatchEvent(new Event('change', { bubbles: true }));
      field.element.dispatchEvent(new Event('blur', { bubbles: true }));
      filledCount++;
      
      // Visual feedback
      field.element.style.background = '#c6f6d5';
      setTimeout(() => {
        field.element.style.background = '';
      }, 1000);
    } else {
      console.log(`No suggestion for field: ${field.label} (${field.id})`);
    }
  }
  
  console.log(`Auto-fill complete: ${filledCount} fields filled`);
  updateStatus(`Filled ${filledCount} standard fields. Generate responses for unique fields below.`);
}

// Generate and display AI response for a unique field
async function generateAndDisplayResponse(field) {
  const previewDiv = document.getElementById(`preview_${field.id}`);
  if (!previewDiv) return;
  
  // Render loading state
  previewDiv.innerHTML = '<div style="text-align: center; padding: 10px; color: #667eea;">Generating response...</div>';
  
  try {
    const response = await generateAIResponse(field);
    
    if (response) {
      // Show the generated response with edit and apply buttons
      previewDiv.innerHTML = `
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 4px; padding: 8px; margin-bottom: 8px;">
          <textarea 
            id="response_${field.id}" 
            style="width: 100%; min-height: 80px; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px; font-size: 12px; resize: vertical;"
          >${response}</textarea>
        </div>
        <div style="display: flex; gap: 6px;">
          <button 
            class="applyease-apply-btn" 
            data-field-id="${field.id}"
            style="flex: 1; padding: 6px; background: #48bb78; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 500;">
            Apply to Form
          </button>
          <button 
            class="applyease-regenerate-btn" 
            data-field-id="${field.id}"
            style="flex: 1; padding: 6px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 500;">
            Regenerate
          </button>
        </div>
      `;
      
      // Add event listeners
      const applyBtn = previewDiv.querySelector('.applyease-apply-btn');
      const regenerateBtn = previewDiv.querySelector('.applyease-regenerate-btn');
      
      if (applyBtn) {
        applyBtn.addEventListener('click', () => applyResponseToField(field, response));
      }
      
      if (regenerateBtn) {
        regenerateBtn.addEventListener('click', () => generateAndDisplayResponse(field));
      }
      
    } else {
      previewDiv.innerHTML = '<div style="color: #c53030; font-size: 12px;">Failed to generate response. Try again or use the chat below.</div>';
    }
  } catch (error) {
    console.error('Error generating response:', error);
    previewDiv.innerHTML = '<div style="color: #c53030; font-size: 12px;">Error generating response. Try again.</div>';
  }
}

// Handle AI generation for grouped fields
async function generateAndApplyGroupResponse(field) {
  console.log('Generating AI response for grouped field:', field.label);
  
  const response = await generateAIResponse(field);
  
  if (response) {
    // Find and select the matching option
    applyResponseToField(field, response);
  }
}

// Apply user-selected option directly to form
function applyGroupOption(field, optionIndex) {
  if (!field.options || !field.options[optionIndex]) return;
  
  const selectedOption = field.options[optionIndex];
  console.log(`User selected option: ${selectedOption.label} (${selectedOption.value})`);
  
  // Apply to actual form field
  if (selectedOption.element) {
    if (field.type === 'radio') {
      selectedOption.element.checked = true;
    } else if (field.type === 'checkbox') {
      selectedOption.element.checked = true;
    }
    selectedOption.element.dispatchEvent(new Event('change', { bubbles: true }));
    selectedOption.element.dispatchEvent(new Event('click', { bubbles: true }));
    
  // Visual feedback on filled field
    selectedOption.element.parentElement.style.background = '#c6f6d5';
    setTimeout(() => {
      selectedOption.element.parentElement.style.background = '';
    }, 1500);
    
    updateStatus(`✓ Selected: ${selectedOption.label || selectedOption.value}`);
  }
}

// Apply AI-generated response to the actual form field
function applyResponseToField(field, response) {
  const textarea = document.getElementById(`response_${field.id}`);
  const finalResponse = textarea ? textarea.value : response;
  
  // Handle grouped fields (radio/checkbox)
  if (field.isGroup && field.options) {
    console.log(`Applying response to grouped field: ${field.label}`);
    console.log(`Response: ${finalResponse}`);
    console.log(`Options: ${field.options.map(o => o.value).join(', ')}`);
    
    // Find matching option (case-insensitive partial match)
    const responseLower = finalResponse.toLowerCase();
    let matchedOption = field.options.find(opt => {
      const optionValue = (opt.value || opt.label || '').toLowerCase();
      return responseLower.includes(optionValue) || optionValue.includes(responseLower.split(' ')[0]);
    });
    
    // If no match, try common patterns
    if (!matchedOption) {
      if (responseLower.includes('yes') || responseLower.includes('authorize')) {
        matchedOption = field.options.find(opt => (opt.value || '').toLowerCase() === 'yes');
      } else if (responseLower.includes('no')) {
        matchedOption = field.options.find(opt => (opt.value || '').toLowerCase() === 'no');
      }
    }
    
    if (matchedOption && matchedOption.element) {
      // Select the appropriate radio/checkbox
      if (field.type === 'radio') {
        matchedOption.element.checked = true;
      } else if (field.type === 'checkbox') {
        matchedOption.element.checked = true;
      }
      matchedOption.element.dispatchEvent(new Event('change', { bubbles: true }));
      matchedOption.element.dispatchEvent(new Event('click', { bubbles: true }));
      
    // Visual feedback on all group elements
      field.elements.forEach(el => {
        el.parentElement.style.background = '#c6f6d5';
        setTimeout(() => {
          el.parentElement.style.background = '';
        }, 2000);
      });
      
      console.log(`Selected option: ${matchedOption.label} (${matchedOption.value})`);
    } else {
      console.warn('No matching option found for response:', finalResponse);
    }
  } else {
    // Regular field (text, textarea, etc.)
    field.element.value = finalResponse;
    field.element.dispatchEvent(new Event('input', { bubbles: true }));
    field.element.dispatchEvent(new Event('change', { bubbles: true }));
    field.element.dispatchEvent(new Event('blur', { bubbles: true }));
    
    // Visual feedback
    field.element.style.background = '#c6f6d5';
    setTimeout(() => {
      field.element.style.background = '';
    }, 2000);
  }
  
  // Update preview
  const previewDiv = document.getElementById(`preview_${field.id}`);
  if (previewDiv) {
    previewDiv.innerHTML = `
      <div style="color: #22543d; font-size: 12px; padding: 8px; background: #c6f6d5; border-radius: 4px;">
        Applied to form.
      </div>
    `;
  }
  
  updateStatus('Response applied to form!');
  
  // Log the ML data
  logMLData(field, finalResponse);
}

// Generate AI response for a field
function generateAIResponse(field) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({
      action: 'generateResponse',
      field: {
        id: field.id,
        label: field.label,
        type: field.type,
        placeholder: field.placeholder,
        maxLength: field.maxLength,
        isGroup: field.isGroup || false,
        options: field.options || [],
        fieldset: field.fieldset
      }
    }, (response) => {
      if (response && response.response) {
        resolve(response.response);
      } else {
        resolve(null);
      }
    });
  });
}

// Log ML data for learning
function logMLData(field, finalResponse) {
  fetch(`${API_URL}/api/ml/log`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      field_type: field.type,
      field_label: field.label,
      generated_response: finalResponse,
      user_response: finalResponse,  // Same for now, can track edits later
      confidence: 0.8
    })
  }).catch(err => console.error('Failed to log ML data:', err));
}

// Save application to tracker
function saveApplication() {
  const fields = window.applyEaseFields || [];
  const data = {};
  
  fields.forEach(field => {
    data[field.label || field.name] = field.element.value;
  });
  
  chrome.runtime.sendMessage({
    action: 'saveApplication',
    application: {
      company_name: document.title.split(' | ')[0] || 'Unknown Company',
      position: extractPosition(),
      job_url: window.location.href,
      submission_data: data,
      status: 'submitted'
    }
  }, (response) => {
    if (response && response.success) {
      updateStatus('Application saved to tracker!');
    } else {
      updateStatus('Failed to save application');
    }
  });
}

// Extract position title from page
function extractPosition() {
  const h1 = document.querySelector('h1');
  if (h1) return h1.innerText.trim();
  
  const title = document.title;
  const patterns = [/apply.+?for\s+(.+?)\s+at/i, /(.+?)\s+-\s+apply/i, /apply.+?:\s+(.+)/i];
  
  for (const pattern of patterns) {
    const match = title.match(pattern);
    if (match) return match[1].trim();
  }
  
  return 'Unknown Position';
}

// Send chat message
function sendChatMessage() {
  const input = document.getElementById('applyease-chat-input');
  const message = input.value.trim();
  
  if (!message) return;
  
  // Add user message to chat
  addChatMessage(message, 'user');
  input.value = '';
  
  // Send to AI
  chrome.runtime.sendMessage({
    action: 'chatMessage',
    message: message
  }, (response) => {
    if (response && response.response) {
      addChatMessage(response.response, 'assistant');
    }
  });
}

// Add message to chat
function addChatMessage(message, role) {
  const container = document.getElementById('applyease-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `applyease-message ${role}`;
  messageDiv.innerText = message;
  container.appendChild(messageDiv);
  container.scrollTop = container.scrollHeight;
}

// Update status message
function updateStatus(message) {
  const status = document.getElementById('applyease-status');
  if (status) {
    status.innerText = message;
  }
}

// Monitor form submission to auto-save application
function monitorFormSubmission() {
  console.log('ApplyEase: Monitoring form submissions...');
  
  // Find all forms on the page
  const forms = document.querySelectorAll('form');
  
  forms.forEach(form => {
    // Add submit event listener
    form.addEventListener('submit', handleFormSubmit, true);
    
    // Also watch for button clicks (some forms use AJAX)
    const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
    submitButtons.forEach(button => {
      button.addEventListener('click', () => {
        // Delay to let form populate
        setTimeout(() => {
          captureAndSaveApplication();
        }, 500);
      });
    });
  });
  
  // Also monitor for dynamic forms
  const observer = new MutationObserver((mutations) => {
    mutations.forEach(mutation => {
      mutation.addedNodes.forEach(node => {
        if (node.tagName === 'FORM') {
          node.addEventListener('submit', handleFormSubmit, true);
        }
      });
    });
  });
  
  observer.observe(document.body, { childList: true, subtree: true });
}

// Handle form submission
function handleFormSubmit(event) {
  console.log('ApplyEase: Form submitted!');
  
  // Don't prevent default submission
  // Just capture data and save in background
  setTimeout(() => {
    captureAndSaveApplication();
  }, 100);
}

// Capture and save application data
function captureAndSaveApplication() {
  console.log('ApplyEase: Capturing application data...');
  
  const fields = window.applyEaseFields || [];
  const data = {};
  
  // Collect all field values
  fields.forEach(field => {
    try {
      if (field.element && document.body.contains(field.element)) {
        if (field.isGroup) {
          // For radio/checkbox groups, find selected option
          const selected = field.elements?.find(el => el.checked);
          if (selected) {
            data[field.label || field.name] = selected.value || selected.parentElement?.textContent?.trim();
          }
        } else {
          data[field.label || field.name] = field.element.value;
        }
      }
    } catch (e) {
      console.warn('Error capturing field:', field.label, e);
    }
  });
  
  // Extract company and position info
  const companyName = extractCompanyFromPage();
  const position = extractPosition();
  
  const applicationData = {
    company_name: companyName,
    position: position,
    job_url: window.location.href,
    application_url: window.location.href,
    submission_data: data,
    status: 'submitted',
    notes: `Auto-saved from ApplyEase extension on ${new Date().toLocaleDateString()}`
  };
  
  console.log('Saving application:', applicationData);
  
  // Save to backend (which will sync to Google Sheets)
  console.log('Sending application data to backend...');
  
  chrome.runtime.sendMessage({
    action: 'saveApplication',
    application: applicationData
  }, (response) => {
    if (response && response.success) {
      console.log('Application saved successfully.');
      console.log('  Application ID:', response.data?.application_id);
      console.log('  Synced to Google Sheets:', response.data?.synced_to_sheets);
      
      showSuccessNotification(
        `${companyName} - ${position}`,
        'Application saved.'
      );
    } else {
      console.error('Failed to save application:', response?.error);
      showErrorNotification(
        'Application not saved',
        response?.error || 'Unknown error occurred'
      );
    }
  });
}

// Extract company name from page
function extractCompanyFromPage() {
  // Try various selectors commonly used for company names
  const selectors = [
    '[data-company]',
    '.company-name',
    '.employer-name',
    'h1.company',
    '.job-company',
    '[class*="company"]'
  ];
  
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element.textContent.trim();
    }
  }
  
  // Try to extract from page title
  const title = document.title;
  const patterns = [
    /(.+?)\s*[\|\-–]/,
    /at\s+(.+?)$/i,
    /^(.+?)\s+careers/i
  ];
  
  for (const pattern of patterns) {
    const match = title.match(pattern);
    if (match) {
      return match[1].trim();
    }
  }
  
  // Fallback to domain name
  try {
    const domain = new URL(window.location.href).hostname;
    const parts = domain.split('.');
    const mainPart = parts.length > 1 ? parts[parts.length - 2] : parts[0];
    return mainPart.charAt(0).toUpperCase() + mainPart.slice(1);
  } catch (e) {
    return 'Unknown Company';
  }
}

// Show success notification
function showSuccessNotification(title, message) {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 10001;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    font-weight: 500;
    animation: slideIn 0.3s ease-out;
    max-width: 350px;
  `;
  
  notification.innerHTML = `
    <div style="display: flex; align-items: start; gap: 12px;">
      <div style="font-size: 24px;">📊</div>
      <div>
        <div style="font-weight: 600; margin-bottom: 4px;">${title}</div>
        <div style="font-size: 12px; opacity: 0.9;">${message}</div>
      </div>
    </div>
  `;
  
  // Add animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
  `;
  document.head.appendChild(style);
  
  document.body.appendChild(notification);
  
  // Remove after 5 seconds
  setTimeout(() => {
    notification.style.animation = 'slideIn 0.3s ease-out reverse';
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
      if (document.head.contains(style)) {
        document.head.removeChild(style);
      }
    }, 300);
  }, 5000);
}

// Show error notification
function showErrorNotification(title, message) {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 10001;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    font-weight: 500;
    animation: slideIn 0.3s ease-out;
    max-width: 350px;
  `;
  
  notification.innerHTML = `
    <div style="display: flex; align-items: start; gap: 12px;">
      <div style="font-size: 24px;">⚠️</div>
      <div>
        <div style="font-weight: 600; margin-bottom: 4px;">${title}</div>
        <div style="font-size: 12px; opacity: 0.9;">${message}</div>
      </div>
    </div>
  `;
  
  document.body.appendChild(notification);
  
  // Remove after 6 seconds (errors need more time to read)
  setTimeout(() => {
    notification.style.animation = 'slideIn 0.3s ease-out reverse';
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 300);
  }, 6000);
}

// Handle messages from popup/background
function handleMessage(request, sender, sendResponse) {
  switch (request.action) {
    case 'togglePanel':
      togglePanel();
      break;
    case 'detectFields':
      detectFormFields();
      break;
    case 'autoFill':
      autoFillForm();
      break;
    default:
      break;
  }
  
  sendResponse({ success: true });
  return true;
}
