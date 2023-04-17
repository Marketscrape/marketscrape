// Check if localStorage has items
if (localStorage.length > 0) {
    // Show the table if localStorage has items
    document.getElementById('result-table').style.display = 'table';
    document.getElementById('noItemsMsg').style.display = 'none';
} else {
    // Show the "No items!" message if localStorage is empty
    document.getElementById('result-table').style.display = 'none';
    document.getElementById('noItemsMsg').style.display = 'block';
}