function create_tree(path, is_comparison)
{

	var margin_tree = {top: 30, right: 20, bottom: 30, left: 20},
        width_tree = 1080 - margin_tree.left - margin_tree.right,
        barHeight_tree = 22,
        barWidth_tree = width_tree * .8;

    var i = 0,
        duration_tree = 400,
        root_tree;

    var tree = d3.layout.tree()
        .nodeSize([0, 20]);

    var diagonal_tree = d3.svg.diagonal()
        .projection(function(d) { return [d.y, d.x]; });

    var svg_tree = d3.select("#tree_diagram").append("svg")
        .attr("width", width_tree + margin_tree.left + margin_tree.right)
        .attr("height", 1200)
      .append("g")
        .attr("transform", "translate(" + margin_tree.left + "," + margin_tree.top + ")");

    d3.json(path, function(error, flare) {
      if (error) throw error;
      flare.x0 = 0;
      flare.y0 = 0;
      update(root_tree = flare);
    });

    function update(source) {

      // Compute the flattened node list. TODO use d3.layout.hierarchy.
      var nodes_tree = tree.nodes(root_tree);

      var height_t = Math.max(500, nodes_tree.length * barHeight_tree + margin_tree.top + margin_tree.bottom);

      d3.select("svg").transition()
          .duration(duration_tree)
          .attr("height", height_t);

      d3.select(self.frameElement).transition()
          .duration(duration_tree)
          .style("height", height_t + "px");

      // Compute the "layout".
      nodes_tree.forEach(function(n, i) {
        n.x = i * barHeight_tree;
      });

      // Update the nodes…
      var node_tree = svg_tree.selectAll("g.node")
          .data(nodes_tree, function(d) { return d.id || (d.id = ++i); });

      var nodeEnter_tree = node_tree.enter().append("g")
          .attr("class", "node")
          .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; })
          .style("opacity", 1e-6);

      // Enter any new nodes at the parent's previous position.
      nodeEnter_tree.append("rect")
          .attr("y", -barHeight_tree / 2)
          .attr("height", barHeight_tree)
          .attr("width", barWidth_tree)
          .style("fill", color_func)
          .on("click", click_func);

      nodeEnter_tree.append("text")
          .attr("dy", 3.5)
          .attr("dx", 5.5)
          .html(function(d,i) {
          	// shorten method name
          	var name_list = d.name.split(".");
          	name_list[1] = "*";
          	name_list[2] = "*";
          	name_list[3] = "*";
          	name_list[4] = "*";
            var method_name = d.name.split("-")[1] == null ? " " : d.name.split("-")[1];
            var class_name = d.name.split("-")[0];
          	var name_new = name_list.join(".");
            if (is_comparison)
            {
              return d.percentage_delta  + "%  " + method_name + " · " + d.avg_delta + "ms" + " · " + class_name ;
            }
            else
            {
              return d.percentage + "%  " + name_new + "·" + d.avg + "ms" + " Invoke Count:" + d.count;
            }
           });

      // Transition nodes to their new position.
      nodeEnter_tree.transition()
          .duration(duration_tree)
          .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })
          .style("opacity", 1);

      node_tree.transition()
          .duration(duration_tree)
          .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })
          .style("opacity", 1)
        .select("rect")
          .style("fill", color_func);

      // Transition exiting nodes to the parent's new position.
      node_tree.exit().transition()
          .duration(duration_tree)
          .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
          .style("opacity", 1e-6)
          .remove();

      // Update the links…
      var link_tree = svg_tree.selectAll("path.link")
          .data(tree.links(nodes_tree), function(d) { return d.target.id; });

      // Enter any new links at the parent's previous position.
      link_tree.enter().insert("path", "g")
          .attr("class", "link")
          .attr("d", function(d) {
            var o = {x: source.x0, y: source.y0};
            return diagonal_tree({source: o, target: o});
          })
        .transition()
          .duration(duration_tree)
          .attr("d", diagonal_tree);

      // Transition links to their new position.
      link_tree.transition()
          .duration(duration_tree)
          .attr("d", diagonal_tree);

      // Transition exiting nodes to the parent's new position.
      link_tree.exit().transition()
          .duration(duration_tree)
          .attr("d", function(d) {
            var o = {x: source.x, y: source.y};
            return diagonal_tree({source: o, target: o});
          })
          .remove();

      // Stash the old positions for transition.
      nodes_tree.forEach(function(d) {
        d.x0 = d.x;
        d.y0 = d.y;
      });
    }

    // Toggle children on click.
    function click_func(d) {
      if (d.children) {
        d._children = d.children;
        d.children = null;
      } else {
        d.children = d._children;
        d._children = null;
      }
      update(d);
    }

    function color_func(d) {
      return d._children ? "#9ea480" : d.children ? "#9ea480" : "#e3e8cb";
    }
	
}
