function create_circle(path)
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
      .value(function(d) { return d.score; });

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
      return "<strong>method:</strong><span style='color:blue'>" + d.name + "</span>" + "  <strong>score:</strong>" + "<span>" + d.score + "</span>";
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
       /* .call(d3.tip()
                //.attr({class: function(d, i) { return d + ' ' +  i + ' A'; }})
                .style({color: 'blue'})
                //.text(function(d){ return 'value: '+ d.name; })
                .html(function(d) {
                  return "<strong>method:</strong><span style='color:blue'>" + d.name + "</span>" + "  <strong>score:</strong>" + "<span>" + d.score + "</span>";
                })
            )
        */
        //.on('mouseover', function(d, i){ d3.select(this).style({fill: 'skyblue'}); })
        //.on('mouseout', function(d, i){ d3.select(this).style({fill: 'aliceblue'}); });

        //.append("title")
        //.text(function(d) { return d.name; });
        .on("mouseover", tip.show)
        .on('mouseout', tip.hide);
        //.on("mouseover", function(){return tooltip.style("visibility", "visible");})
        //.on("mousemove", function(){return tooltip.style("top", (event.pageY-10)+"px").style("left",(event.pageX+10)+"px");})
        //.on("mouseout", function(){return tooltip.style("visibility", "hidden");});
    
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


