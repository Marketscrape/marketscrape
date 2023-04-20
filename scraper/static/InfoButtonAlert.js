document.getElementById('infoBtn').addEventListener('click', function () {
    // Show the Bootstrap alert
    var alertElement = document.getElementById('infoAlert');
    // Set the display property to 'block' to make the alert visible
    alertElement.style.display = 'block';

    document.getElementById('closeAlertBtn').addEventListener('click', function() {
        alertElement.style.display = 'none';
    });
});