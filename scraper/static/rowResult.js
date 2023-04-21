// Get all the keys in localStorage
for (var i = localStorage.length - 1; i >= 0; i--) {
    var shortened_url = localStorage.key(i);
    var data = JSON.parse(localStorage.getItem(shortened_url));

    // Create a row for the item and add it to the table
    var row = document.createElement("tr");
    row.innerHTML = `
        <td style="vertical-align: middle; horizontal-align: middle;"><img src="${data.image}" style="width:50%;" class="figure-img img-fluid rounded clickable" style="object-fit: fill;" data-url="${ shortened_url }" onClick="rowReport(this)"></td>
        <td style="vertical-align: middle;" class="clickable" data-url="${ shortened_url }" onClick="rowReport(this)">${ data.title }</td>
        <td style="vertical-align: middle;" class="clickable" data-url="${ shortened_url }" onClick="rowReport(this)">$${ data.price }</td>
        <td style="vertical-align: middle;" class="clickable" data-url="${ shortened_url }" onClick="rowReport(this)">
            <div class="Stars" style="--rating: ${ data.rating }" aria-label="Rating of this product is ${ data.rating } out of 5."></div>
        </td>
    `;
    document.getElementById("result-table").appendChild(row);
}

function rowReport (select) {
    var url = select.getAttribute("data-url");
    document.getElementById("id_url").value = url;
    document.querySelector("form").submit();
}