document.getElementById('generateBtn').addEventListener('click', async () => {
    const generateBtn = document.getElementById('generateBtn');
    const statusMessage = document.getElementById('statusMessage');
    const generatedImage = document.getElementById('generatedImage');
    const promptInput = document.getElementById('promptInput'); // Get prompt input
    const filenameInput = document.getElementById('filenameInput'); // Get filename input

    const prompt = promptInput.value.trim(); // Get and trim prompt value
    const filename = filenameInput.value.trim(); // Get and trim filename value

    // Basic validation
    if (!prompt) {
        statusMessage.textContent = 'Please enter a prompt for the image.';
        statusMessage.style.color = 'red';
        return; // Stop the function
    }

    // Disable button and update status
    generateBtn.disabled = true;
    statusMessage.textContent = 'Generating and uploading image...';
    statusMessage.style.color = 'orange';
    generatedImage.src = ''; // Clear previous image
    generatedImage.alt = 'Generated Image will appear here'; // Reset alt text

    try {
        // Make a POST request with the prompt and filename in the body
        const response = await fetch('/generate_and_upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            // Send the prompt and filename as JSON in the request body
            body: JSON.stringify({
                prompt: prompt,
                filename: filename
            })
        });

        const data = await response.json();

        if (response.ok) { // Check if the HTTP status code is in the 200s
            statusMessage.textContent = data.message;
            statusMessage.style.color = 'green';
            if (data.imageUrl) {
                generatedImage.src = data.imageUrl;
                generatedImage.alt = 'Generated Image';
            } else {
                 generatedImage.alt = 'Generated image data received, but no URL was provided.';
            }
        } else {
            // Handle errors returned from the backend (status codes like 400, 500)
            statusMessage.textContent = `Error: ${data.message}`;
            statusMessage.style.color = 'red';
            generatedImage.alt = 'Image generation failed.';
        }

    } catch (error) {
        // Handle network errors or unexpected issues
        statusMessage.textContent = `An error occurred: ${error}`;
        statusMessage.style.color = 'red';
        generatedImage.alt = 'An error occurred.';
        console.error('Fetch error:', error);
    } finally {
        // Re-enable the button
        generateBtn.disabled = false;
    }
});