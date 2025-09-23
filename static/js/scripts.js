// Global variables
const API_BASE = '/api';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DIU Portal initialized successfully!');
    setupEventListeners();

    // Load programs if on programs page
    if (window.location.pathname === '/programs') {
        loadPrograms();
    }
});

// Setup event listeners
function setupEventListeners() {
    // Waiver form
    const waiverForm = document.getElementById('waiver-form');
    if (waiverForm) {
        waiverForm.addEventListener('submit', handleWaiverCalculation);
    }

    // Recommendation form
    const recommendationForm = document.getElementById('recommendation-form');
    if (recommendationForm) {
        recommendationForm.addEventListener('submit', handleRecommendations);
    }

    // Application form
    const applicationForm = document.getElementById('application-form');
    if (applicationForm) {
        applicationForm.addEventListener('submit', handleApplicationSubmission);
    }

    // Chat form
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', handleChatMessage);
    }

    // Search functionality
    const programSearch = document.getElementById('program-search');
    if (programSearch) {
        programSearch.addEventListener('input', handleProgramSearch);
    }

    // Filter tags
    setupFilterTags();
}

// Programs functionality
async function loadPrograms() {
    try {
        const response = await fetch(`${API_BASE}/programs`);
        if (!response.ok) {
            throw new Error('Failed to fetch programs');
        }
        const programs = await response.json();
        displayPrograms(programs);
    } catch (error) {
        console.error('Error loading programs:', error);
        displayProgramsError();
    }
}

function displayPrograms(programs) {
    const grid = document.getElementById('programs-grid');
    if (!grid) return;

    if (programs.length === 0) {
        grid.innerHTML = `
            <div class="card" style="text-align: center;">
                <h3>No Programs Available</h3>
                <p>Please check back later or contact admissions office.</p>
            </div>
        `;
        return;
    }

    const programsHTML = programs.map(program => `
        <div class="card program-card" data-type="${program.program_type.toLowerCase()}" data-dept="${program.department_code.toLowerCase()}">
            <div class="card-header">
                <div class="card-icon" style="background: linear-gradient(135deg, #667eea, #764ba2);">🎓</div>
                <div>
                    <div class="card-title">${program.name}</div>
                    <div class="card-subtitle">${program.department_code} • ${program.program_type}</div>
                </div>
            </div>
            <div class="card-content">
                <p>${program.description}</p>
                <div style="margin: 15px 0;">
                    <strong>💰 Cost:</strong> ${program.total_cost.toLocaleString()} BDT<br>
                    <strong>⏱️ Duration:</strong> ${program.duration} years<br>
                    <strong>📚 Credits:</strong> ${program.credits}
                </div>
                <div>
                    <strong>🎯 Career Prospects:</strong><br>
                    <small>${program.career_prospects.join(', ')}</small>
                </div>
            </div>
            <div class="card-actions">
                <button class="btn btn-primary flex-1" onclick="viewProgramDetails('${program.code}')">View Details</button>
                <button class="btn btn-secondary flex-1" onclick="applyForProgram('${program.code}')">Apply Now</button>
            </div>
        </div>
    `).join('');

    grid.innerHTML = programsHTML;
}

function displayProgramsError() {
    const grid = document.getElementById('programs-grid');
    if (!grid) return;

    grid.innerHTML = `
        <div class="card" style="text-align: center; color: #ef4444;">
            <h3>❌ Unable to load programs</h3>
            <p>Please try refreshing the page or contact support if the problem persists.</p>
            <button class="btn btn-primary" onclick="loadPrograms()">Try Again</button>
        </div>
    `;
}

