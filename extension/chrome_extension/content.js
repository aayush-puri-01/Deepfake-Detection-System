// content.js - updated version with region selection

let selectionDiv = null;
let startX, startY;
let isSelecting = false;

function createSelectionInterface() {
  // Remove existing selection if any
  removeSelectionInterface();
  
  // Create selection overlay
  const overlay = document.createElement('div');
  overlay.id = 'dfdetector-overlay';
  overlay.style.position = 'fixed';
  overlay.style.top = '0';
  overlay.style.left = '0';
  overlay.style.width = '100%';
  overlay.style.height = '100%';
  overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
  overlay.style.zIndex = '2147483647'; // Max z-index
  overlay.style.cursor = 'crosshair';
  
  // Create selection div
  selectionDiv = document.createElement('div');
  selectionDiv.id = 'dfdetector-selection';
  selectionDiv.style.position = 'fixed';
  selectionDiv.style.border = '2px dashed white';
  selectionDiv.style.backgroundColor = 'rgba(66, 133, 244, 0.2)';
  selectionDiv.style.display = 'none';
  selectionDiv.style.zIndex = '2147483647';
  
  // Create instruction text
  const instructions = document.createElement('div');
  instructions.textContent = 'Click and drag to select area for deepfake detection';
  instructions.style.position = 'fixed';
  instructions.style.top = '10px';
  instructions.style.left = '50%';
  instructions.style.transform = 'translateX(-50%)';
  instructions.style.backgroundColor = 'black';
  instructions.style.color = 'white';
  instructions.style.padding = '8px 12px';
  instructions.style.borderRadius = '4px';
  instructions.style.zIndex = '2147483648';
  instructions.style.fontFamily = 'Arial, sans-serif';
  
  // Add mousedown event to start selection
  overlay.addEventListener('mousedown', function(e) {
    isSelecting = true;
    startX = e.clientX;
    startY = e.clientY;
    
    selectionDiv.style.left = startX + 'px';
    selectionDiv.style.top = startY + 'px';
    selectionDiv.style.width = '0';
    selectionDiv.style.height = '0';
    selectionDiv.style.display = 'block';
  });
  
  // Add mousemove event to resize selection
  overlay.addEventListener('mousemove', function(e) {
    if (!isSelecting) return;
    
    const currentX = e.clientX;
    const currentY = e.clientY;
    
    const width = Math.abs(currentX - startX);
    const height = Math.abs(currentY - startY);
    
    selectionDiv.style.left = Math.min(startX, currentX) + 'px';
    selectionDiv.style.top = Math.min(startY, currentY) + 'px';
    selectionDiv.style.width = width + 'px';
    selectionDiv.style.height = height + 'px';
  });
  
  // Add mouseup event to complete selection
  overlay.addEventListener('mouseup', function(e) {
    if (!isSelecting) return;
    isSelecting = false;
    
    // Ensure we have a minimum selection size
    const width = parseInt(selectionDiv.style.width);
    const height = parseInt(selectionDiv.style.height);
    
    if (width < 10 || height < 10) {
      // Selection too small
      alert('Selected area is too small. Please try again.');
      return;
    }
    
    // Get the coordinates
    const rect = {
      x: parseInt(selectionDiv.style.left),
      y: parseInt(selectionDiv.style.top),
      width: width,
      height: height
    };
    
    // Capture the screenshot of the selected area
    captureSelectedArea(rect);
  });
  
  // Add escape key to cancel selection
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      removeSelectionInterface();
    }
  });
  
  // Append elements to body
  document.body.appendChild(overlay);
  document.body.appendChild(selectionDiv);
  document.body.appendChild(instructions);
}

function removeSelectionInterface() {
  const overlay = document.getElementById('dfdetector-overlay');
  const selection = document.getElementById('dfdetector-selection');
  const instructions = document.querySelector('div[style*="translateX(-50%)"]');
  
  if (overlay) overlay.remove();
  if (selection) selection.remove();
  if (instructions) instructions.remove();
  
  isSelecting = false;
}

function captureSelectedArea(rect) {
  // Set the status message
  const statusDiv = document.createElement('div');
  statusDiv.id = 'dfdetector-status';
  statusDiv.textContent = 'Capturing selected area...';
  statusDiv.style.position = 'fixed';
  statusDiv.style.top = '10px';
  statusDiv.style.left = '50%';
  statusDiv.style.transform = 'translateX(-50%)';
  statusDiv.style.backgroundColor = 'black';
  statusDiv.style.color = 'white';
  statusDiv.style.padding = '8px 12px';
  statusDiv.style.borderRadius = '4px';
  statusDiv.style.zIndex = '2147483648';
  statusDiv.style.fontFamily = 'Arial, sans-serif';
  document.body.appendChild(statusDiv);
  
  // Use html2canvas to capture the page
  // We need to adjust for scroll position
  const scrollX = window.scrollX;
  const scrollY = window.scrollY;
  
  // Adjust rect coordinates to account for scroll
  const absoluteRect = {
    x: rect.x + scrollX,
    y: rect.y + scrollY,
    width: rect.width,
    height: rect.height
  };
  
  html2canvas(document.documentElement, {
    useCORS: true,
    allowTaint: true,
    scrollX: -scrollX,
    scrollY: -scrollY,
    windowWidth: document.documentElement.offsetWidth,
    windowHeight: document.documentElement.offsetHeight
  }).then(function(canvas) {
    try {
      // Create a new canvas for just the cropped area
      const croppedCanvas = document.createElement('canvas');
      croppedCanvas.width = rect.width;
      croppedCanvas.height = rect.height;
      const ctx = croppedCanvas.getContext('2d');
      
      // Draw only the selected portion onto the new canvas
      ctx.drawImage(
        canvas, 
        absoluteRect.x, absoluteRect.y, absoluteRect.width, absoluteRect.height,
        0, 0, rect.width, rect.height
      );
      
      // Convert to data URL
      const dataUrl = croppedCanvas.toDataURL('image/png');
      
      // Send back to extension
      chrome.runtime.sendMessage({
        //action: "analyzeImage",
        action: "screenshotSelected",
        image: dataUrl
      });
      
      // Remove status div
      if (statusDiv) statusDiv.remove();
    } catch (error) {
      console.error('Error cropping image:', error);
      
      // Update status
      if (statusDiv) {
        statusDiv.textContent = 'Error capturing screenshot: ' + error.message;
        setTimeout(() => {
          if (statusDiv) statusDiv.remove();
        }, 3000);
      }
    }
  }).catch(error => {
    console.error('html2canvas error:', error);
    
    // Update status
    if (statusDiv) {
      statusDiv.textContent = 'Error capturing screenshot: ' + error.message;
      setTimeout(() => {
        if (statusDiv) statusDiv.remove();
      }, 3000);
    }
  });
}

// Listen for messages from the extension
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === "captureScreenshot") {
    // Start the selection process
    createSelectionInterface();
    sendResponse({success: true});
    return true;
  }
});