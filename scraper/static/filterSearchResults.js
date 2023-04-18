function filterTable() {
    var input = document.getElementById('searchBar').value.toLowerCase();
    console.log(input);
    var table  = document.getElementById('result-table');
    var rows = table.getElementsByTagName('tr');

    for (var i = 0; i < rows.length; i++) {
        var item = rows[i].getElementsByTagName('td')[1];
        if (item) {
            var itemName = item.textContent || item.innerText;
            itemName = itemName.toLowerCase();

            if (itemName.indexOf(input) > -1) {
                rows[i].style.display = '';
            }  else {
                rows[i].style.display = 'none';
            }
        }
    }
}
