const defaultAmountOfYearsLoaded = 5; 

$(document).ready(function () {


    // we have to switch these 2 elements to ensure correct positioning
    let div1 = $('#content-related');
	let div2 = $('#swapper');
	
	let tdiv1 = div1.clone();
	let tdiv2 = div2.clone();
	
	if(!div2.is(':empty')){
		div1.replaceWith(tdiv2);
		div2.replaceWith(tdiv1);	  
	}

    // create charts
    let donationsCtx = document.getElementById("donationsChart").getContext("2d");
    var donationsChart = new Chart(donationsCtx, {
    type: "bar",
    options: {
        responsive: true,
        plugins: {
        legend: {
            position: 'top',
        },
        title: {
            display: true,
            text: 'Yearly Donations'
        }
        }
    }
    });

    let moneyRatieCtx = document.getElementById("moneyRatioChart").getContext("2d");
    var moneyRatioChart = new Chart(moneyRatieCtx, {
    type: "pie",
    options: {
        responsive: true,
        plugins: {
        legend: {
            position: 'top',
        },
        title: {
            display: true,
            text: 'Donations vs. Adoption Parents (€)'
        }
        }
    }
    });

    $('#multiYearSelect').select2({
        placeholder: 'Choose years',
        allowClear: false,
    });

    $('#singleYearSelect').select2({
        placeholder: 'Choose year',
        allowClear: false,
    });

    $.ajax({
        url: "/stats/chart/filter-options/",
        type: "GET",
        dataType: "json",
        success: (jsonResponse) => {

            // Load all the options
            jsonResponse.options.forEach(option => {
                $("#multiYearSelect").append(new Option(option, option));
                $("#singleYearSelect").append(new Option(option, option));
            });

            $('#multiYearSelect').trigger('change');
            $('#singleYearSelect').trigger('change');

            // Load data for latest 5 years
            loadAllMultiYearCharts(jsonResponse.options.slice(0, defaultAmountOfYearsLoaded));
            // Load data for latest year
            loadAllSingleYearCharts(jsonResponse.options[0]);

        },
        error: () => console.log("Failed to fetch chart filter options!")
    });

    $("#multiYearFilterForm").on("submit", (event) => {
        event.preventDefault();
        
        const years = $("#multiYearSelect").val();
        loadAllMultiYearCharts(years)
    });
    
    $("#singleYearFilterForm").on("submit", (event) => {
        event.preventDefault();
    
        const year = $("#singleYearSelect").val();
        loadAllSingleYearCharts(year)
    });
    
    function loadChart(chart, endpoint, isMultiYear) {
        $.ajax({
            url: endpoint,
            type: "GET",
            dataType: "json",
            success: (jsonResponse) => {      
    
                // Extract data from the response
                const labels = jsonResponse.data.labels;
                const datasets = jsonResponse.data.datasets;
    
                if (isMultiYear) {
                    // update the yearpicker
                    labels.forEach((label, index) => {
                        if (index < defaultAmountOfYearsLoaded) {
                            $('#multiYearSelect option[value="' + label + '"]').prop('selected', true);
                        }
                    })
                    $('#multiYearSelect').trigger('change');
    
                } else {
                    $('#singleYearSelect option[value="' + labels[0] + '"]').prop('selected', true);
                    $('#singleYearSelect').trigger('change');
                }
    
                // Reset the current charts
                chart.data.datasets = [];
                chart.data.labels = [];
    
                // Load new data into the chart
                chart.data.labels = labels;
                datasets.forEach(dataset => {
                    chart.data.datasets.push(dataset);
                });
                chart.update();
            },
            error: () => console.log("Failed to fetch chart data from " + endpoint)
        });
    }
      
    function loadAllMultiYearCharts(years) {
        loadChart(donationsChart, `/stats/chart/donations-per-year${createYearQueryString(years)}/`, true);
    }
      
    function loadAllSingleYearCharts(year) {
        loadChart(moneyRatioChart, `/stats/chart/money-ratio${createYearQueryString([year])}/`, false)
    }

});

function createYearQueryString(years) {
    if (!Array.isArray(years) || years.length === 0) {
        return '';
    }

    const queryString = years.map(year => `years=${year}`).join('&');
    return `?${queryString}`;
}
