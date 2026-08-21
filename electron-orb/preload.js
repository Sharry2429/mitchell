const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  toggleChat: () => ipcRenderer.send('toggle-chat'),
  closeChat: () => ipcRenderer.send('close-chat'),
  showContextMenu: () => ipcRenderer.send('show-context-menu'),
  sendMessage: (text) => ipcRenderer.send('send-message', text),
  onStatusUpdate: (callback) => ipcRenderer.on('status-update', (event, value) => callback(value)),
  onChatMessage: (callback) => ipcRenderer.on('chat-message', (event, value) => callback(value)),
  onEventsUpdate: (callback) => ipcRenderer.on('events-update', (event, value) => callback(value)),
  requestEvents: () => ipcRenderer.send('request-events')
});
