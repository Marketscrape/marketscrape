var resultTable = document.getElementById("result-table");
var emptyMessage = document.getElementById("emptyMessage");
if (resultTable.rows.length === 0) {
    // Show empty message
    emptyMessage.style.display = "block";
} else {
    // Hide empty message
    emptyMessage.style.display = "none";
}