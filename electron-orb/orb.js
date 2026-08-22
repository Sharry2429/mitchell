const orbContainer = document.getElementById('orb-container');

// State classes mapping (7 Peak States)
const STATES = ['idle', 'listening', 'thinking', 'speaking', 'working', 'success', 'needs_attention', 'error'];

function setOrbStatus(status) {
  STATES.forEach(s => orbContainer.classList.remove(s));
  if (STATES.includes(status)) {
    orbContainer.classList.add(status);
  } else {
    orbContainer.classList.add('idle');
  }
}

// Click handlers
orbContainer.addEventListener('click', (e) => {
  if (e.button === 0) {
    // Left click: toggle chat panel
    window.electronAPI.toggleChat();
  }
});

orbContainer.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  // Right click: show context menu
  window.electronAPI.showContextMenu();
});

// IPC Listener for real-time status updates from Python
window.electronAPI.onStatusUpdate((status) => {
  setOrbStatus(status);
});
