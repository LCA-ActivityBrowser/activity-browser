console.log ("Starting "+(is_sankey_mode ? "Sankey" : "Navigator"));

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


function getWindowSize() {
    w = window,
    d = document,
    e = d.documentElement,
    g = d.getElementsByTagName('body')[0],
    x = w.innerWidth ; //|| e.clientWidth || g.clientWidth;
    y = w.innerHeight ; //|| e.clientHeight || g.clientHeight;

    //preventing the svg canvas to be 0x0, as page is loaded in the background with dimensions 0x0
    if (x,y == 0) {
        x = 600;
        y = 500;
    };

    globalWidth = x;
    globalHeight = y;
    return {x,y};
};

var max_string_length = 20;
var max_edge_width = 40;

var globalWidth = null;
var globalHeight = null;

// initialize panCanvas (container actually displaying graph) globally, to enable node-info extraction on-click
var panCanvas = {};

/*
BEGIN OF ADAPTED DEMO CODE FROM BILL WHITE D3 PAN AND ZOOM DEMOS
http://www.billdwhite.com/wordpress/2017/09/
http://www.billdwhite.com/wordpress/2014/02/03/d3-pan-and-zoom-reuse-demo/
http://www.billdwhite.com/wordpress/2013/12/02/d3-force-layout-with-pan-and-zoom-minimap/
*/


d3.demo = {};

