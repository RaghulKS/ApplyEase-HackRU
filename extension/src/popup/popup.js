// Popup script for ApplyEase - Resume Upload First Version

const API_URL = 'http://localhost:8001';
let parsedResumeData = null;

// DOM Elements
const elements = {
  loading: document.getElementById('loading'),
  uploadSection: document.getElementById('uploadSection'),
  formSection: document.getElementById('formSection'),
  dashboardSection: document.getElementById('dashboardSection'),
  
  uploadZone: document.getElementById('uploadZone'),
  resumeFile: document.getElementById('resumeFile'),
  skipUpload: document.getElementById('skipUpload'),
  uploadError: document.getElementById('uploadError'),
  uploadSuccess: document.getElementById('uploadSuccess'),
  
  profileForm: document.getElementById('profileForm'),
  formError: document.getElementById('formError'),
  formSuccess: document.getElementById('formSuccess'),
  parsedInfo: document.getElementById('parsedInfo'),
  uploadAnotherResume: document.getElementById('uploadAnotherResume'),
  
  userName: document.getElementById('userName'),
  userEmail: document.getElementById('userEmail'),
  totalApplications: document.getElementById('totalApplications'),
  savedResponses: document.getElementById('savedResponses')
};

// Initialize popup
document.addEventListener('DOMContentLoaded', () => {
  checkProfileStatus();
  setupEventListeners();
});

// Check if profile exists
async function checkProfileStatus() {
  showLoading(true);
  
  try {
    const response = await fetch(`${API_URL}/api/profile`);
    const data = await response.json();
    
    showLoading(false);
    
    if (data.exists && data.profile) {
      // Profile exists, show dashboard
      chrome.storage.local.set({ userProfile: data.profile });
      showDashboard(data.profile);
    } else {
      // No profile, show resume upload
      showUpload();
    }
  } catch (error) {
    showLoading(false);
    console.error('Error checking profile:', error);
    showUploadError('Cannot connect to backend. Make sure the server is running on http://localhost:8001');
    showUpload();
  }
}

// Setup event listeners
function setupEventListeners() {
  // Upload zone
  elements.uploadZone.addEventListener('click', () => elements.resumeFile.click());
  elements.resumeFile.addEventListener('change', handleFileSelect);
  elements.skipUpload.addEventListener('click', () => showForm(null));
  elements.uploadAnotherResume.addEventListener('click', showUpload);
  
  // Edit buttons
  document.getElementById('addEducation')?.addEventListener('click', () => addEducation());
  document.getElementById('addExperience')?.addEventListener('click', () => addExperience());
  document.getElementById('editSkills')?.addEventListener('click', toggleSkillsEdit);
  
  // Drag and drop
  elements.uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.uploadZone.classList.add('dragover');
  });
  
  elements.uploadZone.addEventListener('dragleave', () => {
    elements.uploadZone.classList.remove('dragover');
  });
  
  elements.uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      uploadResume(file);
    }
  });
  
  // Form
  elements.profileForm.addEventListener('submit', handleProfileSubmit);
  
  // Dashboard
  document.getElementById('detectFieldsBtn')?.addEventListener('click', detectFields);
  document.getElementById('autoFillBtn')?.addEventListener('click', autoFillForm);
  document.getElementById('openPanelBtn')?.addEventListener('click', openPanel);
  document.getElementById('viewApplicationsBtn')?.addEventListener('click', viewApplications);
  document.getElementById('editProfileBtn')?.addEventListener('click', editProfile);
}

// Handle file selection
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) {
    uploadResume(file);
  }
}

