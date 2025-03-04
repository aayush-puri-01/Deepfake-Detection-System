chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
    if (request.action === "analyzeImage") {
      const imageData = request.imageData;
      const serverUrl = "http://127.0.0.1:5000/analyze";
  
      fetch(serverUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ image: imageData }),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Server responded with status " + response.status);
          }
          return response.json();
        })
        .then((data) => {
          sendResponse({
            success: true,
            result: data.isDeepfake
              ? `This image appears to be a deepfake (confidence: ${data.confidence}%)`
              : `This image appears to be authentic (confidence: ${data.confidence}%)`,
          });
        })
        .catch((error) => {
          sendResponse({
            success: false,
            result: "Error: " + error.message,
          });
        });
  
      // Keep the message channel open for asynchronous response
      return true;
    }
  });
  