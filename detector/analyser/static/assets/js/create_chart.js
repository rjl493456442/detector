function create_chart(chartData, b_parseDate, graph_type, categoryField,html_element,dataDateFormator = "", ){
    var chart;
    var graph;

    AmCharts.ready(function () {
        // SERIAL CHART
        chart = new AmCharts.AmSerialChart();

        chart.dataProvider = chartData;
        chart.marginLeft = 10;
        chart.categoryField = categoryField;
        chart.dataDateFormat = dataDateFormator;

        // listen for "dataUpdated" event (fired when chart is inited) and call zoomChart method when it happens
        //chart.addListener("dataUpdated", zoomChart);

        // AXES
        // category
        var categoryAxis = chart.categoryAxis;
        categoryAxis.parseDates = true; // as our data is date-based, we set parseDates to true
        categoryAxis.minPeriod = "mm"; // our data is yearly, so we set minPeriod to YYYY
        categoryAxis.dashLength = 1;
        categoryAxis.minorGridEnabled = true;
        categoryAxis.minorGridAlpha = 0.1;
        categoryAxis.offset = 0;
        categoryAxis.dateFormats = [
            {period:'fff',format:'JJ:NN:SS'},
            {period:'ss',format:'JJ:NN:SS'},
            {period:'mm',format:'JJ:NN'},
            {period:'hh',format:'JJ:NN'},
            {period:'DD',format:'MMM DD'},
            {period:'WW',format:'MMM DD'},
            {period:'MM',format:'MMM'},
            {period:'YYYY',format:'YYYY'}
        ];
        // value
        var valueAxis = new AmCharts.ValueAxis();
        valueAxis.axisAlpha = 0;
        valueAxis.inside = true;
        valueAxis.dashLength = 1;
        chart.addValueAxis(valueAxis);

        // GRAPH
        graph = new AmCharts.AmGraph();
        graph.type = "smoothedLine"; // this line makes the graph smoothed line.
        graph.lineColor = "#d1655d";
        graph.negativeLineColor = "#637bb6"; // this line makes the graph to change color when it drops below 0
        graph.bullet = "round";
        graph.bulletSize = 8;
        graph.bulletBorderColor = "#FFFFFF";
        graph.bulletBorderAlpha = 1;
        graph.bulletBorderThickness = 2;
        graph.lineThickness = 2;
        graph.valueField = "value";
        graph.balloonText = "[[category]]<br><b><span style='font-size:14px;'>[[value]]</span></b>";
        chart.addGraph(graph);

        // CURSOR
        var chartCursor = new AmCharts.ChartCursor();
        chartCursor.cursorAlpha = 0;
        chartCursor.cursorPosition = "mouse";
        chartCursor.categoryBalloonDateFormat = dataDateFormator;
        chart.addChartCursor(chartCursor);

        // SCROLLBAR
        var chartScrollbar = new AmCharts.ChartScrollbar();
        chart.addChartScrollbar(chartScrollbar);

        chart.creditsPosition = "bottom-right";


        // WRITE
        chart.write(html_element);

    });
}
