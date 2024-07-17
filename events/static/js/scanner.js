var SCAN_MODE = "registration"

// SCANNER
var html5QrcodeScanner = new Html5QrcodeScanner(
    "reader", { fps: 10, qrbox: 250 }
);
html5QrcodeScanner.render(onScanSuccess);

// JavaScript to toggle the label text
const toggleSwitch = document.getElementById('toggleSwitch');
const toggleLabel = document.getElementById('toggleLabel');
toggleSwitch.addEventListener('change', () => {
    if (toggleSwitch.checked) {
        toggleLabel.innerText = 'See Participant';
        SCAN_MODE = "participant";
    } else {
        toggleLabel.innerText = 'Registration';
        SCAN_MODE = "registration";
    }
});

function extractParticipantId(str) {
    const match = str.match(/participant_id:(\d+)/);
    if (match) {
        return parseInt(match[1], 10);
    } else {
        throw new Error("QR code not recognised!");
    }
}

function onScanSuccess(decodedText, decodedResult) {
    var id = -1;

    try {
        id = extractParticipantId(decodedText)
    } catch (error) {
        console.error(error)
        return setStatusToFailed(error.message);
    }

    if (SCAN_MODE == "participant") {
        // redirect user to the admin page of the participant
        window.location.href = `${getBaseUrl()}admin/events/participant/${id}/change/`;
        return;
    }

    fetch('/events/set-attendance/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({ 'participant_id':id })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);

        return data.success ? setStatusToSucces(data.message): setStatusToFailed(data.message);
    })
    .catch((error) => {
        console.error('Error:', error);
        return setStatusToFailed(error.message);
    });
}

function setStatusToSucces(message) {
    console.log('status OK');
    document.getElementById('title').innerText = message;
    setTemporaryBackgroundColor('green', 2);
}

function setStatusToFailed(message) {
    console.log('status BAD');
    document.getElementById('title').innerText = message;
    setTemporaryBackgroundColor('red', 4)
}

function setTemporaryBackgroundColor(color, seconds) {
    // Get the body element
    const body = document.body;
    
    // Store the original background color
    const originalColor = body.style.backgroundColor;
    
    // Set the new background color
    body.style.backgroundColor = color;
    
    // Set a timeout to revert to the original color after the specified time
    setTimeout(() => {
        body.style.backgroundColor = originalColor;
    }, seconds * 1000); // Convert seconds to milliseconds
}

function getBaseUrl() {
    const protocol = window.location.protocol; // "http:" or "https:"
    const hostname = window.location.hostname; // "localhost" or your domain name
    const port = window.location.port; // "8100" or empty if using default ports (80 for HTTP, 443 for HTTPS)

    // Construct the base URL
    let baseUrl = `${protocol}//${hostname}`;
    if (port) {
        baseUrl += `:${port}`;
    }

    return baseUrl + '/';
}