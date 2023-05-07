// Get array of all dates
var dates = [];
for (var i = 0; i < localStorage.length; i++) {
    var shortened_url = localStorage.key(i);
    var data = JSON.parse(localStorage.getItem(shortened_url));
    dates.push(data.date);
}

// Sort the dates in descending order
dates.sort(function(a, b) {
    return new Date(b) - new Date(a);
});

// Select the two most recent dates
var mostRecentDates = dates.slice(0, 10);

// Remove any items that are not in the most recent two dates
for (var i = localStorage.length - 1; i >= 0; i--) {
    var shortened_url = localStorage.key(i);
    var data = JSON.parse(localStorage.getItem(shortened_url));
    if (mostRecentDates.indexOf(data.date) === -1) {
        localStorage.removeItem(shortened_url);
    }
}