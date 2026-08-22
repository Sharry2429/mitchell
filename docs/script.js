// Interactive Simulator Controller

let currentMode = 'windows';

function setMode(mode) {
  currentMode = mode;
  const title = document.getElementById('active-pillar-title');
  const btnWin = document.getElementById('btn-windows');
  const btnAnd = document.getElementById('btn-android');
  const btnBro = document.getElementById('btn-browser');

  [btnWin, btnAnd, btnBro].forEach(b => {
    b.className = "px-6 py-2.5 rounded-xl text-sm font-display font-medium text-slate hover:text-white";
  });

  if (mode === 'windows') {
    btnWin.className = "px-6 py-2.5 rounded-xl text-sm font-display font-medium text-white bg-white/10";
    title.textContent = "Pillar: Windows UIA Automation";
    logOutput("Switched active focus to Native Windows UIA pillar.");
  } else if (mode === 'android') {
    btnAnd.className = "px-6 py-2.5 rounded-xl text-sm font-display font-medium text-white bg-white/10";
    title.textContent = "Pillar: Wireless Android Touch";
    logOutput("Switched active focus to Android Wireless ADB pillar.");
  } else {
    btnBro.className = "px-6 py-2.5 rounded-xl text-sm font-display font-medium text-white bg-white/10";
    title.textContent = "Pillar: Playwright Browser & Deep Research";
    logOutput("Switched active focus to Playwright Browser & Research pillar.");
  }
}

function setGoal(goal) {
  document.getElementById('goal-input').value = goal;
}

function logOutput(msg, color = 'text-mint') {
  const box = document.getElementById('console-output');
  const time = new Date().toTimeString().split(' ')[0];
  const p = document.createElement('p');
  p.className = color;
  p.textContent = `[${time}] ${msg}`;
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

function runSimulation() {
  const input = document.getElementById('goal-input');
  const goal = input.value.trim();
  if (!goal) return;

  logOutput(`Target Goal Received: "${goal}"`, 'text-lavender');
  logOutput("1. Fast Intent Analyzer: Evaluating goal complexity...", 'text-slate');
  
  setTimeout(() => {
    logOutput("2. Goal Classifier: Formulating structured TaskGraph...", 'text-slate');
  }, 400);

  setTimeout(() => {
    logOutput("3. Critic Pass: Verified pre-conditions & safety invariants.", 'text-slate');
  }, 800);

  setTimeout(() => {
    logOutput("4. Hive Router: Dispatched subtasks to specialized worker agents.", 'text-slate');
  }, 1200);

  setTimeout(() => {
    logOutput(`✓ Execution Completed Successfully across ${currentMode.toUpperCase()} environment!`, 'text-mint font-semibold');
  }, 1800);

  input.value = '';
}