function handleProgramSearch(e) {
    const query = e.target.value.toLowerCase();
    const cards = document.querySelectorAll('.program-card');

    cards.forEach(card => {
        const title = card.querySelector('.card-title').textContent.toLowerCase();
        const content = card.querySelector('.card-content').textContent.toLowerCase();

        if (title.includes(query) || content.includes(query)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

function setupFilterTags() {
    const filterTags = document.querySelectorAll('.filter-tag');
    filterTags.forEach(tag => {
        tag.addEventListener('click', function() {
            // Remove active class from all tags
            filterTags.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            const filter = this.dataset.filter;
            filterPrograms(filter);
        });
    });
}

function filterPrograms(filter) {
    const cards = document.querySelectorAll('.program-card');

    cards.forEach(card => {
        if (filter === 'all') {
            card.style.display = 'block';
        } else {
            const type = card.dataset.type;
            const dept = card.dataset.dept;

            if (type === filter || dept.includes(filter)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        }
    });
}

// Waiver calculation
async function handleWaiverCalculation(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        faculty: formData.get('faculty'),
        ssc_gpa: parseFloat(formData.get('ssc_gpa')) || 0,
        hsc_gpa: parseFloat(formData.get('hsc_gpa')) || 0,
        is_new_student: true,
        current_sgpa: 0,
        student_profile: {
            family_income: parseFloat(formData.get('family_income')) || null,
            is_freedom_fighter_child: formData.get('is_freedom_fighter_child') === 'on',
            is_diu_employee_relative: formData.get('is_diu_employee_relative') === 'on',
            has_sports_achievement: formData.get('has_sports_achievement') === 'on',
            has_diploma: formData.get('has_diploma') === 'on',
            is_international_student: formData.get('is_international_student') === 'on',
            group_admission: formData.get('group_admission') === 'on'
        }
    };

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = '🔄 Calculating...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/waivers/recommend`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Failed to calculate waivers');
        }

        const waivers = await response.json();
        displayWaiverResults(waivers);
    } catch (error) {
        console.error('Error calculating waivers:', error);
        alert('❌ Error calculating waivers. Please try again.');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

function displayWaiverResults(waivers) {
    const resultsSection = document.getElementById('waiver-results');
    const cardsContainer = document.getElementById('waiver-cards');

    if (!waivers || waivers.length === 0) {
        cardsContainer.innerHTML = `
            <div class="card" style="text-align: center; background: #fef2f2; color: #dc2626;">
                <h3>😔 No Waivers Found</h3>
                <p>Based on your current information, you don't qualify for any waivers yet. Try improving your GPA or check if you have any special achievements!</p>
            </div>
        `;
    } else {
        cardsContainer.innerHTML = waivers.map(waiver => `
            <div class="result-card">
                <div class="result-header">
                    <div class="result-title">💰 ${waiver.name}</div>
                    <div class="result-score">${waiver.waiver_percentage} Waiver!</div>
                </div>
                <div class="card-content">
                    <p>${waiver.description}</p>
                    <div style="margin: 15px 0;">
                        <strong>✅ Eligibility:</strong>
                        <ul style="margin-left: 20px;">
                            ${waiver.eligibility_criteria.map(criteria => `<li>${criteria}</li>`).join('')}
                        </ul>
                    </div>
                    <div>
                        <strong>📋 Required Documents:</strong>
                        <ul style="margin-left: 20px;">
                            ${waiver.required_documents.map(doc => `<li>${doc}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary flex-1" onclick="applyForWaiver('${waiver.id}')">Apply for Waiver</button>
                </div>
            </div>
        `).join('');
    }

    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Recommendations
async function handleRecommendations(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        interests: formData.get('interests').split(',').map(i => i.trim()).filter(i => i),
        academic_background: formData.get('academic_background'),
        career_goals: formData.get('career_goals').split(',').map(g => g.trim()).filter(g => g),
        ssc_gpa: parseFloat(formData.get('ssc_gpa')) || 0,
        hsc_gpa: parseFloat(formData.get('hsc_gpa')) || 0
    };

    // Validate input
    if (data.interests.length === 0 || data.career_goals.length === 0 || !data.academic_background) {
        alert('Please fill in all required fields: interests, academic background, and career goals.');
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = '🧠 AI Analyzing...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/recommendations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Failed to get recommendations');
        }

        const recommendations = await response.json();
        displayRecommendations(recommendations);
    } catch (error) {
        console.error('Error getting recommendations:', error);
        alert('❌ Error getting recommendations. Please try again.');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

function displayRecommendations(recommendations) {
    const resultsSection = document.getElementById('recommendation-results');
    const cardsContainer = document.getElementById('recommendation-cards');

    if (!recommendations || recommendations.length === 0) {
        cardsContainer.innerHTML = `
            <div class="card" style="text-align: center; background: #fef2f2; color: #dc2626;">
                <h3>🤔 No Perfect Matches Found</h3>
                <p>Try expanding your interests or consider exploring different career paths. All our programs are designed to help you succeed!</p>
            </div>
        `;
    } else {
        cardsContainer.innerHTML = recommendations.map((rec, index) => `
            <div class="result-card">
                <div class="result-header">
                    <div class="result-title">${index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '🎯'} ${rec.department.name}</div>
                    <div class="result-score">${Math.round(rec.match_score * 100)}% Match</div>
                </div>
                <div class="card-content">
                    <p>${rec.department.description}</p>
                    <div style="margin: 15px 0;">
                        <strong>🎯 Why This Matches:</strong>
                        <ul style="margin-left: 20px;">
                            ${rec.reasons.map(reason => `<li>${reason}</li>`).join('')}
                        </ul>
                    </div>
                    <div>
                        <strong>📚 Programs:</strong><br>
                        <small>${rec.department.programs.join(', ')}</small>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary flex-1" onclick="explorePrograms('${rec.department.name}')">Explore Programs</button>
                    <button class="btn btn-secondary flex-1" onclick="applyForProgram('${rec.department.programs[0]}')">Apply Now</button>
                </div>
            </div>
        `).join('');
    }

    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Application submission
async function handleApplicationSubmission(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        student_name: formData.get('student_name'),
        email: formData.get('email'),
        phone: formData.get('phone'),
        dob: formData.get('dob'),
        father_name: formData.get('father_name'),
        mother_name: formData.get('mother_name'),
        nid: formData.get('nid'),
        gender: formData.get('gender'),
        program_code: formData.get('program_code'),
        ssc_gpa: parseFloat(formData.get('ssc_gpa')) || 0,
        hsc_gpa: parseFloat(formData.get('hsc_gpa')) || 0,
        ssc_year: parseInt(formData.get('ssc_year')) || 0,
        hsc_year: parseInt(formData.get('hsc_year')) || 0,
        ssc_board: formData.get('ssc_board'),
        hsc_board: formData.get('hsc_board'),
        ssc_group: formData.get('ssc_group'),
        hsc_group: formData.get('hsc_group'),
        family_income: parseFloat(formData.get('family_income')) || 0,
        is_freedom_fighter_child: formData.get('is_freedom_fighter_child') === 'on',
        is_diu_employee_relative: formData.get('is_diu_employee_relative') === 'on',
        has_sports_achievement: formData.get('has_sports_achievement') === 'on',
        has_diploma: formData.get('has_diploma') === 'on',
        is_international_student: formData.get('is_international_student') === 'on',
        group_admission: formData.get('group_admission') === 'on',
        documents_submitted: ['SSC Certificate', 'HSC Certificate', 'Passport Photo']
    };

    // Basic validation
    const requiredFields = ['student_name', 'email', 'phone', 'program_code'];
    for (const field of requiredFields) {
        if (!data[field]) {
            alert(`Please fill in the ${field.replace('_', ' ')} field.`);
            return;
        }
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = '🔄 Submitting...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/applications`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to submit application');
        }

        const result = await response.json();
        showApplicationSuccess(result);
    } catch (error) {
        console.error('Error submitting application:', error);
        alert(`❌ Application submission failed: ${error.message}`);
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

function showApplicationSuccess(result) {
    const form = document.getElementById('application-form');
    const successDiv = document.getElementById('application-success');

    if (form) form.style.display = 'none';
    if (successDiv) {
        successDiv.classList.remove('hidden');
        successDiv.scrollIntoView({ behavior: 'smooth' });
    }
}

// Chat functionality
async function handleChatMessage(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const message = formData.get('message');
    const sessionId = Date.now().toString();

    if (!message.trim()) return;

    // Add user message to chat
    addChatMessage(message, 'user');

    // Clear input
    e.target.reset();

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId })
        });

        if (!response.ok) {
            throw new Error('Failed to get chat response');
        }

        const result = await response.json();
        addChatMessage(result.response, 'bot');
    } catch (error) {
        console.error('Error in chat:', error);
        addChatMessage('Sorry, I encountered an error. Please try again.', 'bot');
    }
}

