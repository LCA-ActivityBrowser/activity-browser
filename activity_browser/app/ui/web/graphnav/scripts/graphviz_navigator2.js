

var jsondata = '{"nodes": [{"id": "eb3b15cfce031f9f7494882cccaa04bf", "product": "1,1-dimethylcyclopentane", "name": "market for 1,1-dimethylcyclopentane", "location": "GLO"}, {"id": "304d42eabdcfe000e76034a265f7aa6a", "product": "solvent, organic", "name": "1,1-dimethylcyclopentane to generic market for solvent, organic", "location": "GLO"}], "edges": [{"source": "eb3b15cfce031f9f7494882cccaa04bf", "target": "304d42eabdcfe000e76034a265f7aa6a", "label": "1,1-dimethylcyclopentane"}]}'
console.log ("Hello World");

var heading = document.getElementById("heading");
// document.getElementById("data").innerHTML = "no data yet";

// SETUP GRAPH
// https://github.com/dagrejs/graphlib/wiki/API-Reference
// HOW TO SET EDGES AND NODES MANUALLY USING GRAPHLIB:
// digraph.setNode("kspacey",    { label: "Kevin Spacey",  width: 144, height: 100 });
// digraph.setEdge("kspacey",   "swilliams");
// var graph = new dagre.graphlib.Graph({ multigraph: true });

// Set an object for the graph label
// graph.setGraph({});


// Create and configure the renderer
// var render = dagreD3.render();


function windowSize() {
    w = window,
    d = document,
    e = d.documentElement,
    g = d.getElementsByTagName('body')[0],
    x = w.innerWidth || e.clientWidth || g.clientWidth;
    y = w.innerHeight|| e.clientHeight|| g.clientHeight;
    return [x,y];
};

/**
 * Build svg container and listen for zoom and drag calls
 */

var svg = d3.select("body")
 .append("svg")
 .attr("viewBox", "0 0 600 400")
 .attr("height", "100%")
 .attr("width", "100%")
 .call(d3.zoom().on("zoom", function () {
    svg.attr("transform", d3.event.transform)
 }))
 .append("g")

var render = dagreD3.render();

function update_graph(json_data) {
    console.log("Updating Graph")
	data = JSON.parse(json_data)

	heading.innerHTML = data.title;

	// reset graph
	var graph = new dagre.graphlib.Graph({ multigraph: true });
	graph.setGraph({});

	  // nodes --> graph
	  data.nodes.forEach(function(n) {

	    graph.setNode(n['id'], {
	      label: chunkString(n['name'], 40),
	      product: n['product'],
	      location: n['location'],
	      id: n['id'],
	      database: n['db'],
	    });
	  });

    console.log("Nodes successfully loaded...");

	  // edges --> graph
	  data.edges.forEach(function(e) {
	  	// document.writeln(e['source']);
	    graph.setEdge(e['source_id'], e['target_id'], {label: chunkString(e['label'], 40)
	    });
	  });

    console.log("Edges successfully loaded...")
	  // Render the graph into svg g
	  svg.call(render, graph);


	  // Adds click listener, calling handleMouseClick func
	  var nodes = svg.selectAll("g .node")
	      .on("click", handleMouseClick)
	      console.log ("click!");

	// Function called on click

	function handleMouseClick(node){
        //launch downstream exploration on shift+clicked node
		if (window.event.shiftKey){
            console.log ('shift')

            new QWebChannel(qt.webChannelTransport, function (channel) {
                window.bridge = channel.objects.bridge;
                window.bridge.node_clicked_expand(
                  graph.node(node).database + ";" + graph.node(node).id
                );
                window.bridge.graph_ready.connect(update_graph);
            });


        //launch reduction on alt+clicked node
		} else if (window.event.altKey){
            console.log ('alt')

            new QWebChannel(qt.webChannelTransport, function (channel) {
                window.bridge = channel.objects.bridge;
                window.bridge.node_clicked_reduce(
                  graph.node(node).database + ";" + graph.node(node).id
                );
                window.bridge.graph_ready.connect(update_graph);
            });


        //launch navigation from clicked node
		} else  {
            console.log ('no additional key')
            new QWebChannel(qt.webChannelTransport, function (channel) {
                window.bridge = channel.objects.bridge;
                window.bridge.node_clicked(
                  graph.node(node).database + ";" + graph.node(node).id
                );
            window.bridge.graph_ready.connect(update_graph);
            });
	}

};
};


// break strings into multiple lines after certain length if necessary
function chunkString(str, length) {
    return str.match(new RegExp('.{1,' + length + '}', 'g')).join("\n");
}


new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.bridge;
    window.bridge.graph_ready.connect(update_graph);
});

