// cdmf_voice_cloning_ui.js
// Voice cloning form submission and UI handling

(function () {
  "use strict";

  window.CDMF = window.CDMF || {};
  var CDMF = window.CDMF;

  CDMF.onSubmitVoiceClone = function (event) {
    event.preventDefault();
    
    var form = event.target;
    var formData = new FormData(form);
    
    // Get output directory from Settings (sync with generate form)
    var outDirInput = document.getElementById("out_dir_settings");
    if (outDirInput) {
      formData.set("out_dir", outDirInput.value);
    }
    
    // Show loading bar
    var loadingBar = document.getElementById("voiceCloneLoadingBar");
    if (loadingBar) {
      loadingBar.style.display = "block";
    }
    
    // Disable submit button
    var submitBtn = document.getElementById("voiceCloneButton");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="icon">⏳</span><span>Cloning...</span>';
    }
    
    // Make API call
    fetch("/voice_clone", {
      method: "POST",
      body: formData,
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        // Hide loading bar
        if (loadingBar) {
          loadingBar.style.display = "none";
        }
        
        // Re-enable submit button
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<span class="icon">🎤</span><span>Clone Voice</span>';
        }
        
        if (data.error) {
          // Show error message
          var errorMsg = data.message || "Voice cloning failed";
          if (CDMF.showToast) {
            CDMF.showToast(errorMsg, "error");
          } else {
            alert(errorMsg);
          }
          if (data.details && window.console) {
            console.error("[Voice Cloning] Error details:", data.details);
          }
        } else {
          // Show success message
          var successMsg = data.message || "Voice cloning completed!";
          if (CDMF.showToast) {
            CDMF.showToast(successMsg, "success");
          } else {
            console.log("[Voice Cloning] " + successMsg);
          }
          
          // Refresh Music Player to show the new file
          if (window.CDMF && CDMF.refreshTracksAfterGeneration) {
            CDMF.refreshTracksAfterGeneration({ autoplay: true });
          } else if (data.tracks && window.CDMF && CDMF.updateTrackList) {
            CDMF.updateTrackList(data.tracks);
          }
          
          // Reset form (optional - keep values for convenience)
          // form.reset();
        }
      })
      .catch(function (error) {
        // Hide loading bar
        if (loadingBar) {
          loadingBar.style.display = "none";
        }
        
        // Re-enable submit button
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<span class="icon">🎤</span><span>Clone Voice</span>';
        }
        
        // Show error
        var errorMsg = "Voice cloning failed: " + error.message;
        if (CDMF.showToast) {
          CDMF.showToast(errorMsg, "error");
        } else {
          alert(errorMsg);
        }
        if (window.console) {
          console.error("[Voice Cloning] Request failed:", error);
        }
      });
    
    return false;
  };

  // Sync output directory from Settings when voice cloning form is shown
  CDMF.syncVoiceCloneOutputDir = function () {
    var outDirSettings = document.getElementById("out_dir_settings");
    var outDirVoiceClone = document.getElementById("voice_clone_out_dir");

    if (outDirSettings && outDirVoiceClone) {
      outDirVoiceClone.value = outDirSettings.value;
    }
  };

  // Apply voice clone track metadata into the Voice Clone form (used by "copy settings" in Music Player)
  CDMF.applyVoiceCloneSettingsToForm = function (settings) {
    if (!settings) return;

    if (typeof CDMF.switchMode === "function") {
      CDMF.switchMode("voice_clone");
    }

    function setVal(id, v) {
      var el = document.getElementById(id);
      if (el && v != null && v !== "") {
        el.value = String(v);
      }
    }

    function setNumPair(numId, rangeId, v) {
      if (v == null || Number.isNaN(v)) return;
      var s = String(v);
      var num = document.getElementById(numId);
      var rng = document.getElementById(rangeId);
      if (num) num.value = s;
      if (rng) rng.value = s;
    }

    setVal("voice_clone_text", settings.text);
    setVal("voice_clone_output_filename", settings.basename);
    setVal("voice_clone_language", settings.language);
    setVal("voice_clone_device", settings.device_preference);
    setNumPair("voice_clone_temperature", "voice_clone_temperature_range", settings.temperature);
    setNumPair("voice_clone_length_penalty", "voice_clone_length_penalty_range", settings.length_penalty);
    setNumPair("voice_clone_repetition_penalty", "voice_clone_repetition_penalty_range", settings.repetition_penalty);
    setVal("voice_clone_top_k", settings.top_k);
    setNumPair("voice_clone_top_p", "voice_clone_top_p_range", settings.top_p);
    setNumPair("voice_clone_speed", "voice_clone_speed_range", settings.speed);

    var cb = document.getElementById("voice_clone_enable_text_splitting");
    if (cb && typeof settings.enable_text_splitting === "boolean") {
      cb.checked = settings.enable_text_splitting;
    }

    setVal("voice_clone_out_dir", settings.out_dir);
  };

  // Initialize on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      // Sync output directory when voice cloning mode is activated
      var voiceCloneTab = document.querySelector('[data-mode="voice_clone"]');
      if (voiceCloneTab) {
        voiceCloneTab.addEventListener("click", function () {
          setTimeout(CDMF.syncVoiceCloneOutputDir, 100);
        });
      }
    });
  } else {
    // DOM already loaded
    var voiceCloneTab = document.querySelector('[data-mode="voice_clone"]');
    if (voiceCloneTab) {
      voiceCloneTab.addEventListener("click", function () {
        setTimeout(CDMF.syncVoiceCloneOutputDir, 100);
      });
    }
  }
})();