// Upload and parse resume
async function uploadResume(file) {
  console.log('Uploading resume:', file.name, 'Type:', file.type, 'Size:', file.size);
  
  hideUploadError();
  showLoading(true);
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch(`${API_URL}/api/profile/resume`, {
      method: 'POST',
      body: formData
    });
    
    showLoading(false);
    
    console.log('Upload response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('Resume parsed successfully:', data);
      
      parsedResumeData = data.parsed_data;
      showUploadSuccess(`Resume "${data.filename}" uploaded and parsed successfully!`);
      
      setTimeout(() => {
        showForm(parsedResumeData);
      }, 1500);
    } else {
      const errorData = await response.json();
      console.error('Upload error:', errorData);
      
      let errorMessage = 'Failed to upload resume';
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map(e => e.msg || e).join(', ');
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }
      
      showUploadError(errorMessage);
    }
  } catch (error) {
    showLoading(false);
    console.error('Error uploading resume:', error);
    showUploadError(`Connection error: ${error.message}. Make sure backend is running on http://localhost:8001`);
  }
}

// Show form with parsed data
function showForm(parsedData) {
  hideAllSections();
  elements.formSection.classList.add('active');
  
  if (parsedData) {
    elements.parsedInfo.style.display = 'block';
    populateForm(parsedData);
  }
}