/** CANVAS **/
// function object for the canvas
d3.demo.canvas = function() {

    getWindowSize();

    "use strict";
    console.log("w: "+globalWidth+ " ; h: "+globalHeight)
    var width           = globalWidth*(is_sankey_mode?0.9:1.0),
        height          = globalHeight*0.6,
        base            = null,
        wrapperBorder   = 0,
        minimap         = null,
        minimapPadding  = 10,
        minimapScale    = 0.1; //reduced minimap scale to (help) prevent graph to exceed panel size

    //introduced function to reset width/height according to new window sizes
    updateDimensions = function() {
        getWindowSize();
        width           = globalWidth*0.99;
        height          = globalHeight*(is_sankey_mode?0.6:0.65);
    }


    function canvas(selection) {

        base = selection;
        //changed location of MiniMap to under the graph for better layout with very wide graphs
        var svgWidth = (width  + (wrapperBorder*2) + minimapPadding*2);
        var svgHeight = (height + (wrapperBorder*2) + minimapPadding*2 + (height*minimapScale));
        var svg = selection.append("svg")
            .attr("class", "svg canvas")
            .attr("width", svgWidth)
            .attr("height", svgHeight)
            .attr("shape-rendering", "auto");

        var svgDefs = svg.append("defs");
        svgDefs.append("clipPath")
            .attr("id", "wrapperClipPath_qwpyza")
            .attr("class", "wrapper clipPath")
            .append("rect")
            .attr("class", "background")
            .attr("width", width)
            .attr("height", height);
        svgDefs.append("clipPath")
            .attr("id", "minimapClipPath_qwpyza")
            .attr("class", "minimap clipPath")
            .attr("width", width)
            .attr("height", height)
            .append("rect")
            .attr("class", "background")
            .attr("width", width)
            .attr("height", height);

        var filter = svgDefs.append("svg:filter")  // frame of the mini-map
            .attr("id", "minimapDropShadow_qwpyza")
            .attr("x", "-20%")
            .attr("y", "-20%")
            .attr("width", "150%")
            .attr("height", "150%");
        filter.append("svg:feOffset")
            .attr("result", "offOut")
            .attr("in", "SourceGraphic")
            .attr("dx", "1")
            .attr("dy", "1");
        filter.append("svg:feColorMatrix")
            .attr("result", "matrixOut")
            .attr("in", "offOut")
            .attr("type", "matrix")
            .attr("values", "0.1 0 0 0 0 0 0.1 0 0 0 0 0 0.1 0 0 0 0 0 0.5 0");
        filter.append("svg:feGaussianBlur")
            .attr("result", "blurOut")
            .attr("in", "matrixOut")
            .attr("stdDeviation", "10");
        filter.append("svg:feBlend")
            .attr("in", "SourceGraphic")
            .attr("in2", "blurOut")
            .attr("mode", "normal");

        var minimapRadialFill = svgDefs.append("radialGradient")
            .attr('id', "minimapGradient")
            .attr('gradientUnits', "userSpaceOnUse")
            .attr('cx', "500")
            .attr('cy', "500")
            .attr('r', "400")
            .attr('fx', "500")
            .attr('fy', "500");
        minimapRadialFill.append("stop")
            .attr("offset", "0%")
            .attr("stop-color", "#FFFFFF");
        minimapRadialFill.append("stop")
            .attr("offset", "40%")
            .attr("stop-color", "#EEEEEE")
        minimapRadialFill.append("stop")
            .attr("offset", "100%")
            .attr("stop-color", "#E0E0E0");

        var outerWrapper = svg.append("g")
            .attr("class", "wrapper outer")
            .attr("transform", "translate(0, " + minimapPadding + ")");
        outerWrapper.append("rect")
            .attr("class", "background")
            .attr("width", width + wrapperBorder*2)
            .attr("height", height + wrapperBorder*2);

        var innerWrapper = outerWrapper.append("g")
            .attr("class", "wrapper inner")
            .attr("clip-path", "url(#wrapperClipPath_qwpyza)")
            .attr("transform", "translate(" + (wrapperBorder) + "," + (wrapperBorder) + ")");

        innerWrapper.append("rect")
            .attr("class", "background")
            .attr("width", width)
            .attr("height", height);

        panCanvas = innerWrapper.append("g")
            .attr("class", "panCanvas")
            .attr("width", width)
            .attr("height", height)
            .attr("transform", "translate(0,0)");

        panCanvas.append("rect")
            .attr("class", "background")
            .attr("width", width)
            .attr("height", height);

        var zoom = d3.zoom()
            .scaleExtent([0.25, 5]);

        // updates the zoom boundaries based on the current size and scale
        var updateCanvasZoomExtents = function() {
            var scale = innerWrapper.property("__zoom").k;
            var targetWidth = svgWidth;
            var targetHeight = svgHeight;
            var viewportWidth = width;
            var viewportHeight = height;
            //DISABLED LIMITED TRANSLATION BC OF FAULTY ZOOM BEHAVIOR
            // # TODO : Find useful way of limiting translation to boundaries of own container
            //zoom.translateExtent([
            //    [-viewportWidth/scale, -viewportHeight/scale],
            //    [(viewportWidth/scale + targetWidth), (viewportHeight/scale + targetHeight)]
            //]);
        };

        var zoomHandler = function() {
            panCanvas.attr("transform", d3.event.transform);
            // here we filter out the emitting of events that originated outside of the normal ZoomBehavior; this prevents an infinite loop
            // between the host and the minimap
            if (d3.event.sourceEvent instanceof MouseEvent || d3.event.sourceEvent instanceof WheelEvent) {
                minimap.update(d3.event.transform);
            }
            updateCanvasZoomExtents();
        };

        zoom.on("zoom", zoomHandler);

        innerWrapper.call(zoom);

        // initialize the minimap, passing needed references
        //changed location of MiniMap to under the graph for better layout with very wide graphs
        minimap = d3.demo.minimap()
            .host(canvas)
            .target(panCanvas)
            .minimapScale(minimapScale)
            .x(minimapPadding)
            .y(height + 2*minimapPadding);

        svg.call(minimap);

        /** ADD SHAPE **/
        // function to update dimensions, reset the canvas (with new dimensions), render the graph in canvas & minimap
        canvas.addItem = function() {
            //canvas.render();
            updateDimensions();
            canvas.reset();
            panCanvas.call(render,graph);
            // get panCanvas width here?
            // pan to node (implement here)
            minimap.render();
        };

        /** RENDER **/
        canvas.render = function() {
        updateDimensions(); //added call to update window sizes
            svgDefs
                .select(".clipPath .background")
                .attr("width", width)
                .attr("height", height);
            //changed location of MiniMap to under the graph for better layout with very wide graphs
            svg
                .attr("width",  width  + (wrapperBorder*2) )
                .attr("height", height + (wrapperBorder*2) + minimapPadding*2 + (width*minimapScale));

            outerWrapper
                .select(".background")
                .attr("width", width + wrapperBorder*2)
                .attr("height", height + wrapperBorder*2);

            innerWrapper
                .attr("transform", "translate(" + (wrapperBorder) + "," + (wrapperBorder) + ")")
                .select(".background")
                .attr("width", width)
                .attr("height", height);

            panCanvas
                .attr("width", width)
                .attr("height", height)
                .select(".background")
                .attr("width", width)
                .attr("height", height);

            minimap
                .x(minimapPadding)
                .y(height + 2*minimapPadding)
                .render();
        };

        canvas.reset = function() {

            //svg.call(zoom.event);
            //svg.transition().duration(750).call(zoom.event);
            zoom.transform(panCanvas, d3.zoomIdentity);
            svg.property("__zoom", d3.zoomIdentity);
            minimap.update(d3.zoomIdentity);
        };

        canvas.update = function(minimapZoomTransform) {
            zoom.transform(panCanvas, minimapZoomTransform);
            // update the '__zoom' property with the new transform on the rootGroup which is where the zoomBehavior stores it since it was the
            // call target during initialization
            innerWrapper.property("__zoom", minimapZoomTransform);

            updateCanvasZoomExtents();
        };

        updateCanvasZoomExtents();
    }


    //============================================================
    // Accessors
    //============================================================

    canvas.width = function(value) {
        if (!arguments.length) return width;
        width = parseInt(value, 10);
        return this;
    };

    canvas.height = function(value) {
        if (!arguments.length) return height;
        height = parseInt(value, 10);
        return this;
    };

    return canvas;
};



