// pywebview_bridge.js - Bridge between JavaScript and pywebview API
// This replaces all fetch() calls with pywebview API calls

(function() {
  'use strict';

  // Check if we're running in pywebview
  const isPywebview = typeof window.pywebview !== 'undefined';
  
  if (!isPywebview) {
    console.warn('[PywebviewBridge] pywebview API not available, falling back to fetch');
  }

  // Get the pywebview API object
  function getAPI() {
    if (isPywebview && window.pywebview && window.pywebview.api) {
      return window.pywebview.api;
    }
    return null;
  }

  // Log message handler (called from Python)
  window.handleLogMessage = function(message) {
    const consoleOutput = document.getElementById('consoleOutput');
    if (consoleOutput && window.appendLogLine) {
      window.appendLogLine(message);
    }
  };

  // Progress update handler (called from Python)
  window.handleProgressUpdate = function(progress) {
    if (window.updateProgressBar) {
      window.updateProgressBar(progress);
    }
  };

  // API wrapper that handles both pywebview and fetch fallback
  window.AceForgeAPI = {
    // Generation
    generate: async function(params) {
      const api = getAPI();
      if (api && api.generate) {
        try {
          return await api.generate(params);
        } catch (error) {
          console.error('[API] Generate error:', error);
          return { status: 'error', message: String(error) };
        }
      }
      // Fallback to fetch
      const formData = new FormData();
      for (const [key, value] of Object.entries(params)) {
        if (value !== null && value !== undefined) {
          formData.append(key, value);
        }
      }
      const response = await fetch('/generate', { method: 'POST', body: formData });
      return await response.json();
    },

    // Tracks
    listTracks: async function() {
      const api = getAPI();
      if (api && api.listTracks) {
        try {
          return await api.listTracks();
        } catch (error) {
          console.error('[API] List tracks error:', error);
          return { tracks: [], current: null };
        }
      }
      const response = await fetch('/tracks.json');
      return await response.json();
    },

    getTrackMeta: async function(name) {
      const api = getAPI();
      if (api && api.getTrackMeta) {
        try {
          return await api.getTrackMeta(name);
        } catch (error) {
          return { error: String(error) };
        }
      }
      const response = await fetch(`/tracks/meta?name=${encodeURIComponent(name)}`);
      return await response.json();
    },

    updateTrackMeta: async function(name, updates) {
      const api = getAPI();
      if (api && api.updateTrackMeta) {
        try {
          return await api.updateTrackMeta(name, updates);
        } catch (error) {
          return { error: String(error) };
        }
      }
      const response = await fetch('/tracks/meta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, ...updates })
      });
      return await response.json();
    },

    renameTrack: async function(oldName, newName) {
      const api = getAPI();
      if (api && api.renameTrack) {
        try {
          return await api.renameTrack(oldName, newName);
        } catch (error) {
          return { error: String(error) };
        }
      }
      const response = await fetch('/tracks/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_name: oldName, new_name: newName })
      });
      return await response.json();
    },

    deleteTrack: async function(name) {
      const api = getAPI();
      if (api && api.deleteTrack) {
        try {
          return await api.deleteTrack(name);
        } catch (error) {
          return { error: String(error) };
        }
      }
      const response = await fetch('/tracks/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      return await response.json();
    },

    // Progress
    getProgress: async function() {
      const api = getAPI();
      if (api && api.getProgress) {
        try {
          return await api.getProgress();
        } catch (error) {
          return { current: 0, total: 1, done: false, error: false, stage: '' };
        }
      }
      const response = await fetch('/progress');
      return await response.json();
    },

    // Models
    getModelStatus: async function() {
      const api = getAPI();
      if (api && api.getModelStatus) {
        try {
          return await api.getModelStatus();
        } catch (error) {
          return { state: 'unknown', message: String(error) };
        }
      }
      const response = await fetch('/models/status');
      const data = await response.json();
      return { state: data.state, message: data.message };
    },

    downloadModels: async function() {
      const api = getAPI();
      if (api && api.downloadModels) {
        try {
          return await api.downloadModels();
        } catch (error) {
          return { status: 'error', message: String(error) };
        }
      }
      const response = await fetch('/models/ensure', { method: 'POST' });
      return await response.json();
    },

    // Presets
    listPresets: async function() {
      const api = getAPI();
      if (api && api.listPresets) {
        try {
          return await api.listPresets();
        } catch (error) {
          return { ok: false, presets: [] };
        }
      }
      const response = await fetch('/user_presets');
      return await response.json();
    },

    savePreset: async function(presetData) {
      const api = getAPI();
      if (api && api.savePreset) {
        try {
          return await api.savePreset(presetData);
        } catch (error) {
          return { error: String(error) };
        }
      }
      const response = await fetch('/user_presets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(presetData)
      });
      return await response.json();
    },

    // Prompt/Lyrics
    generatePromptLyrics: async function(params) {
      const api = getAPI();
      if (api && api.generatePromptLyrics) {
        try {
          return await api.generatePromptLyrics(params);
        } catch (error) {
          return { error: String(error) };
        }
      }
      const response = await fetch('/prompt_lyrics/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      return await response.json();
    },

    // Utility
    getDefaults: async function() {
      const api = getAPI();
      if (api && api.getDefaults) {
        try {
          return await api.getDefaults();
        } catch (error) {
          return {};
        }
      }
      return {
        target_seconds: 90,
        fade_in: 0.5,
        fade_out: 0.5,
        steps: 55,
        guidance_scale: 6.0,
      };
    },

    shutdown: async function() {
      const api = getAPI();
      if (api && api.shutdown) {
        try {
          await api.shutdown();
          // Close window if in pywebview
          if (isPywebview && window.pywebview) {
            window.pywebview.window.close();
          }
          return { status: 'ok' };
        } catch (error) {
          return { error: String(error) };
        }
      }
      const response = await fetch('/shutdown', { method: 'POST' });
      return await response.json();
    }
  };

  // Start polling for progress updates if in pywebview
  if (isPywebview) {
    let progressInterval = null;
    
    function startProgressPolling() {
      if (progressInterval) return;
      
      progressInterval = setInterval(async () => {
        try {
          const progress = await window.AceForgeAPI.getProgress();
          if (window.handleProgressUpdate) {
            window.handleProgressUpdate(progress);
          }
        } catch (error) {
          // Ignore errors
        }
      }, 500); // Poll every 500ms
    }
    
    // Start polling when page loads
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', startProgressPolling);
    } else {
      startProgressPolling();
    }
  }

  console.log('[PywebviewBridge] Initialized', isPywebview ? '(pywebview mode)' : '(fallback mode)');
})();