// Populate form with parsed resume data
function populateForm(data) {
  document.getElementById('firstName').value = data.first_name || '';
  document.getElementById('middleName').value = data.middle_name || '';
  document.getElementById('lastName').value = data.last_name || '';
  document.getElementById('email').value = data.email || '';
  document.getElementById('phone').value = data.phone || '';
  document.getElementById('location').value = data.location || '';
  document.getElementById('linkedinUrl').value = data.linkedin_url || '';
  document.getElementById('githubUrl').value = data.github_url || '';
  
  // Display education (inline editable)
  const educationContainer = document.getElementById('educationEntries');
  if (data.education && data.education.length > 0) {
    educationContainer.innerHTML = data.education.map((edu, idx) => `
      <div class="edu-card" data-index="${idx}" style="background: #f7fafc; padding: 10px; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #667eea; position: relative;">
        <button class="delete-btn" data-type="education" data-index="${idx}" style="position: absolute; top: 8px; right: 8px; background: #fc8181; color: white; border: none; border-radius: 4px; padding: 2px 8px; font-size: 10px; cursor: pointer; z-index: 10;">✕</button>
        
        <div class="edu-display-${idx}" style="cursor: pointer;">
          <strong>${edu.institution || 'Institution'}</strong><br>
          <small>${edu.degree || ''} ${edu.field ? 'in ' + edu.field : ''}</small><br>
          <small style="color: #718096;">${edu.dates || ''} ${edu.gpa ? '• GPA: ' + edu.gpa : ''}</small>
          <div style="font-size: 10px; color: #a0aec0; margin-top: 4px;">Click to edit</div>
        </div>
        
        <div class="edu-edit-${idx}" style="display: none;">
          <input type="text" class="edu-institution" value="${edu.institution || ''}" placeholder="Institution" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <input type="text" class="edu-degree" value="${edu.degree || ''}" placeholder="Degree" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <input type="text" class="edu-field" value="${edu.field || ''}" placeholder="Field of Study" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <input type="text" class="edu-dates" value="${edu.dates || ''}" placeholder="Dates (e.g. 2020-2024)" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <input type="text" class="edu-gpa" value="${edu.gpa || ''}" placeholder="GPA (optional)" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <button class="save-edu-btn" data-index="${idx}" style="width: 100%; padding: 6px; background: #48bb78; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: 600; cursor: pointer;">Save</button>
        </div>
      </div>
    `).join('');
    
    // Add click handlers
    setTimeout(() => {
      data.education.forEach((edu, idx) => {
        // Toggle edit mode
        document.querySelector(`.edu-display-${idx}`)?.addEventListener('click', () => {
          document.querySelector(`.edu-display-${idx}`).style.display = 'none';
          document.querySelector(`.edu-edit-${idx}`).style.display = 'block';
        });
        
        // Save button
        document.querySelector(`.save-edu-btn[data-index="${idx}"]`)?.addEventListener('click', () => {
          saveEducation(idx);
        });
      });
      
      // Delete buttons
      document.querySelectorAll('.delete-btn[data-type="education"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          deleteEducation(parseInt(btn.dataset.index));
        });
      });
    }, 0);
  } else {
    educationContainer.innerHTML = '<p class="small-text" style="color: #a0aec0;">No education entries found in resume</p>';
  }
  
  // Display experience (inline editable)
  const experienceContainer = document.getElementById('experienceEntries');
  if (data.experience && data.experience.length > 0) {
    experienceContainer.innerHTML = data.experience.map((exp, idx) => `
      <div class="exp-card" data-index="${idx}" style="background: #f7fafc; padding: 10px; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #764ba2; position: relative;">
        <button class="delete-btn" data-type="experience" data-index="${idx}" style="position: absolute; top: 8px; right: 8px; background: #fc8181; color: white; border: none; border-radius: 4px; padding: 2px 8px; font-size: 10px; cursor: pointer; z-index: 10;">✕</button>
        
        <div class="exp-display-${idx}" style="cursor: pointer;">
          <strong>${exp.company || 'Company'}</strong><br>
          <small>${exp.title || 'Position'}</small><br>
          <small style="color: #718096;">${exp.dates || ''}</small>
          ${exp.description ? `<p style="font-size: 11px; margin: 4px 0 0 0; color: #4a5568;">${exp.description.substring(0, 100)}${exp.description.length > 100 ? '...' : ''}</p>` : ''}
          <div style="font-size: 10px; color: #a0aec0; margin-top: 4px;">Click to edit</div>
        </div>
        
        <div class="exp-edit-${idx}" style="display: none;">
          <input type="text" class="exp-company" value="${exp.company || ''}" placeholder="Company" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <input type="text" class="exp-title" value="${exp.title || ''}" placeholder="Job Title" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <input type="text" class="exp-dates" value="${exp.dates || ''}" placeholder="Dates (e.g. Jan 2020 - Present)" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px;">
          <textarea class="exp-description" placeholder="Description" style="width: 100%; margin-bottom: 6px; padding: 6px; font-size: 12px; border: 1px solid #cbd5e0; border-radius: 4px; min-height: 60px; resize: vertical;">${exp.description || ''}</textarea>
          <button class="save-exp-btn" data-index="${idx}" style="width: 100%; padding: 6px; background: #48bb78; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: 600; cursor: pointer;">Save</button>
        </div>
      </div>
    `).join('');
    
    // Add click handlers
    setTimeout(() => {
      data.experience.forEach((exp, idx) => {
        // Toggle edit mode
        document.querySelector(`.exp-display-${idx}`)?.addEventListener('click', () => {
          document.querySelector(`.exp-display-${idx}`).style.display = 'none';
          document.querySelector(`.exp-edit-${idx}`).style.display = 'block';
        });
        
        // Save button
        document.querySelector(`.save-exp-btn[data-index="${idx}"]`)?.addEventListener('click', () => {
          saveExperience(idx);
        });
      });
      
      // Delete buttons
      document.querySelectorAll('.delete-btn[data-type="experience"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          deleteExperience(parseInt(btn.dataset.index));
        });
      });
    }, 0);
  } else {
    experienceContainer.innerHTML = '<p class="small-text" style="color: #a0aec0;">No work experience found in resume</p>';
  }
  
  // Display skills
  const skillsContainer = document.getElementById('skillsEntries');
  if (data.skills && data.skills.length > 0) {
    skillsContainer.innerHTML = data.skills.map(skill => `
      <span style="background: #667eea; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px;">${skill}</span>
    `).join('');
  } else {
    skillsContainer.innerHTML = '<p class="small-text" style="color: #a0aec0;">No skills found in resume</p>';
  }
  
  console.log('Form populated with:', {
    education: data.education?.length || 0,
    experience: data.experience?.length || 0,
    skills: data.skills?.length || 0
  });
}

