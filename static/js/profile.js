/**
 * Profile Management JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize tabs
  initializeTabs();
  
  // Initialize form submissions
  initializeProfileForms();
});

/**
 * Initialize tab functionality
 */
function initializeTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');
  
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      // Remove active class from all buttons and panes
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabPanes.forEach(pane => pane.classList.remove('active'));
      
      // Add active class to clicked button
      button.classList.add('active');
      
      // Show corresponding tab pane
      const tabId = button.getAttribute('data-tab');
      const tabPane = document.getElementById(tabId);
      if (tabPane) {
        tabPane.classList.add('active');
      }
    });
  });
}

/**
 * Initialize form submissions
 */
function initializeProfileForms() {
  // Personal Information Form
  const personalInfoForm = document.getElementById('personal-info-form');
  if (personalInfoForm) {
    personalInfoForm.addEventListener('submit', handlePersonalInfoSubmit);
  }
  
  // Resume Form
  const resumeForm = document.getElementById('resume-form');
  if (resumeForm) {
    resumeForm.addEventListener('submit', handleResumeSubmit);
  }
  
  // Cover Letter Form
  const coverLetterForm = document.getElementById('cover-letter-form');
  if (coverLetterForm) {
    coverLetterForm.addEventListener('submit', handleCoverLetterSubmit);
  }
  
  // Preferences Form
  const preferencesForm = document.getElementById('preferences-form');
  if (preferencesForm) {
    preferencesForm.addEventListener('submit', handlePreferencesSubmit);
  }
  
  // Resume and Cover Letter Actions
  initializeItemActions();
}

/**
 * Handle personal information form submission
 * @param {Event} event - Form submit event
 */
async function handlePersonalInfoSubmit(event) {
  event.preventDefault();
  
  try {
    const formData = new FormData(event.target);
    const personalInfo = {
      full_name: formData.get('full_name'),
      email: formData.get('email'),
      phone: formData.get('phone'),
      address: formData.get('address'),
      city: formData.get('city'),
      state: formData.get('state'),
      zip: formData.get('zip'),
      linkedin: formData.get('linkedin'),
      portfolio: formData.get('portfolio')
    };
    
    // Send data to API
    const response = await apiRequest('/api/profile/personal-info', 'PUT', personalInfo);
    
    // Show success message
    showNotification('Personal information updated successfully', 'success');
  } catch (error) {
    showNotification(error.message || 'Failed to update personal information', 'error');
  }
}

/**
 * Handle resume form submission
 * @param {Event} event - Form submit event
 */
