// Improved client-side code for the Gemini Image Generator

document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generateBtn');
    const statusMessage = document.getElementById('statusMessage');
    const generatedImage = document.getElementById('generatedImage');
    const promptInput = document.getElementById('promptInput');
    const filenameInput = document.getElementById('filenameInput');

    // Show status message function
    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        
        // Set color based on message type
        if (type === 'error') {
            statusMessage.style.color = 'red';
            statusMessage.style.borderLeftColor = '#e74c3c';
            statusMessage.style.backgroundColor = '#fdedec';
        } else if (type === 'success') {
            statusMessage.style.color = 'green';
            statusMessage.style.borderLeftColor = '#27ae60';
            statusMessage.style.backgroundColor = '#e8f8f5';
        } else if (type === 'loading') {
            statusMessage.style.color = 'orange';
            statusMessage.style.borderLeftColor = '#f39c12';
            statusMessage.style.backgroundColor = '#fef9e7';
        }
    }

    generateBtn.addEventListener('click', async function() {
        const prompt = promptInput.value.trim();
        const filename = filenameInput.value.trim();

        // Basic validation
        if (!prompt) {
            showStatus('Please enter a prompt for the image.', 'error');
            return;
        }

        // Disable button and update status
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
        showStatus('Generating and uploading image...', 'loading');
        
        // Hide previous image while generating
        generatedImage.style.display = 'none';
        generatedImage.src = '';
        generatedImage.alt = 'Generated Image will appear here';

        try {
            // Make the request with proper headers and error handling
            const response = await fetch('/generate_and_upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    prompt: prompt,
                    filename: filename
                })
            });

            // Check if response is JSON before trying to parse it
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Received non-JSON response from server: ' + contentType);
            }

            const data = await response.json();

            if (response.ok) {
                let imageLoaded = false;
                
                // Handle different response formats
                if (data.imageUrl) {
                    // Display image from URL (Firebase storage)
                    generatedImage.onload = function() {
                        // Show the image once it's loaded
                        generatedImage.style.display = 'block';
                        imageLoaded = true;
                    };
                    generatedImage.src = data.imageUrl;
                    generatedImage.alt = 'Generated Image';
                } else if (data.image_data) {
                    // Display image from base64 data
                    generatedImage.onload = function() {
                        // Show the image once it's loaded
                        generatedImage.style.display = 'block';
                        imageLoaded = true;
                    };
                    generatedImage.src = `data:image/png;base64,${data.image_data}`;
                    generatedImage.alt = 'Generated Image';
                } else {
                    generatedImage.alt = 'Generated image data received, but no URL was provided.';
                }
                
                // Set a timeout to ensure the image is displayed even if onload doesn't fire
                setTimeout(() => {
                    if (!imageLoaded) {
                        generatedImage.style.display = 'block';
                    }
                }, 1000);
                
                showStatus(data.message || 'Image generated successfully!', 'success');
                
                // Add Gemini's text response if available
                if (data.text_response) {
                    const textResponse = document.createElement('p');
                    textResponse.textContent = `Gemini says: ${data.text_response}`;
                    textResponse.style.fontStyle = 'italic';
                    textResponse.style.marginTop = '10px';
                    statusMessage.appendChild(textResponse);
                }
            } else {
                showStatus(`Error: ${data.message}`, 'error');
                generatedImage.alt = 'Image generation failed.';
            }
        } catch (error) {
            console.error('Error:', error);
            showStatus(`An error occurred: ${error.message}`, 'error');
            generatedImage.alt = 'An error occurred.';
        } finally {
            // Re-enable the button
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate & Upload Image';
        }
    });
});