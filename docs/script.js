/**
 * Mitchell Documentation & Developer Portal Interactive Scripts
 */

// 1. Theme Switcher
function changeTheme(themeName) {
  if (themeName === 'default') {
    document.documentElement.removeAttribute('data-theme');
  } else {
    document.documentElement.setAttribute('data-theme', themeName);
  }
  localStorage.setItem('mitchell-theme', themeName);
}

// Restore saved theme on page load
document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = localStorage.getItem('mitchell-theme');
  if (savedTheme) {
    const selector = document.getElementById('theme-selector');
    if (selector) selector.value = savedTheme;
    changeTheme(savedTheme);
  }
});

// 2. Install Tab Switcher
const installCommands = {
  ps1: 'powershell -ExecutionPolicy Bypass -File scripts\\install.ps1',
  sh: 'bash scripts/install.sh',
  docker: 'docker compose up -d',
  sdk: 'pip install -e .',
};

function setInstallTab(tabKey) {
  const cmdElem = document.getElementById('install-cmd');
  if (cmdElem && installCommands[tabKey]) {
    cmdElem.textContent = installCommands[tabKey];
  }

  const tabButtons = document.querySelectorAll('#install-tabs button');
  tabButtons.forEach(btn => {
    btn.className = 'px-2.5 py-1 text-xs font-mono rounded-md text-slate hover:text-white';
  });

  const activeBtn = document.getElementById(`tab-${tabKey}`);
  if (activeBtn) {
    activeBtn.className = 'px-2.5 py-1 text-xs font-mono rounded-md bg-white/10 text-white';
  }
}

function copyInstallCmd() {
  const cmdElem = document.getElementById('install-cmd');
  const copyBtn = document.getElementById('copy-btn');
  if (cmdElem && copyBtn) {
    navigator.clipboard.writeText(cmdElem.textContent.trim());
    copyBtn.innerHTML = '<i class="fa-solid fa-check text-mint"></i> Copied!';
    setTimeout(() => {
      copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
    }, 2000);
  }
}

// 3. Documentation Section Tabs Switcher
function showDocTab(tabName) {
  const tabs = ['quickstart', 'sdk', 'architecture', 'cli', 'api'];
  
  tabs.forEach(t => {
    const content = document.getElementById(`content-${t}`);
    const btn = document.getElementById(`btn-doc-${t}`);
    
    if (content) {
      if (t === tabName) {
        content.classList.remove('hidden');
      } else {
        content.classList.add('hidden');
      }
    }

    if (btn) {
      if (t === tabName) {
        btn.className = 'tab-btn active px-4 py-2 rounded-lg text-xs font-mono';
      } else {
        btn.className = 'tab-btn px-4 py-2 rounded-lg text-xs font-mono text-slate hover:text-white';
      }
    }
  });
}

// 4. Interactive Terminal Emulator
function setTerminalPreset(cmdText) {
  const input = document.getElementById('terminal-input');
  if (input) {
    input.value = cmdText;
    executeTerminalCmd();
  }
}

function executeTerminalCmd() {
  const input = document.getElementById('terminal-input');
  const screen = document.getElementById('terminal-screen');
  if (!input || !screen) return;

  const rawCmd = input.value.trim();
  if (!rawCmd) return;

  input.value = '';

  // Append user command
  const timeStr = new Date().toTimeString().split(' ')[0];
  const userP = document.createElement('p');
  userP.className = 'text-white font-bold';
  userP.textContent = `[${timeStr}] $ ${rawCmd}`;
  screen.appendChild(userP);

  // Simulate realistic autonomous hive processing
  const responseP = document.createElement('p');
  responseP.className = 'text-lavender animate-pulse';
  responseP.textContent = `[${timeStr}] 🧠 Manager Loop: Decomposing goal and dispatching specialized agents...`;
  screen.appendChild(responseP);
  screen.scrollTop = screen.scrollHeight;

  setTimeout(() => {
    responseP.classList.remove('animate-pulse');
    responseP.className = 'text-mint';

    if (rawCmd.includes('benchmark')) {
      responseP.innerHTML = `[${timeStr}] 🏆 <strong>Benchmark Arena Complete:</strong> 26/26 Scenarios Passed (100.0% Pass Rate). Cost: ₹0.00.`;
    } else if (rawCmd.includes('security')) {
      responseP.innerHTML = `[${timeStr}] 🛡️ <strong>Security Audit Passed:</strong> SHA256 Log Hash Chain Validated. Risk Policy: Active.`;
    } else if (rawCmd.includes('evolve')) {
      responseP.innerHTML = `[${timeStr}] 🧬 <strong>Self-Evolution Engine:</strong> AST Inspection clean, 0 syntax violations. Self-repair ready.`;
    } else {
      responseP.innerHTML = `[${timeStr}] ✓ <strong>Autonomous Task Succeeded:</strong> Claim posted to Blackboard topic <code>#results</code>. Tokens: 412 (₹0.003).`;
    }

    screen.scrollTop = screen.scrollHeight;
  }, 900);
}

// Allow Enter key to trigger terminal
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('terminal-input');
  if (input) {
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        executeTerminalCmd();
      }
    });
  }
});
