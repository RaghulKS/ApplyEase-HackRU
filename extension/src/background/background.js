const API_URL = 'http://localhost:8001';
let userProfile = null;

chrome.runtime.onInstalled.addListener(() => {
  console.log('ApplyEase Extension installed - No Auth Version');
  
  chrome.storage.local.set({
    apiUrl: API_URL,
    autoDetect: true,
    autoFill: false
  });
  
  loadUserProfile();
  
  chrome.contextMenus.create({
    id: 'applyease-autofill',
    title: 'Auto-fill with ApplyEase',
    contexts: ['page', 'frame']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'applyease-autofill') {
    chrome.tabs.sendMessage(tab.id, { action: 'autoFill' });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request.action);
  
  switch (request.action) {
    case 'getProfile':
      getProfile(sendResponse);
      return true;
      
    case 'classifyFields':
      classifyFields(request.fields, request.url, sendResponse);
      return true;
      
    case 'generateResponse':
      generateResponse(request.field, sendResponse);
      return true;
      
    case 'saveApplication':
      saveApplication(request.application, sendResponse);
      return true;
      
    case 'chatMessage':
      handleChatMessage(request.message, sendResponse);
      return true;
      
    default:
      sendResponse({ error: 'Unknown action' });
      return false;
  }
});

// Load user profile
async function loadUserProfile() {
  try {
    const response = await fetch(`${API_URL}/api/profile`);
    
    if (response.ok) {
      const data = await response.json();
      if (data.exists && data.profile) {
        userProfile = data.profile;
        chrome.storage.local.set({ userProfile });
      }
    }
  } catch (error) {
    console.error('Error loading profile:', error);
  }
}

// Get profile
function getProfile(sendResponse) {
  if (userProfile) {
    sendResponse({ success: true, profile: userProfile });
  } else {
    loadUserProfile().then(() => {
      sendResponse({ success: true, profile: userProfile });
    });
    return true;
  }
}

// Classify form fields using ML model
async function classifyFields(fields, url, sendResponse) {
  try {
    const response = await fetch(`${API_URL}/api/fields/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ fields, url })
    });
    
    const data = await response.json();
    sendResponse(data);
  } catch (error) {
    console.error('Field classification error:', error);
    sendResponse({ error: error.message });
  }
}

// Generate AI response for a field
async function generateResponse(field, sendResponse) {
  try {
    // Get current tab URL for context
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = tab ? tab.url : '';
    
    // Extract company name from URL or title
    const companyName = extractCompanyName(url, tab ? tab.title : '');
    
    const response = await fetch(`${API_URL}/api/chatbot/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        field_info: field,
        company_info: { name: companyName },
        messages: [],
        resume_context: userProfile
      })
    });
    
    const data = await response.json();
    sendResponse(data);
  } catch (error) {
    console.error('Generate response error:', error);
    sendResponse({ error: error.message });
  }
}

// Save application to tracker
async function saveApplication(application, sendResponse) {
  try {
    console.log('Saving application to backend:', application);
    console.log('  Company:', application.company_name);
    console.log('  Position:', application.position);
    console.log('  Fields captured:', Object.keys(application.submission_data || {}).length);
    
    // Use extension-specific endpoint (no auth required)
    const response = await fetch(`${API_URL}/api/extension/track-application`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'applyease-extension-dev-key' // Simple API key for extension
      },
      body: JSON.stringify(application)
    });
    
    console.log('Backend response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('Application saved successfully:', data);
      console.log('  Application ID:', data.application_id);
      console.log('  Synced to Google Sheets:', data.synced_to_sheets);
      
      // Show success notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/icon128.png',
        title: 'Application Saved',
        message: `${application.company_name} - ${application.position}`,
        priority: 2
      });
      
      sendResponse({ success: true, data });
    } else {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      console.error('Failed to save application:', response.status, errorData);
      
      // Show error notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/icon128.png',
        title: 'Application Save Failed',
        message: `Could not save ${application.company_name} application. Error: ${errorData.detail}`,
        priority: 2
      });
      
      sendResponse({ success: false, error: errorData.detail || 'Failed to save application' });
    }
  } catch (error) {
    console.error('Save application error:', error);
    
    // Show error notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: '/icon128.png',
      title: 'Application Save Error',
      message: `Network error: ${error.message}. Application not saved.`,
      priority: 2
    });
    
    sendResponse({ success: false, error: error.message });
  }
}

// Handle chat messages
async function handleChatMessage(message, sendResponse) {
  try {
    const response = await fetch(`${API_URL}/api/chatbot/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: [
          { role: 'user', content: message }
        ],
        field_info: {},
        resume_context: userProfile
      })
    });
    
    const data = await response.json();
    sendResponse(data);
  } catch (error) {
    console.error('Chat message error:', error);
    sendResponse({ error: error.message });
  }
}

// Extract company name from URL and title
function extractCompanyName(url, title) {
  // Try to extract from domain
  try {
    const domain = new URL(url).hostname;
    const parts = domain.split('.');
    if (parts.length > 1) {
      // Remove common TLDs and subdomains
      const name = parts.find(p => 
        p !== 'www' && p !== 'jobs' && p !== 'careers' && 
        p !== 'com' && p !== 'org' && p !== 'net' && p !== 'io'
      );
      if (name) {
        return name.charAt(0).toUpperCase() + name.slice(1);
      }
    }
  } catch (e) {
    // Invalid URL
  }
  
  // Try to extract from title
  if (title) {
    const patterns = [
      /(.+?)\s*[\|\-–]/, // Company name before separator
      /at\s+(.+?)$/i,      // "at Company"
      /^(.+?)\s+careers/i  // "Company Careers"
    ];
    
    for (const pattern of patterns) {
      const match = title.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }
  }
  
  return 'Unknown Company';
}

// Load user profile on startup
chrome.storage.local.get(['userProfile'], (data) => {
  if (data.userProfile) {
    userProfile = data.userProfile;
    console.log('ApplyEase: Loaded user profile');
  } else {
    // Try to load from backend
    loadUserProfile();
  }
});
