document.addEventListener("DOMContentLoaded", function () {
    var chart = document.getElementById('render-wordcloud');
    var chartContent = chart.getAttribute('data-chart');
    var chartObject = JSON.parse(chartContent);
    Plotly.newPlot(chart, chartObject);
});
