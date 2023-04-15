function isValidUrl(url) {
    const regex = new RegExp(/https:\/\/www\.facebook\.com\/marketplace\/item\/[0-9]{15,16}\//g);

    if (regex.test(url)){
        return true;
    }

    return false;
}

document.getElementById('MarketForm').addEventListener('submit', function(event) {
    event.preventDefault();

    var inputUrl = document.getElementById('id_url');
    if (isValidUrl(inputUrl.value)) {
        inputUrl.classList.add('is-valid');
        inputUrl.classList.remove('is-invalid');
        this.submit();
    } else {
        inputUrl.classList.add('is-invalid');
        inputUrl.classList.remove('is-valid');
    }

});