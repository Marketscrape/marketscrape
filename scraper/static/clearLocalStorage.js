document.getElementById('clearResultsBtn').addEventListener('click', function() {
    if (localStorage.length > 0) {
        localStorage.clear();
    }
});