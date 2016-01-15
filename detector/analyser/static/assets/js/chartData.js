      $(document).ready(function() {
            $('#dataTables-service').DataTable({
                    responsive: true,
                    searching : false
            });
        });
      $(document).ready(function() {
            $('#dataTables-method').DataTable({
                    responsive: true,
                    searching : false
            });
        });
      $(document).ready(function() {
            $('#dataTables-statistic').DataTable({
                    responsive: true,
                    searching : false
            });
        });

      $(document).ready(function() {
        $(".clickable-row").click(function() {
            window.document.location = $(this).data("href");
        });
      });

      var _labels = [];
      var data_max = [];
      var data_min = [];
      var data_avg = [];

      {%for itm in ret_value.services%}
      _labels.push({{itm.serviceId}});
      data_max.push({{itm.max}});
      data_min.push({{itm.min}});
      data_avg.push({{itm.avg}});
      {%endfor%}

      var ctx = document.getElementById("myBarChart").getContext("2d");
      var data = {
        labels : _labels,
        datasets : [
          {
            fillColor : "rgba(220,220,220,0.5)",
            strokeColor : "rgba(220,220,220,1)",
            data : data_max
          },
          {
            fillColor : "rgba(151,187,205,0.5)",
            strokeColor : "rgba(151,187,205,1)",
            data : data_min
          },
          {
            fillColor : "rgba(99,87,245,0.5)",
            strokeColor : "rgba(99,87,245,1)",
            data : data_avg
          }
        ]
      };
      new Chart(ctx).Bar(data);