// Handle profile form submission
async function handleProfileSubmit(e) {
  e.preventDefault();
  
  // Gather all form data
  const profile = {
    first_name: document.getElementById('firstName').value.trim(),
    middle_name: document.getElementById('middleName').value.trim() || null,
    last_name: document.getElementById('lastName').value.trim(),
    email: document.getElementById('email').value.trim(),
    phone: document.getElementById('phone').value.trim() || null,
    birthday: document.getElementById('birthday').value || null,
    location: document.getElementById('location').value.trim() || null,
    address: document.getElementById('address').value.trim() || null,
    postal_code: document.getElementById('postalCode').value.trim() || null,
    
    ethnicity: document.getElementById('ethnicity').value || null,
    gender: document.getElementById('gender').value || null,
    veteran_status: document.getElementById('veteranStatus').value || null,
    authorized_us: document.getElementById('authorizedUs').value || null,
    require_sponsorship: document.getElementById('requireSponsorship').value || null,
    has_disability: document.getElementById('hasDisability').value || null,
    lgbtq: document.getElementById('lgbtq').value || null,
    
    linkedin_url: document.getElementById('linkedinUrl').value.trim() || null,
    github_url: document.getElementById('githubUrl').value.trim() || null,
    portfolio_url: document.getElementById('portfolioUrl').value.trim() || null,
    
    skills: parsedResumeData?.skills || [],
    experience: parsedResumeData?.experience || [],
    education: parsedResumeData?.education || []
  };
  
  console.log('Submitting profile with:');
  console.log('  - Education entries:', profile.education.length);
  console.log('  - Experience entries:', profile.experience.length);
  console.log('  - Skills:', profile.skills.length);
  console.log('Full profile data:', JSON.stringify(profile, null, 2));
  
  hideFormError();
  showLoading(true);
  
  try {
    const response = await fetch(`${API_URL}/api/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(profile)
    });
    
    showLoading(false);
    
    console.log('Response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('Profile saved:', data);
      chrome.storage.local.set({ userProfile: data.profile });
      showFormSuccess('Profile saved successfully!');
      
      setTimeout(() => {
        showDashboard(data.profile);
      }, 1000);
    } else {
      const errorData = await response.json();
      console.error('Server error:', errorData);
      
      // Extract meaningful error message
      let errorMessage = 'Failed to save profile';
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }
      
      showFormError(errorMessage);
    }
  } catch (error) {
    showLoading(false);
    console.error('Error saving profile:', error);
    showFormError(`Connection error: ${error.message}`);
  }
}

// Show/hide sections
function showLoading(show) {
  elements.loading.classList.toggle('active', show);
}

function showUpload() {
  hideAllSections();
  elements.uploadSection.classList.add('active');
}

function showDashboard(profile) {
  hideAllSections();
  elements.dashboardSection.classList.add('active');
  loadDashboardData(profile);
}

function hideAllSections() {
  elements.uploadSection.classList.remove('active');
  elements.formSection.classList.remove('active');
  elements.dashboardSection.classList.remove('active');
}

// Load dashboard data
async function loadDashboardData(profile) {
  if (profile) {
    elements.userName.textContent = `Welcome, ${profile.first_name} ${profile.last_name}!`;
    elements.userEmail.textContent = profile.email;
  }
  
  // Load application stats
  try {
    const response = await fetch(`${API_URL}/api/applications/stats/summary`);
    if (response.ok) {
      const stats = await response.json();
      elements.totalApplications.textContent = stats.total || 0;
    }
  } catch (error) {
    console.error('Error loading stats:', error);
  }
  
  // Load saved responses count
  try {
    const response = await fetch(`${API_URL}/api/chatbot/unique-fields`);
    if (response.ok) {
      const data = await response.json();
      elements.savedResponses.textContent = data.fields?.length || 0;
    }
  } catch (error) {
    console.error('Error loading saved responses:', error);
  }
}

// Dashboard actions
function detectFields() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { action: 'detectFields' }, (response) => {
        if (chrome.runtime.lastError) {
          showNotification('Please reload the page and try again', 'error');
        } else if (response && response.success) {
          showNotification('Form fields detected!', 'success');
        }
      });
      window.close();
    }
  });
}

function autoFillForm() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { action: 'autoFill' }, (response) => {
        if (chrome.runtime.lastError) {
          showNotification('Please reload the page and try again', 'error');
        } else if (response && response.success) {
          showNotification('Form auto-filled!', 'success');
        }
      });
      window.close();
    }
  });
}

function openPanel() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { action: 'togglePanel' }, (response) => {
        if (!chrome.runtime.lastError) {
          window.close();
        }
      });
    }
  });
}

function viewApplications() {
  chrome.tabs.create({ url: `${API_URL}/docs` });
}

function editProfile() {
  chrome.storage.local.get(['userProfile'], (result) => {
    if (result.userProfile) {
      const p = result.userProfile;
      
      // Populate all fields
      document.getElementById('firstName').value = p.first_name || '';
      document.getElementById('middleName').value = p.middle_name || '';
      document.getElementById('lastName').value = p.last_name || '';
      document.getElementById('email').value = p.email || '';
      document.getElementById('phone').value = p.phone || '';
      document.getElementById('birthday').value = p.birthday || '';
      document.getElementById('location').value = p.location || '';
      document.getElementById('address').value = p.address || '';
      document.getElementById('postalCode').value = p.postal_code || '';
      
      document.getElementById('ethnicity').value = p.ethnicity || '';
      document.getElementById('gender').value = p.gender || '';
      document.getElementById('veteranStatus').value = p.veteran_status || '';
      document.getElementById('authorizedUs').value = p.authorized_us || '';
      document.getElementById('requireSponsorship').value = p.require_sponsorship || '';
      document.getElementById('hasDisability').value = p.has_disability || '';
      document.getElementById('lgbtq').value = p.lgbtq || '';
      
      document.getElementById('linkedinUrl').value = p.linkedin_url || '';
      document.getElementById('githubUrl').value = p.github_url || '';
      document.getElementById('portfolioUrl').value = p.portfolio_url || '';
      
      // Restore parsed resume data
      parsedResumeData = {
        skills: p.skills || [],
        experience: p.experience || [],
        education: p.education || []
      };
      
      // Show the data in the form
      populateForm(p);
    }
    showForm(null);
  });
}

// Education editing functions
function addEducation() {
  if (!parsedResumeData) parsedResumeData = {education: [], experience: [], skills: []};
  if (!parsedResumeData.education) parsedResumeData.education = [];
  
  parsedResumeData.education.push({
    institution: 'New Institution',
    degree: '',
    field: '',
    dates: '',
    gpa: ''
  });
  
  populateForm({...parsedResumeData, education: parsedResumeData.education});
  
  // Auto-open edit mode for new entry
  setTimeout(() => {
    const newIndex = parsedResumeData.education.length - 1;
    document.querySelector(`.edu-display-${newIndex}`)?.click();
  }, 100);
}

function saveEducation(index) {
  if (!parsedResumeData || !parsedResumeData.education) return;
  
  const card = document.querySelector(`.edu-card[data-index="${index}"]`);
  if (!card) return;
  
  // Read values from inline inputs
  const institution = card.querySelector('.edu-institution').value;
  const degree = card.querySelector('.edu-degree').value;
  const field = card.querySelector('.edu-field').value;
  const dates = card.querySelector('.edu-dates').value;
  const gpa = card.querySelector('.edu-gpa').value;
  
  parsedResumeData.education[index] = {
    institution: institution || '',
    degree: degree || '',
    field: field || '',
    dates: dates || '',
    gpa: gpa || ''
  };
  
  // Refresh display
  populateForm({...parsedResumeData, education: parsedResumeData.education});
}

function deleteEducation(index) {
  if (!parsedResumeData || !parsedResumeData.education) return;
  
  if (confirm('Remove this education entry?')) {
    parsedResumeData.education.splice(index, 1);
    populateForm({...parsedResumeData, education: parsedResumeData.education});
  }
}

// Experience editing functions
function addExperience() {
  if (!parsedResumeData) parsedResumeData = {education: [], experience: [], skills: []};
  if (!parsedResumeData.experience) parsedResumeData.experience = [];
  
  parsedResumeData.experience.push({
    company: 'New Company',
    title: '',
    dates: '',
    description: ''
  });
  
  populateForm({...parsedResumeData, experience: parsedResumeData.experience});
  
  // Auto-open edit mode for new entry
  setTimeout(() => {
    const newIndex = parsedResumeData.experience.length - 1;
    document.querySelector(`.exp-display-${newIndex}`)?.click();
  }, 100);
}

function saveExperience(index) {
  if (!parsedResumeData || !parsedResumeData.experience) return;
  
  const card = document.querySelector(`.exp-card[data-index="${index}"]`);
  if (!card) return;
  
  // Read values from inline inputs
  const company = card.querySelector('.exp-company').value;
  const title = card.querySelector('.exp-title').value;
  const dates = card.querySelector('.exp-dates').value;
  const description = card.querySelector('.exp-description').value;
  
  parsedResumeData.experience[index] = {
    company: company || '',
    title: title || '',
    dates: dates || '',
    description: description || ''
  };
  
  // Refresh display
  populateForm({...parsedResumeData, experience: parsedResumeData.experience});
}

function deleteExperience(index) {
  if (!parsedResumeData || !parsedResumeData.experience) return;
  
  if (confirm('Remove this experience entry?')) {
    parsedResumeData.experience.splice(index, 1);
    populateForm({...parsedResumeData, experience: parsedResumeData.experience});
  }
}

// Skills editing functions
function toggleSkillsEdit() {
  const skillsEntries = document.getElementById('skillsEntries');
  const skillsTextarea = document.getElementById('skillsTextarea');
  const editBtn = document.getElementById('editSkills');
  
  if (skillsTextarea.style.display === 'none') {
    // Show textarea for editing
    const currentSkills = parsedResumeData?.skills || [];
    skillsTextarea.value = currentSkills.join(', ');
    skillsTextarea.style.display = 'block';
    skillsEntries.style.display = 'none';
    editBtn.textContent = 'Save';
  } else {
    // Save and show tags
    const skillsText = skillsTextarea.value;
    const skills = skillsText.split(',').map(s => s.trim()).filter(s => s);
    
    if (!parsedResumeData) parsedResumeData = {education: [], experience: [], skills: []};
    parsedResumeData.skills = skills;
    
    skillsTextarea.style.display = 'none';
    skillsEntries.style.display = 'flex';
    editBtn.textContent = 'Edit';
    
    // Update display
    populateForm({...parsedResumeData});
  }
}

// Error/Success handlers
function showUploadError(message) {
  // Handle if message is an object
  const errorText = typeof message === 'string' ? message : JSON.stringify(message);
  console.error('Upload error:', message);
  elements.uploadError.textContent = errorText;
  elements.uploadError.style.display = 'block';
  elements.uploadSuccess.style.display = 'none';
}

function showUploadSuccess(message) {
  elements.uploadSuccess.textContent = message;
  elements.uploadSuccess.style.display = 'block';
  elements.uploadError.style.display = 'none';
}

function hideUploadError() {
  elements.uploadError.style.display = 'none';
  elements.uploadSuccess.style.display = 'none';
}

function showFormError(message) {
  // Handle if message is an object
  const errorText = typeof message === 'string' ? message : JSON.stringify(message);
  console.error('Form error:', message);
  elements.formError.textContent = errorText;
  elements.formError.style.display = 'block';
  elements.formSuccess.style.display = 'none';
}

function showFormSuccess(message) {
  elements.formSuccess.textContent = message;
  elements.formSuccess.style.display = 'block';
  elements.formError.style.display = 'none';
}

function hideFormError() {
  elements.formError.style.display = 'none';
  elements.formSuccess.style.display = 'none';
}

function showNotification(message, type) {
  const notification = document.createElement('div');
  notification.className = type === 'error' ? 'error' : 'success';
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 10px 15px;
    border-radius: 6px;
    z-index: 10000;
    animation: slideIn 0.3s ease;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.remove();
  }, 3000);
}