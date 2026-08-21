const { app, BrowserWindow, Menu, Tray, ipcMain, screen, nativeImage } = require('electron');
const path = require('path');
const WebSocket = require('ws');

let orbWindow = null;
let chatWindow = null;
let tray = null;
let ws = null;
let currentStatus = 'idle'; // idle | thinking | working | needs_attention | error

const WS_URL = 'ws://127.0.0.1:8765';

function createOrbWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  orbWindow = new BrowserWindow({
    width: 96,
    height: 96,
    x: width - 120,
    y: height - 120,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  orbWindow.loadFile(path.join(__dirname, 'index.html'));
  orbWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
}

function createChatWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  chatWindow = new BrowserWindow({
    width: 420,
    height: 600,
    x: width - 440,
    y: height - 730,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    show: false,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  chatWindow.loadFile(path.join(__dirname, 'chat.html'));

  chatWindow.on('blur', () => {
    // Optional auto-hide on blur
  });
}

function createTray() {
  // Create simple solid color tray icon
  const icon = nativeImage.createFromBuffer(
    Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAElJREFUOE9jZKAQMFKon2HUAAYGBoa/DAwM//9DMY42dICqGBkwUGAkXQ+yAbA8TqphGM2AgY+BYDSkGfAAhmEYDY/R8BhyGAAAK78QcSm18b4AAAAASUVORK5CYII=',
      'base64'
    )
  );

  tray = new Tray(icon);
  tray.setToolTip(`Mitchell AI (Status: ${currentStatus})`);

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Mitchell AI Assistant', enabled: false },
    { type: 'separator' },
    { label: 'Status: Idle', id: 'status-item', enabled: false },
    {
      label: 'Toggle Chat Panel',
      click: () => toggleChatWindow()
    },
    {
      label: 'Reset Position',
      click: () => {
        const { width, height } = screen.getPrimaryDisplay().workAreaSize;
        orbWindow.setPosition(width - 120, height - 120);
      }
    },
    { type: 'separator' },
    {
      label: 'Quit Mitchell',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('click', () => toggleChatWindow());
}

function toggleChatWindow() {
  if (!chatWindow) return;
  if (chatWindow.isVisible()) {
    chatWindow.hide();
  } else {
    // Position chat window above orb
    const [orbX, orbY] = orbWindow.getPosition();
    chatWindow.setPosition(Math.max(10, orbX - 320), Math.max(10, orbY - 610));
    chatWindow.show();
    chatWindow.focus();
  }
}

function updateStatus(status) {
  currentStatus = status;
  if (orbWindow && !orbWindow.isDestroyed()) {
    orbWindow.webContents.send('status-update', status);
  }
  if (chatWindow && !chatWindow.isDestroyed()) {
    chatWindow.webContents.send('status-update', status);
  }
  if (tray) {
    tray.setToolTip(`Mitchell AI (Status: ${status})`);
  }
}

function connectWebSocket() {
  ws = new WebSocket(WS_URL);

  ws.on('open', () => {
    console.log('Connected to Mitchell Python Core bridge');
    updateStatus('idle');
  });

  ws.on('message', (data) => {
    try {
      const payload = JSON.parse(data.toString());
      if (payload.type === 'status') {
        updateStatus(payload.status);
      } else if (payload.type === 'response') {
        if (chatWindow && !chatWindow.isDestroyed()) {
          chatWindow.webContents.send('chat-message', {
            role: 'assistant',
            content: payload.content
          });
        }
        if (payload.status) {
          updateStatus(payload.status);
        }
      } else if (payload.type === 'events') {
        if (chatWindow && !chatWindow.isDestroyed()) {
          chatWindow.webContents.send('events-update', payload.events);
        }
      }
    } catch (e) {
      console.error('Error handling WebSocket message:', e);
    }
  });

  ws.on('close', () => {
    console.log('WebSocket connection closed. Retrying in 2s...');
    updateStatus('error');
    setTimeout(connectWebSocket, 2000);
  });

  ws.on('error', (err) => {
    console.error('WebSocket connection error:', err.message);
  });
}

// IPC Handlers
ipcMain.on('toggle-chat', () => {
  toggleChatWindow();
});

ipcMain.on('close-chat', () => {
  if (chatWindow) chatWindow.hide();
});

ipcMain.on('show-context-menu', (event) => {
  const menu = Menu.buildFromTemplate([
    { label: `Status: ${currentStatus.toUpperCase()}`, enabled: false },
    { type: 'separator' },
    { label: 'Open Chat', click: () => toggleChatWindow() },
    {
      label: 'Set Status: Thinking',
      click: () => updateStatus('thinking')
    },
    {
      label: 'Set Status: Working',
      click: () => updateStatus('working')
    },
    {
      label: 'Set Status: Idle',
      click: () => updateStatus('idle')
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);
  menu.popup({ window: BrowserWindow.fromWebContents(event.sender) });
});

ipcMain.on('send-message', (event, text) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    updateStatus('thinking');
    ws.send(JSON.stringify({ type: 'message', content: text }));
  } else {
    // Echo fallback if python is not running
    if (chatWindow) {
      chatWindow.webContents.send('chat-message', {
        role: 'assistant',
        content: `[Offline] Mitchell Core is not running on ${WS_URL}. You said: ${text}`
      });
    }
  }
});

ipcMain.on('request-events', () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'get_events' }));
  }
});

app.whenReady().then(() => {
  createOrbWindow();
  createChatWindow();
  createTray();
  connectWebSocket();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createOrbWindow();
      createChatWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