async function handleResumeSubmit(event) {
  event.preventDefault();
  
  try {
    const formData = new FormData(event.target);
    
    // For file uploads, we need to use FormData directly
    const resumeData = new FormData();
    resumeData.append('name', formData.get('resume_name'));
    resumeData.append('description', formData.get('resume_description'));
    resumeData.append('is_default', formData.get('resume_default') ? 'true' : 'false');
    
    const resumeFile = formData.get('resume_file');
    if (resumeFile && resumeFile.size > 0) {
      resumeData.append('file', resumeFile);
    }
    
    // Send data to API using fetch directly (not apiRequest helper)
    const response = await fetch('/api/profile/resumes', {
      method: 'POST',
      body: resumeData,
      credentials: 'same-origin'
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to upload resume');
    }
    
    // Reset form
    event.target.reset();
    
    // Refresh resume list
    await refreshResumeList();
    
    // Show success message
    showNotification('Resume uploaded successfully', 'success');
  } catch (error) {
    showNotification(error.message || 'Failed to upload resume', 'error');
  }
}

/**
 * Handle cover letter form submission
 * @param {Event} event - Form submit event
 */
async function handleCoverLetterSubmit(event) {
  event.preventDefault();
  
  try {
    const formData = new FormData(event.target);
    
    // For file uploads, we need to use FormData directly
    const letterData = new FormData();
    letterData.append('name', formData.get('letter_name'));
    letterData.append('template', formData.get('letter_template'));
    letterData.append('is_default', formData.get('letter_default') ? 'true' : 'false');
    
    const letterFile = formData.get('letter_file');
    if (letterFile && letterFile.size > 0) {
      letterData.append('file', letterFile);
    }
    
    // Send data to API using fetch directly
    const response = await fetch('/api/profile/cover-letters', {
      method: 'POST',
      body: letterData,
      credentials: 'same-origin'
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to save cover letter');
    }
    
    // Reset form
    event.target.reset();
    
    // Refresh cover letter list
    await refreshCoverLetterList();
    
    // Show success message
    showNotification('Cover letter saved successfully', 'success');
  } catch (error) {
    showNotification(error.message || 'Failed to save cover letter', 'error');
  }
}

/**
 * Handle preferences form submission
 * @param {Event} event - Form submit event
 */
async function handlePreferencesSubmit(event) {
  event.preventDefault();
  
  try {
    const formData = new FormData(event.target);
    
    // Get all selected job types
    const jobTypeCheckboxes = document.querySelectorAll('input[name="job_types"]:checked');
    const jobTypes = Array.from(jobTypeCheckboxes).map(cb => cb.value);
    
    // Build preferences object
    const preferences = {
      job_title: formData.get('job_title'),
      min_salary: formData.get('min_salary') ? parseInt(formData.get('min_salary')) : null,
      max_salary: formData.get('max_salary') ? parseInt(formData.get('max_salary')) : null,
      locations: formData.get('locations').split(',').map(loc => loc.trim()).filter(loc => loc),
      job_types: jobTypes,
      experience_level: formData.get('experience_level'),
      skills: formData.get('skills').split(',').map(skill => skill.trim()).filter(skill => skill),
      keywords: formData.get('keywords').split(',').map(keyword => keyword.trim()).filter(keyword => keyword)
    };
    
    // Send data to API
    const response = await apiRequest('/api/profile/preferences', 'PUT', preferences);
    
    // Show success message
    showNotification('Job preferences updated successfully', 'success');
  } catch (error) {
    showNotification(error.message || 'Failed to update job preferences', 'error');
  }
}

/**
 * Initialize actions for resume and cover letter items
 */
function initializeItemActions() {
  // Resume actions
  document.addEventListener('click', async function(event) {
    // Edit resume
    if (event.target.matches('[data-action="edit-resume"]')) {
      const resumeId = event.target.getAttribute('data-id');
      await editResume(resumeId);
    }
    
    // Delete resume
    if (event.target.matches('[data-action="delete-resume"]')) {
      const resumeId = event.target.getAttribute('data-id');
      if (confirm('Are you sure you want to delete this resume?')) {
        await deleteResume(resumeId);
      }
    }
    
    // Edit cover letter
    if (event.target.matches('[data-action="edit-letter"]')) {
      const letterId = event.target.getAttribute('data-id');
      await editCoverLetter(letterId);
    }
    
    // Delete cover letter
    if (event.target.matches('[data-action="delete-letter"]')) {
      const letterId = event.target.getAttribute('data-id');
      if (confirm('Are you sure you want to delete this cover letter?')) {
        await deleteCoverLetter(letterId);
      }
    }
  });
}

/**
 * Edit a resume
 * @param {string} resumeId - Resume ID
 */
async function editResume(resumeId) {
  try {
    // Fetch resume details
    const resume = await apiRequest(`/api/profile/resumes/${resumeId}`, 'GET');
    
    // Populate form
    const form = document.getElementById('resume-form');
    form.querySelector('#resume-name').value = resume.name;
    form.querySelector('#resume-description').value = resume.description || '';
    form.querySelector('#resume-default').checked = resume.is_default;
    
    // Add hidden field for resume ID
    let idField = form.querySelector('#resume-id');
    if (!idField) {
      idField = document.createElement('input');
      idField.type = 'hidden';
      idField.id = 'resume-id';
      idField.name = 'resume_id';
      form.appendChild(idField);
    }
    idField.value = resumeId;
    
    // Change form submit button text
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.textContent = 'Update Resume';
    
    // Scroll to form
    form.scrollIntoView({ behavior: 'smooth' });
  } catch (error) {
    showNotification('Failed to load resume details', 'error');
  }
}

/**
 * Delete a resume
 * @param {string} resumeId - Resume ID
 */
async function deleteResume(resumeId) {
  try {
    await apiRequest(`/api/profile/resumes/${resumeId}`, 'DELETE');
    
    // Remove from UI
    const resumeItem = document.querySelector(`.resume-item[data-id="${resumeId}"]`);
    if (resumeItem) {
      resumeItem.remove();
    }
    
    showNotification('Resume deleted successfully', 'success');
    
    // Check if no resumes left
    const resumeList = document.querySelector('.resume-list');
    if (resumeList && resumeList.children.length === 0) {
      resumeList.innerHTML = '<p class="no-items">No resumes uploaded yet.</p>';
    }
  } catch (error) {
    showNotification('Failed to delete resume', 'error');
  }
}

/**
 * Edit a cover letter
 * @param {string} letterId - Cover letter ID
 */
async function editCoverLetter(letterId) {
  try {
    // Fetch cover letter details
    const letter = await apiRequest(`/api/profile/cover-letters/${letterId}`, 'GET');
    
    // Populate form
    const form = document.getElementById('cover-letter-form');
    form.querySelector('#letter-name').value = letter.name;
    form.querySelector('#letter-template').value = letter.template || '';
    form.querySelector('#letter-default').checked = letter.is_default;
    
    // Add hidden field for letter ID
    let idField = form.querySelector('#letter-id');
    if (!idField) {
      idField = document.createElement('input');
      idField.type = 'hidden';
      idField.id = 'letter-id';
      idField.name = 'letter_id';
      form.appendChild(idField);
    }
    idField.value = letterId;
    
    // Change form submit button text
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.textContent = 'Update Cover Letter';
    
    // Scroll to form
    form.scrollIntoView({ behavior: 'smooth' });
  } catch (error) {
    showNotification('Failed to load cover letter details', 'error');
  }
}

/**
 * Delete a cover letter
 * @param {string} letterId - Cover letter ID
 */
async function deleteCoverLetter(letterId) {
  try {
    await apiRequest(`/api/profile/cover-letters/${letterId}`, 'DELETE');
    
    // Remove from UI
    const letterItem = document.querySelector(`.cover-letter-item[data-id="${letterId}"]`);
    if (letterItem) {
      letterItem.remove();
    }
    
    showNotification('Cover letter deleted successfully', 'success');
    
    // Check if no cover letters left
    const letterList = document.querySelector('.cover-letter-list');
    if (letterList && letterList.children.length === 0) {
      letterList.innerHTML = '<p class="no-items">No cover letters created yet.</p>';
    }
  } catch (error) {
    showNotification('Failed to delete cover letter', 'error');
  }
}

/**
 * Refresh the resume list
 */
async function refreshResumeList() {
  try {
    const resumes = await apiRequest('/api/profile/resumes', 'GET');
    const resumeList = document.querySelector('.resume-list');
    
    if (!resumeList) return;
    
    if (resumes.length === 0) {
      resumeList.innerHTML = '<p class="no-items">No resumes uploaded yet.</p>';
      return;
    }
    
    let html = '';
    resumes.forEach(resume => {
      html += `
        <div class="resume-item" data-id="${resume.id}">
          <div class="resume-header">
            <h4>${resume.name}</h4>
            <div class="resume-actions">
              <button class="btn btn-sm btn-edit" data-action="edit-resume" data-id="${resume.id}">Edit</button>
              <button class="btn btn-sm btn-delete" data-action="delete-resume" data-id="${resume.id}">Delete</button>
            </div>
          </div>
          <div class="resume-meta">
            <span>Last Updated: ${new Date(resume.updated_at).toLocaleDateString()}</span>
            <span>${resume.is_default ? 'Default' : ''}</span>
          </div>
        </div>
      `;
    });
    
    resumeList.innerHTML = html;
  } catch (error) {
    console.error('Failed to refresh resume list:', error);
  }
}

/**
 * Refresh the cover letter list
 */
async function refreshCoverLetterList() {
  try {
    const letters = await apiRequest('/api/profile/cover-letters', 'GET');
    const letterList = document.querySelector('.cover-letter-list');
    
    if (!letterList) return;
    
    if (letters.length === 0) {
      letterList.innerHTML = '<p class="no-items">No cover letters created yet.</p>';
      return;
    }
    
    let html = '';
    letters.forEach(letter => {
      html += `
        <div class="cover-letter-item" data-id="${letter.id}">
          <div class="cover-letter-header">
            <h4>${letter.name}</h4>
            <div class="cover-letter-actions">
              <button class="btn btn-sm btn-edit" data-action="edit-letter" data-id="${letter.id}">Edit</button>
              <button class="btn btn-sm btn-delete" data-action="delete-letter" data-id="${letter.id}">Delete</button>
            </div>
          </div>
          <div class="cover-letter-meta">
            <span>Last Updated: ${new Date(letter.updated_at).toLocaleDateString()}</span>
            <span>${letter.is_default ? 'Default' : ''}</span>
          </div>
        </div>
      `;
    });
    
    letterList.innerHTML = html;
  } catch (error) {
    console.error('Failed to refresh cover letter list:', error);
  }
}