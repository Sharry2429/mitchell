/**
 * Mitchell Official Documentation Portal Scripts
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
    btn.className = 'px-2.5 py-1 text-xs font-mono rounded text-slate hover:text-white';
  });

  const activeBtn = document.getElementById(`tab-${tabKey}`);
  if (activeBtn) {
    activeBtn.className = 'px-2.5 py-1 text-xs font-mono rounded bg-white/10 text-white';
  }
}

// 3. Universal Copy Function
function copySnippet(elementId, btnElement) {
  const elem = document.getElementById(elementId);
  if (!elem || !btnElement) return;

  const textToCopy = elem.innerText || elem.textContent;
  navigator.clipboard.writeText(textToCopy.trim()).then(() => {
    const originalHTML = btnElement.innerHTML;
    btnElement.innerHTML = '<i class="fa-solid fa-check text-mint"></i> Copied!';
    setTimeout(() => {
      btnElement.innerHTML = originalHTML;
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy text: ', err);
  });
}

// 4. Documentation Tabs Switcher
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
        btn.className = 'tab-btn active px-3 py-1.5 rounded text-xs font-mono';
      } else {
        btn.className = 'tab-btn px-3 py-1.5 rounded text-xs font-mono text-slate hover:text-white';
      }
    }
  });
}

// 5. CLI Table Search Filter
function filterCLITable() {
  const input = document.getElementById('cli-search');
  const filter = input ? input.value.toLowerCase() : '';
  const rows = document.querySelectorAll('#cli-table tbody tr');

  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    if (text.includes(filter)) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

// 6. Page Initialization
document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = localStorage.getItem('mitchell-theme');
  if (savedTheme) {
    const selector = document.getElementById('theme-selector');
    if (selector) selector.value = savedTheme;
    changeTheme(savedTheme);
  }
});