/** MINIMAP **/
d3.demo.minimap = function() {

    "use strict";

    var minimapScale    = 0.1,
        host            = null,
        base            = null,
        target          = null,
        width           = 0,
        height          = 0,
        x               = 0,
        y               = 0;

    function minimap(selection) {

        base = selection;

        var zoom = d3.zoom()
            .scaleExtent([0.25, 5]);

        // updates the zoom boundaries based on the current size and scale
        var updateMinimapZoomExtents = function() {
            var scale = container.property("__zoom").k;
            var targetWidth = parseInt(target.attr("width"));
            var targetHeight = parseInt(target.attr("height"));
            var viewportWidth = host.width();
            var viewportHeight = host.height();
            //DISABLED LIMITED TRANSLATION BC OF FAULTY ZOOM BEHAVIOR
            // # TODO : Find useful way of limiting translation to boundaries of own container
            //zoom.translateExtent([
            //    [-viewportWidth/scale, -viewportHeight/scale],
            //   [(viewportWidth/scale + targetWidth), (viewportHeight/scale + targetHeight)]
            //]);
        };

        var zoomHandler = function() {
            frame.attr("transform", d3.event.transform);
            // here we filter out the emitting of events that originated outside of the normal ZoomBehavior; this prevents an infinite loop
            // between the host and the minimap
            if (d3.event.sourceEvent instanceof MouseEvent || d3.event.sourceEvent instanceof WheelEvent) {
                // invert the outgoing transform and apply it to the host
                var transform = d3.event.transform;
                // ordering matters here! you have to scale() before you translate()
                var modifiedTransform = d3.zoomIdentity.scale(1/transform.k).translate(-transform.x, -transform.y);
                host.update(modifiedTransform);
            }

            updateMinimapZoomExtents();
        };

        zoom.on("zoom", zoomHandler);

        var container = selection.append("g")
            .attr("class", "minimap");

        container.call(zoom);

        minimap.node = container.node();

        var frame = container.append("g")
            .attr("class", "frame")

        frame.append("rect")
            .attr("class", "background")
            .attr("width", width)
            .attr("height", height)
            .attr("filter", "url(#minimapDropShadow_qPWKOg)");


        minimap.update = function(hostTransform) {
            // invert the incoming zoomTransform; ordering matters here! you have to scale() before you translate()
            var modifiedTransform = d3.zoomIdentity.scale((1/hostTransform.k)).translate(-hostTransform.x, -hostTransform.y);
            // call this.zoom.transform which will reuse the handleZoom method below
            zoom.transform(frame, modifiedTransform);
            // update the new transform onto the minimapCanvas which is where the zoomBehavior stores it since it was the call target during initialization
            container.property("__zoom", modifiedTransform);

            updateMinimapZoomExtents();
        };


        /** RENDER **/
        minimap.render = function() {
            // update the placement of the minimap
            container.attr("transform", "translate(" + x + "," + y + ")scale(" + minimapScale + ")");
            // update the visualization being shown by the minimap in case its appearance has changed
            var node = target.node().cloneNode(true);
            node.removeAttribute("id");
            base.selectAll(".minimap .panCanvas").remove();
            minimap.node.appendChild(node); // minimap node is the container's node
            d3.select(node).attr("transform", "translate(0,0)");
            // keep the minimap's viewport (frame) sized to match the current visualization viewport dimensions
            frame.select(".background")
                .attr("width", width)
                .attr("height", height);
            frame.node().parentNode.appendChild(frame.node());
        };

        updateMinimapZoomExtents();
    }


    //============================================================
    // Accessors
    //============================================================


    minimap.width = function(value) {
        if (!arguments.length) return width;
        width = parseInt(value, 10);
        return this;
    };


    minimap.height = function(value) {
        if (!arguments.length) return height;
        height = parseInt(value, 10);
        return this;
    };


    minimap.x = function(value) {
        if (!arguments.length) return x;
        x = parseInt(value, 10);
        return this;
    };


    minimap.y = function(value) {
        if (!arguments.length) return y;
        y = parseInt(value, 10);
        return this;
    };


    minimap.host = function(value) {
        if (!arguments.length) { return host;}
        host = value;
        return this;
    }


    minimap.minimapScale = function(value) {
        if (!arguments.length) { return minimapScale; }
        minimapScale = value;
        return this;
    };


    minimap.target = function(value) {
        if (!arguments.length) { return target; }
        target = value;
        width  = parseInt(target.attr("width"),  10);
        height = parseInt(target.attr("height"), 10);
        return this;
    };

    return minimap;
};

