document.addEventListener("DOMContentLoaded", function () {
    const uploadButton = document.getElementById("uploadBtn");
    const imageInput = document.getElementById("imageUpload");
    const resultDiv = document.getElementById("result");
  
    uploadButton.addEventListener("click", function () {
      const file = imageInput.files[0];
  
      if (!file) {
        resultDiv.textContent = "Please select an image.";
        resultDiv.style.display = "block";
        return;
      }
  
      if (file.type !== "image/png") {
        resultDiv.textContent = "Only PNG images are supported.";
        resultDiv.style.display = "block";
        return;
      }
  
      // Show loading state
      resultDiv.textContent = "Uploading image...";
      resultDiv.style.display = "block";
  
      const reader = new FileReader();
      reader.onloadend = function () {
        // Extract base64 data and ensure it has the "data:image/png;base64," prefix
        let base64Image = reader.result;
      
        if (!base64Image.startsWith("data:image/png;base64,")) {
          // If the base64 data doesn't start with the correct prefix, add it
          base64Image = "data:image/png;base64," + base64Image.split(",")[1];
        }
      
        // Send to background.js for analysis
        chrome.runtime.sendMessage(
          { action: "analyzeImage", imageData: base64Image },
          function (response) {
            if (chrome.runtime.lastError) {
              resultDiv.textContent = "Error: " + chrome.runtime.lastError.message;
              return;
            }
      
            // Handle the response
            if (response && response.result) {
              resultDiv.textContent = "Result: " + response.result;
            } else {
              resultDiv.textContent = "Analysis failed or returned no result.";
            }
          }
        );
      };
      
  
      reader.readAsDataURL(file);
    });
  });
  