function addChatMessage(message, type) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.textContent = message;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Action handlers
function viewProgramDetails(programCode) {
    alert(`📚 Program Details: ${programCode}\n\nDetailed information would be shown in a modal with:\n• Full curriculum\n• Admission requirements\n• Faculty information\n• Career outcomes`);
}

function applyForProgram(programCode) {
    // Redirect to application page with program pre-selected
    window.location.href = `/application?program=${programCode}`;
}

function applyForWaiver(waiverID) {
    alert(`🚀 Apply for Waiver: ${waiverID}\n\nYou would be redirected to the application form with this waiver pre-selected.`);
    window.location.href = '/application';
}

function explorePrograms(departmentName) {
    window.location.href = `/programs?search=${encodeURIComponent(departmentName)}`;
}

function showNotification() {
    alert('🔔 Notifications\n\n• Application deadline: 15 days left\n• New scholarship available: Merit-based 40%\n• Document upload reminder\n• Entrance exam date announced');
}

function showProfile() {
    alert('👤 Profile Menu\n\n• View Profile\n• Edit Information\n• Application History\n• Settings\n• Logout');
}

function playDemo() {
    alert('▶️ Demo Video\n\nA demo video would play here showing:\n• How to explore programs\n• Calculate waivers step by step\n• Complete application process\n• Track application status');
}

// Utility function to get URL parameters
function getUrlParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// Initialize page-specific functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Pre-fill program if specified in URL
    const programCode = getUrlParam('program');
    if (programCode) {
        const programSelect = document.querySelector('select[name="program_code"]');
        if (programSelect) {
            programSelect.value = programCode;
        }
    }

    // Pre-fill search if specified in URL
    const searchTerm = getUrlParam('search');
    if (searchTerm) {
        const searchInput = document.getElementById('program-search');
        if (searchInput) {
            searchInput.value = searchTerm;
            searchInput.dispatchEvent(new Event('input'));
        }
    }
});