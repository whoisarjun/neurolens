let isPatientLogin = true;
let currentUser = null;
let isRecording = true;

document.addEventListener('DOMContentLoaded', () => {
  const chatStatus = document.getElementById('chatStatus');
  const visualizer = document.querySelector('.audio-visualizer');
  const micIcon    = document.querySelector('.microphone-icon');

  visualizer.classList.add('listening');
  micIcon.textContent = '🎤';
  chatStatus.textContent = 'Listening...';
});

// Login part
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

        document.getElementById('loginView').style.display = 'none';

        if (isPatientLogin) {
            document.getElementById('patientView').classList.add('active', 'fade-in');
        } else {
            document.getElementById('caregiverView').classList.add('active', 'fade-in');
        }
    } else {
        alert('Please enter both ID and access code');
    }
}

// patient view
const visualizer = document.querySelector('.audio-visualizer');
visualizer.addEventListener('click', toggleMute);

function toggleMute() {
  const chatStatus = document.getElementById('chatStatus');
  const micIcon    = document.querySelector('.microphone-icon');
  const waves      = document.querySelectorAll('.wave-animation');

  isRecording = !isRecording;

  chatStatus.textContent = isRecording ? 'Listening...' : 'Muted';
  micIcon.textContent    = isRecording ? '🎤' : '🔇';

  visualizer.classList.toggle('muted',  !isRecording);
  visualizer.classList.toggle('listening', isRecording);

  waves.forEach(w => {
    w.style.display = isRecording ? 'block' : 'none';
  });
}

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
        alert('🚨 Emergency alert sent to caregiver!\n\nHelp is on the way. Stay calm.');

        const emergencyBtn = document.querySelector('.emergency-btn');
        emergencyBtn.style.animation = 'pulse 0.5s infinite';

        setTimeout(() => {
            emergencyBtn.style.animation = '';
        }, 5000);
    }
}

// caregiver
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName + 'Tab').classList.add('active');
}
