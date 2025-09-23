// scripts.js
async function fetchPrograms() {
    try {
        const response = await fetch('/programs');
        const programs = await response.json();
        const list = document.getElementById('programs-list');
        list.innerHTML = programs.map(program => `
            <div class="card bg-white p-4 rounded shadow mb-4">
                <h3 class="text-lg font-bold">${program.name}</h3>
                <p><strong>Code:</strong> ${program.code}</p>
                <p><strong>Department:</strong> ${program.department_code}</p>
                <p><strong>Cost:</strong> ${program.total_cost} BDT</p>
                <p><strong>Credits:</strong> ${program.credits}</p>
                <p><strong>Duration:</strong> ${program.duration} years</p>
                <p><strong>Description:</strong> ${program.description}</p>
                <p><strong>Eligibility:</strong> ${program.eligibility.join(', ')}</p>
                <p><strong>Career Prospects:</strong> ${program.career_prospects.join(', ')}</p>
                <p><strong>Admission Deadline:</strong> ${program.admission_deadline}</p>
                <p><strong>Program Type:</strong> ${program.program_type}</p>
                <p><strong>Accreditation:</strong> ${program.accreditation}</p>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading programs:', error);
    }
}