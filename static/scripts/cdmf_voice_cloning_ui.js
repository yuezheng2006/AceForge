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
