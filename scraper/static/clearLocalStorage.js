document.getElementById('clearResultsBtn').addEventListener('click', function() {
    if (localStorage.length > 0) {
        localStorage.clear();
    }

    // Show the Bootstrap alert
    var alertElement = document.getElementById('myAlert');
    // Set the display property to 'block' to make the alert visible
    alertElement.style.display = 'block';

    document.getElementById('closeAlertBtn').addEventListener('click', function() {
        alertElement.style.display = 'none';
    });
});