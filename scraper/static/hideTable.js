document.addEventListener('DOMContentLoaded', function() {
    // Hide the table header, search bar, and clear button if there are no search results
    let resultTable = document.getElementById('result-table');
    if (resultTable.innerHTML.trim() === '') {
        document.getElementById('table-header').style.display = 'none';
        document.getElementById('searchBar').style.display = 'none';
        document.getElementById('clearResultsBtn').style.display = 'none';
        document.getElementById('emptyMessage').style.display = 'block';
    }
});