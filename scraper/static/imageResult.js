// Get all the keys in localStorage
for (var i = localStorage.length - 1; i >= 0; i--) {
    var shortened_url = localStorage.key(i);
    var data = JSON.parse(localStorage.getItem(shortened_url));
    // Create a row for the item and add it to the table
    var row = document.createElement("tr");
    row.innerHTML = `
        <td style="vertical-align: middle; horizontal-align: middle;"><img src="${data.image}" style="width:50%;" class="figure-img img-fluid rounded" style="object-fit: fill;" data-url="${ shortened_url }"></td>
        <td style="vertical-align: middle;">${ data.title }</td>
        <td style="vertical-align: middle;">$${ data.price }</td>
        <td style="vertical-align: middle;">${ data.rating }/5.0</td>
    `;
    document.getElementById("result-table").appendChild(row);
}

// Add click event listener to image for report action
var images = document.getElementsByTagName("img");
for (var i = 0; i < images.length; i++) {
    images[i].addEventListener("click", function() {
        var url = this.getAttribute("data-url");
        console.log(url);
        document.getElementById("id_url").value = url;
        document.querySelector("form").submit();
    });
}