/** GRAPH **/
const cartographer = function() {
    // call to render to ensure sizing is correct.
    let max_impact;
    canvas.render();

    cartographer.update_svg_style = function (svg) {
        window.style_element_text = svg
    }

    // Allow update of graph by parsing a JSON document.
    cartographer.update_graph = function (json_data) {
        console.log("Updating Graph");
        let data = JSON.parse(json_data);
        if(is_sankey_mode) {
            max_impact = data["max_impact"];
	        console.log("Max impact:", max_impact)
	    }
        heading.innerHTML = data.title;
        // Reset graph to empty
        graph = new dagre.graphlib.Graph({ multigraph: true }).setGraph({});

        // nodes --> graph
        data.nodes.forEach(buildGraphNode);
        console.log("Nodes successfully loaded...");

        // edges --> graph
        data.edges.forEach(buildGraphEdge);
        console.log("Edges successfully loaded...")

        //re-renders canvas with updated dimensions of the screen
        canvas.render();
        //draws graph into canvas
        canvas.addItem();

        // Adds click listener, calling handleMouseClick func
        var nodes = panCanvas.selectAll("g .node")
            .on("click", handleMouseClick);

        if(is_sankey_mode) {
            nodes.on("mouseover", handleMouseOverNode)
            nodes.on("mouseout", function(d) {
                div.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

            // change node fill based on impact
            var node_rects = panCanvas.selectAll("g .node rect")
            .on("click", handleMouseClick)
            .style("fill", function(d) {
                console.log(color(graph.node(d).ind_norm));
                return color(graph.node(d).ind_norm);
            });
        }

        // listener for mouse-hovers
        var edges = panCanvas.selectAll("g .edgePath")
            .on("mouseover", handleMouseOverEdge)
            .on("mouseout", function(d) {
            div.transition()
            .duration(500)
            .style("opacity", 0);
        });

        if(is_sankey_mode) {
            edges.attr("stroke-width", function(d) { return graph.edge(d).weight; })

             // re-scale arrowheads to fit into edge (they become really big otherwise)
            markers = d3.selectAll("marker")
                .attr("viewBox", "0 0 60 60");  // basically zoom out on the arrowhead

            // fix arrowhead urls
            d3.selectAll("path").attr("marker-end", function(data) {
                if (!this.attributes["marker-end"]) return null;
                else return "url(" + /url\(.*?(#.*?)\)/.exec(this.attributes["marker-end"].textContent)[1] + ")";
            });
        }
    };

    const buildGraphNode = function (n) {
        var node_data = {
            product: n['product'],
            location: n['location'],
            id: n['id'],
            database: n['db'],
            class: n['class'],
        };

        if(is_sankey_mode) {
            node_data.label = wrapText(n['name'], max_string_length)
                          + '\n' + n['location']
                          + '\n(' + Math.round(n['ind_norm'] * 100) + '%)';
            node_data.ind_norm = n['ind_norm'];
            node_data.tooltip = '<b>' + n['name'] + '</b>'
                      + '<br>Individual impact: &nbsp&nbsp&nbsp' + roundNumber(n['ind']) + ' ' + n['LCIA_unit'] +  ' (' + Math.round(n['ind_norm'] * 100) + '%)'
                      + '<br>Cumulative impact: ' + roundNumber(n['cum']) + ' ' + n['LCIA_unit'] +  ' (' + Math.round(n['cum_norm'] * 100) + '%)';
        } else {
            node_data.label = formatNodeText(n['name'], n['location']);
            node_data.labelType = "html";
        }

        graph.setNode(n['id'], node_data);
    };

    const buildGraphEdge = function (e) {
        var edge_data = {
            amount: e['amount'],
            unit: e['unit'],
            product: e['product'],
            tooltip: e['tooltip'],
            curve: d3.curveBasis,
        }

        if(is_sankey_mode) {
            edge_data.label = wrapText(e['product']
                + '\n(' + roundNumber(e['ind_norm']*100) + '%)', max_string_length);
            edge_data.weight = Math.abs(e["impact"] / max_impact ) * max_edge_width;
            let impact_or_benefit = "impact";
            if (e['impact'] < 0) {impact_or_benefit = "benefit"; console.log("BENEFIT");};
            edge_data.class = impact_or_benefit;
        } else {
            edge_data.label = formatEdgeText(e['product'], max_string_length);
            edge_data.labelType = "html";
            edge_data.arrowhead = "vee";
        }

        graph.setEdge(e['source_id'], e['target_id'], edge_data);
    };

    // Function called on click
    const handleMouseClick = function (node) {
        // make dictionary containing the node key and how the user clicked on it
        // see also mouse events: https://www.w3schools.com/jsref/obj_mouseevent.asp
        let click_dict = {
            "database": graph.node(node).database,
            "id": graph.node(node).id,
            "mouse": event.button,
            "keyboard": {
                "shift": event.shiftKey,
                "alt": event.altKey,
            }
        }
        console.log(click_dict)

        // pass click_dict (as json text) to python via bridge
        window.bridge.node_clicked(JSON.stringify(click_dict))
    };

    const handleMouseOverNode = function (n) {
        console.log ("mouseover Node!");
        node = graph.node(n);
        div.transition()
            .duration(200)
            .style("opacity", .9);
        div	.html(node.tooltip)
            .style("left", (d3.event.pageX) + "px")
            .style("top", (d3.event.pageY - 28) + "px");
    };

    const handleMouseOverEdge = function (e) {
        console.log ("mouseover Edge!");
        edge = graph.edge(e);
        div.transition()
            .duration(200)
            .style("opacity", .9);
        div	.html(edge.tooltip)
            .style("left", (d3.event.pageX) + "px")
            .style("top", (d3.event.pageY - 28) + "px");
    };
};


/** RUN SCRIPT **/

//instantiation of canvas container+reset button
var canvas = d3.demo.canvas();
d3.select("#canvasqPWKOg").call(canvas);

d3.select("#resetButtonqPWKOg").on("click", function() {
    canvas.reset();
});

d3.select("#downloadSVGtButtonqPWKOg").on("click", function() {

    // create new svg element
    var clone = document.createElementNS("http://www.w3.org/2000/svg", "svg");

    // copy figure content to new svg element
    var inner_graphic = document.getElementsByClassName("inner")[0]
    clone.innerHTML = inner_graphic.outerHTML;

    // edit new svg element
    var parentTag = document.getElementById("canvasqPWKOg");
    var svg = parentTag.firstChild
    var svg_rect = svg.getBBox(); // get the bounding rectangle
    clone.setAttribute("width", String(svg_rect.width));
    clone.setAttribute("height", String(svg_rect.height));

    var inner_graphic_staging = clone.getElementsByClassName("inner")[0]
    panCanvasElem = inner_graphic_staging.getElementsByClassName("panCanvas")[0]
    panCanvasElem.removeAttribute("width")
    panCanvasElem.removeAttribute("height")
    panCanvasElem.removeAttribute("transform")
    var rect_elem = inner_graphic_staging.getElementsByClassName("background")[0]
    inner_graphic_staging.removeChild(rect_elem);

    // insert style info
    clone.insertAdjacentHTML('afterbegin', window.style_element_text)

    //get svg source
    var serializer = new XMLSerializer();
    var source = serializer.serializeToString(clone);

    window.bridge.download_triggered(source)
});

// Construct 'render' object and initialize cartographer.
var render = dagreD3.render();
var graph = new dagre.graphlib.Graph({ multigraph: true }).setGraph({});
cartographer();

/* END OF ADAPTED DEMO SCRIPT*/

/**
 * Build svg container and listen for zoom and drag calls
 */

/*
var svg = d3.select("body")
 .append("svg")
 .attr("viewBox", "0 0 600 400")
 .attr("height", "100%")
 .attr("width", "100%")
 .call(d3.zoom().on("zoom", function () {
    svg.attr("transform", d3.event.transform)
 })) */


// Tooltip: http://bl.ocks.org/d3noob/a22c42db65eb00d4e369
var div = d3.select("#canvasqPWKOg").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

// Access graph size:
//panCanvas.graph().width

var color = d3.scaleLinear()
    .domain([-99999999, -1, 0, 1, 99999999])
    .range(["green", "green", "white", "red", "red"]);

//var color = d3.scaleLinear()
//    .domain([-1, 0, 1])
//    .range(["green", "white", "red"]);

// break strings into multiple lines after certain length if necessary
function wrapText(str, length) {
    //console.log(str.replace(/.{10}\S*\s+/g, "$&@").split(/\s+@/).join("\n"))
    return str.replace(/.{15}\S*\s+/g, "$&@").split(/\s+@/).join(is_sankey_mode?"\n":"<br>")
//    return str.match(new RegExp('.{1,' + length + '}', 'g')).join("\n");
}

function roundNumber(number) {
//    return number.toFixed(2)
    return number.toPrecision(3)
//    return Math.round(number * 100)/100
}

function formatNodeText(name, location) {
    html = '<text class="activityNameText">' + wrapText(name) + '<br>'
    + '</span><span class="locationText">' + location + '</text>'
    return html
}

function formatEdgeText(product) {
    html = '<text class="edgeText">' + wrapText(product) + '</span>'
    return html
}

// Connect bridge to 'update_graph' function through QWebChannel.
new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.bridge;
    window.bridge.graph_ready.connect(cartographer.update_graph);
    window.bridge.style.connect(cartographer.update_svg_style);
});

