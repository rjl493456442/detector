function create_circle(path, is_comparison)
{
  var margin = 10,
    r = 750,
    height = 1000,
    width = 980,
    diameter =800;

  var color = d3.scale.linear()
      .domain([-1, 5])
      .range(["hsl(152,80%,80%)", "hsl(228,30%,40%)"])
      .interpolate(d3.interpolateHcl);

  var pack = d3.layout.pack()
      .padding(2)
      .size([r,r])
      .value(function(d) { return d.avg; });

  var svg = d3.select("#circle").append("svg")
      .attr("width", width)
      .attr("height", height)
    .append("g")
      .attr("transform", "translate(" + diameter / 2 + "," + diameter / 2 + ")");

  d3.json(path, function(error, root) {
  if (error) throw error;
    
    var tip = d3.tip()
    .attr('class', 'd3-tip')
    //.attr('style','z-index:1000, text-align:center')
    .style("z-index",10)       
    //.style("top", (d3.event.pageY - 28) + "px");
    //.offset([-10, 0])
    .html(function(d) {
      var status = 0;
      var threshold = 5;
      var icon;
      //alert(d.percentage_delta);
      if (parseFloat(d.percentage_delta) < threshold || parseFloat(d.percentage_delta) > -1 * threshold) 
      {
          status = 1;
      }
      if (parseFloat(d.percentage_delta) > threshold){
          status = 2;
          icon = "<i class = 'pe-7s-up-arrow'></i>";
      }
      if (parseFloat(d.percentage_delta) < -1 * threshold){ 
          status = 3;
          icon = "<i class = 'pe-7s-bottom-arrow'></i>";
      }
      if (is_comparison){
        var method_name_str = "<strong style = 'color:white'>method: </strong><span style='color:red'>" + d.name + "</span>";
        var avg_delta_str;
        var percentage_delta_str;
        if (status == 1)
        {
          // in threshold
          avg_delta_str = "<br/><strong style = 'color:white'>Average Execute Time: </strong><span style = 'color:blue'>" + d.avg_delta + "(ms)</span>";
          percentage_delta_str = "<br/><strong style = 'color:white'>Percentage: </strong><span style = 'color:blue'>" + d.percentage_delta + "%</span>";

        }else if (status == 2)
        {
          // larger
          avg_delta_str = "<br/><strong style = 'color:white'>Average Execute Time: </strong><span style = 'color:red'>" + icon + d.avg_delta + "(ms)</span>";
          percentage_delta_str = "<br/><strong style = 'color:white'>Percentage: </strong><span style = 'color:red'>" + icon + d.percentage_delta + "%</span>";

        }else if (status == 3)
        {
          // smaller
          avg_delta_str = "<br/><strong style = 'color:white'>Average Execute Time: </strong><span style = 'color:green'>" + icon + d.avg_delta + "(ms)</span>";
          percentage_delta_str = "<br/><strong style = 'color:white'>Percentage: </strong><span style = 'color:green'>" + icon + d.percentage_delta + "%</span>";
        }
        return method_name_str + avg_delta_str + percentage_delta_str;
        
        //+ "<br/><strong style = 'color:white'>Score: </strong><span style = 'color:red'>" + d.score + "</span>"
        //+ "<br/><strong style = 'color:white'>Invoke Count: </strong><span style = 'color:red'>" + d.count + "</span>";
      }
      else
      {
        return "<strong>method: </strong><span style='color:red'>" + d.name 
        + "<br/><strong style = 'color:white'>Average Execute Time: </strong><span>" + d.avg 
        + "(ms)</span>" + "<br><strong style = 'color:white'>Percentage: <strong><span style = 'color:red'>" + d.percentage + "%</span>"
        + "<br><strong style = 'color:white'>Score: <strong><span style = 'color:red'>" + d.score + "</span>"
        + "<br><strong style = 'color:white'>Invoke Count: <strong><span style = 'color:red'>" + d.count + "</span>";
      }
    });
    svg.call(tip);
   
    var tooltip = d3.select("body")
      .append("div")
      .style("position", "absolute")
      .style("z-index", "10")
      .style("visibility", "hidden")
      .text(function(d){
          return "<strong>method:</strong><span style='color:blue'>"  + "</span>" + "  <strong>score:</strong>" + "<span>"  + "</span>";
      });

    var focus = root,
        nodes = pack.nodes(root),
        view;
  
    var circle = svg.selectAll("svg")
        .data(nodes)
      .enter().append("circle")
        .attr("class", function(d) { return d.parent ? d.children ? "node": "node--leaf" : "node--root"; })
        .style("fill", function(d) { return d.children ? color(d.depth) : null; })
        .on("click", function(d) { if (focus !== d) zoom(d), d3.event.stopPropagation(); })
        .on("mouseover", tip.show)
        .on('mouseout', tip.hide);

    var text = svg.selectAll("svg circle")
        .data(nodes)
      .enter().append("text")
        .attr("class", "label")
        .style("fill-opacity", function(d) { return d.parent === root ? 1 : 0; })
        .style("display", function(d) { return d.parent === root ? "inline" : "none"; });

    var node = svg.selectAll("circle,text");

    d3.select("circle")
        .style("background", color(-1))
        .on("click", function() { zoom(root); });

    zoomTo([root.x, root.y, root.r * 2 + margin]);

    
    
    function zoom(d) {
      var focus0 = focus; focus = d;

      var transition = d3.transition()
        .duration(d3.event.altKey ? 7500 : 750)
        .tween("zoom", function(d) {
          var i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2 + margin]);
          return function(t) { zoomTo(i(t)); };
        });

      transition.selectAll("text")
      .filter(function(d) { return d.parent === focus || this.style.display === "inline"; })
        .style("fill-opacity", function(d) { return d.parent === focus ? 1 : 0; })
        .each("start", function(d) { if (d.parent === focus) this.style.display = "inline"; })
        .each("end", function(d) { if (d.parent !== focus) this.style.display = "none"; });
    }

    function zoomTo(v) {
      var k = diameter / v[2]; view = v;
      node.attr("transform", function(d) { return "translate(" + (d.x - v[0]) * k + "," + (d.y - v[1]) * k + ")"; });
      circle.attr("r", function(d) { return d.r * k; });
    }
  });
  d3.select(self.frameElement).style("height", diameter + "px");
}


