let isPatientLogin = true;
let currentUser = null;
let isRecording = true;

// Login functionality
function toggleLoginType() {
    isPatientLogin = !isPatientLogin;
    const title = document.getElementById('loginTitle');
    const toggleText = document.getElementById('toggleText');
    const userIdField = document.getElementById('userId');

    if (isPatientLogin) {
        title.textContent = 'Patient Login';
        toggleText.textContent = 'Switch to Caregiver Login';
        userIdField.placeholder = 'Patient ID';
    } else {
        title.textContent = 'Caregiver Login';
        toggleText.textContent = 'Switch to Patient Login';
        userIdField.placeholder = 'Caregiver ID';
    }
}

function handleLogin() {
    const userId = document.getElementById('userId').value;
    const accessCode = document.getElementById('accessCode').value;

    if (userId && accessCode) {
        currentUser = { id: userId, type: isPatientLogin ? 'patient' : 'caregiver' };

        // Hide login view
        document.getElementById('loginView').style.display = 'none';

        // Show appropriate view with animation
        if (isPatientLogin) {
            const patientView = document.getElementById('patientView');
            patientView.classList.add('active', 'fade-in');
        } else {
            const caregiverView = document.getElementById('caregiverView');
            caregiverView.classList.add('active', 'fade-in');
        }
    } else {
        alert('Please enter both ID and access code');
    }
}

// Patient Interface Functions
const visualizer = document.querySelector('.audio-visualizer');
visualizer.addEventListener('click', () => {
  const chatStatus = document.getElementById('chatStatus');
  if (!isRecording) {
    isRecording = true;
    chatStatus.textContent = 'Listening... Speak now';
    setTimeout(() => {
      chatStatus.textContent = 'I heard you say you feel good today. How did you sleep last night?';
    }, 3000);
  } else {
    isRecording = false;
    chatStatus.textContent = 'Tap to start conversation';
  }
});

function toggleMute() {
  const chatStatus = document.getElementById('chatStatus');
  isRecording = !isRecording;
  chatStatus.textContent = isRecording ? 'Listening… Speak now' : 'Mic muted – tap to un-mute';
}

window.onload = () => { document.getElementById('chatStatus').textContent = 'Listening… Speak now'; };

function markMedicationTaken() {
    const reminderCard = document.querySelector('.medication-reminder');
    reminderCard.innerHTML = `
        <div class="reminder-header">
            <div class="reminder-icon" style="background: linear-gradient(135deg, #34C759, #30D158);">✅</div>
            <div class="reminder-content">
                <h3>Medication Taken</h3>
                <div class="reminder-time">Completed at ${new Date().toLocaleTimeString()}</div>
            </div>
        </div>
    `;
    reminderCard.classList.add('taken');

    setTimeout(() => {
        reminderCard.classList.add('slide-up');
        reminderCard.style.opacity = '0.6';
    }, 1000);
}

function snoozeMedication() {
    const reminderTime = document.querySelector('.reminder-time');
    const newTime = new Date();
    newTime.setMinutes(newTime.getMinutes() + 30);
    reminderTime.textContent = `Snoozed until ${newTime.toLocaleTimeString()}`;
}

function triggerEmergency() {
    if (confirm('Are you experiencing an emergency? This will immediately notify your caregiver.')) {
        // Simulate emergency alert
        alert('🚨 Emergency alert sent to caregiver!\n\nHelp is on the way. Stay calm.');

        // Visual feedback
        const emergencyBtn = document.querySelector('.emergency-btn');
        emergencyBtn.style.animation = 'pulse 0.5s infinite';

        setTimeout(() => {
            emergencyBtn.style.animation = '';
        }, 5000);
    }
}

// Caregiver Interface Functions
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName + 'Tab').classList.add('active');
}
