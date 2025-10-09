document.addEventListener("DOMContentLoaded", function() {

    // ===============================
    // 📊 GRAFICO REGISTRAZIONI UTENTI
    // ===============================
    const regOptions = {
        chart: {
            type: 'area',
            height: 350,
            toolbar: { show: false }
        },
        series: [{
            name: 'Nuovi Utenti',
            data: chartData.data
        }],
        xaxis: {
            categories: chartData.labels,
            labels: { rotate: -45 }
        },
        colors: ['#1E3A8A'],
        fill: {
            type: 'gradient',
            gradient: {
                shadeIntensity: 1,
                opacityFrom: 0.4,
                opacityTo: 0.1,
                stops: [0, 90, 100]
            }
        },
        stroke: { curve: 'smooth', width: 3 },
        tooltip: {
            theme: 'dark',
            y: { formatter: val => `${val} iscrizioni` }
        }
    };

    new ApexCharts(document.querySelector("#registrationsChart"), regOptions).render();


    // ===============================
    // 📈 GRAFICO NUOVI ABBONAMENTI
    // ===============================
    const subChart = new ApexCharts(document.querySelector("#subscriptions-chart"), {
        chart: {
            type: "line",
            height: 350
        },
        series: [{
            name: "Nuovi abbonamenti",
            data: []
        }],
        xaxis: { categories: [] },
        colors: ['#007bff'],
        stroke: { curve: 'smooth', width: 3 },
        markers: { size: 5 },
        title: {
            text: "Andamento nuovi abbonamenti",
            align: "center"
        }
    });
    subChart.render();

    // 🔹 Funzione AJAX per caricare dati abbonamenti
    async function loadSubscriptionData(start_date = "", end_date = "") {
        const url = `/subscription-data/?start_date=${start_date}&end_date=${end_date}`;
        const response = await fetch(url);
        const result = await response.json();

        subChart.updateOptions({ xaxis: { categories: result.labels } });
        subChart.updateSeries([{ name: "Nuovi abbonamenti", data: result.data }]);
    }

    // Carica dati iniziali
    loadSubscriptionData();

    // 🔹 Filtro manuale per abbonamenti
    document.querySelector("#filterBtn").addEventListener("click", function () {
        const start = document.querySelector("#start_date").value;
        const end = document.querySelector("#end_date").value;
        loadSubscriptionData(start, end);
    });


    // ===============================
    // 🥧 GRAFICO ISCRIZIONI PER CATEGORIA
    // ===============================
    const catChart = new ApexCharts(document.querySelector("#categoryChart"), {
        chart: {
            type: 'donut',
            height: 350
        },
        labels: chartData.cat_labels,
        series: chartData.cat_data,
        colors: ['#007bff', '#28a745', '#ffc107'],
        legend: { position: 'bottom' }
    });
    catChart.render();

    // 🔹 Flatpickr per intervallo date (categoria)
    const datePicker = flatpickr("#date_range_categoria", {
        mode: "range",
        dateFormat: "Y-m-d",
        locale: "it",
        altInput: true,
        altFormat: "d/m/Y"
    });

    // 🔹 Funzione AJAX per categorie
    async function loadCategoryData(start_date = "", end_date = "") {
        const url = `/subscriptions-category-data/?start_date=${start_date}&end_date=${end_date}`;
        const response = await fetch(url);
        const result = await response.json();

        catChart.updateOptions({
            labels: result.labels
        });
        catChart.updateSeries(result.data);
    }

    // 🔹 Filtro per categoria
    document.querySelector("#filterBtn_categoria").addEventListener("click", function () {
        const range = document.querySelector("#date_range_categoria").value;
        if (!range) {
            loadCategoryData();
            return;
        }

        // Flatpickr restituisce le date separate da " al " o " to "
        const [start, end] = range.split(" a ");
        loadCategoryData(start, end || start);
    });

});
