let is_sankey_mode = window.ab_sankey_mode || false;
let interactive = window.ab_interactive || false;
let graph_direction = window.ab_graph_direction || "BT";
let mode = is_sankey_mode ? "Sankey" : "Navigator";
if (is_sankey_mode) {
    window.ab_show_sankey_minimap = false;
}

var sankeyColorBy = "direct";
var sankeyOrdinal = null;

function resetSankeyColorScale(payload) {
    sankeyColorBy = (payload && payload.color_by) ? payload.color_by : "direct";
    sankeyOrdinal = null;
    if (sankeyColorBy === "direct" || !payload || !payload.nodes) {
        return;
    }
    var keys = payload.nodes.map(function (n) { return n.color_key; }).filter(Boolean);
    if (typeof abOrdinalScale === "function") {
        sankeyOrdinal = abOrdinalScale(keys);
    } else if (typeof d3.scaleOrdinal === "function" && d3.schemeTableau10) {
        sankeyOrdinal = d3.scaleOrdinal(d3.schemeTableau10).domain(Array.from(new Set(keys)));
    }
}

function sankeyNodeFill(n) {
    if (sankeyColorBy && sankeyColorBy !== "direct" && n && n.color_key && sankeyOrdinal) {
        return sankeyOrdinal(n.color_key);
    }
    var v = n && n.direct_emissions_score_normalized;
    if (typeof abSankeyDirectFill === "function") {
        return abSankeyDirectFill(v);
    }
    return color(v);
}

function sankeyShowTriangle(n) {
    return n && !n.is_aggregate && (n.has_hidden_suppliers || n.can_collapse);
}

console.log(`Starting ${mode}, interactive: ${interactive}`);

// SETUP GRAPH
// https://github.com/dagrejs/graphlib/wiki/API-Reference

const clamp = function (num, min, max) {
    return Math.min(Math.max(num, min), max);
};

const getGraphConfig = function () {
    var cfg = {
        rankdir: graph_direction,
    };
    if (is_sankey_mode) {
        cfg.ranksep = (graph_direction === "LR" || graph_direction === "RL") ? 36 : 26;
        cfg.ranker = "tight-tree";
    }
    return cfg;
};

/**
 * Debounces a function so repeated calls are ignored.
 * @param func
 * @param wait
 * @returns {(function(): void)|*}
 */
function debounce(func, wait) {
    var timeout;
    return () => {
        const context = this, args = arguments;
        const later = function () {
            timeout = null;
            func.apply(context, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};


function getWindowSize() {
    w = window,
        d = document,
        e = d.documentElement,
        g = d.getElementsByTagName('body')[0],
        x = w.innerWidth; //|| e.clientWidth || g.clientWidth;
    y = w.innerHeight; //|| e.clientHeight || g.clientHeight;

    //preventing the svg canvas to be 0x0, as page is loaded in the background with dimensions 0x0
    if (x, y == 0) {
        x = 800;
        y = 600;
    }

    globalWidth = x;
    globalHeight = y;
    globalMinWidth = globalWidth * 0.98;
    return {x, y};
};

/**
 * Sankey-only: fixed overview of the full graph; a red-outlined viewport shows main zoom/pan.
 * Drag the viewport or wheel on the minimap to change only the main Sankey transform.
 */
/** Sankey minimap + label helpers live in sankey_graph_style.js. */

var max_string_length = 20;
var max_edge_width = 40;

var globalWidth = null;
var globalHeight = null;
var globalMinWidth = null;

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
d3.demo.canvas = function () {

    getWindowSize();

    "use strict";
    console.log("w: " + globalWidth + " ; h: " + globalHeight)
    var sankeyMainHeightFrac = 0.76;
    var width = globalWidth * (is_sankey_mode ? 0.99 : 1.0),
        height = globalHeight * (is_sankey_mode ? sankeyMainHeightFrac : 0.6),
        base = null,
        wrapperBorder = 0;

    //introduced function to reset width/height according to new window sizes
    function updateDimensions(minWidth) {
        getWindowSize();
        // Sankey: graph size from the canvas div (flex fills the webview below the controls).
        if (is_sankey_mode) {
            var el = document.getElementById("canvasqPWKOg");
            if (el) {
                var w = el.clientWidth, h = el.clientHeight;
                if (h < 80) {
                    h = Math.max(80, Math.floor(window.innerHeight - el.getBoundingClientRect().top - 4));
                }
                if (w >= 100 && h >= 80) {
                    width = w;
                    height = h;
                    globalMinWidth = width;
                    return;
                }
            }
        }
        if (arguments.length) {
            if (minWidth < globalWidth * 0.99) {
                minWidth = globalWidth * 0.99; // -1% to avoid using scroll bars when not necessary
            } else {
                globalMinWidth = minWidth + 20; // +20px to compensate for the scroll bar width
            }
        } else {
            minWidth = globalMinWidth;
        }
        width = minWidth;
        height = globalHeight * (is_sankey_mode ? sankeyMainHeightFrac : 0.65);
    }

    function canvas(selection) {

        base = selection;
        var plotTopInset = 0;
        var sankeyPanMinimap = null;
        var lastMainTransform = d3.zoomIdentity;

        var svgWidth = (width + (wrapperBorder * 2));
        var svgHeight = (height + (wrapperBorder * 2));
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

        var outerWrapper = svg.append("g")
            .attr("class", "wrapper outer")
            .attr("transform", "translate(0, " + plotTopInset + ")");
        outerWrapper.append("rect")
            .attr("class", "background")
            .attr("width", width + wrapperBorder * 2)
            .attr("height", height + wrapperBorder * 2);

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
        var updateCanvasZoomExtents = function () {
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

        var zoomHandler = function (event) {
            var t = event.transform;
            panCanvas.attr("transform", t);
            lastMainTransform = t;
            innerWrapper.property("__zoom", t);
            if (sankeyPanMinimap) {
                sankeyPanMinimap.onMainZoom(t);
            }
            updateCanvasZoomExtents();
        };

        zoom.on("zoom", zoomHandler);

        innerWrapper.call(zoom);

        if (is_sankey_mode) {
            sankeyPanMinimap = abCreateSankeyPanMinimap({
                svg: svg,
                innerWrapper: innerWrapper,
                panCanvas: panCanvas,
                zoomMain: zoom,
                getVpW: function () {
                    return width;
                },
                getVpH: function () {
                    return height;
                },
                onHostTransform: function (t) {
                    lastMainTransform = t;
                }
            });
        }

        canvas.applySankeyMinimapVisibility = function () {
            if (sankeyPanMinimap) {
                sankeyPanMinimap.setVisible(window.ab_show_sankey_minimap === true);
            }
        };

        canvas.refreshThemeFills = function () {
            if (!is_sankey_mode) {
                return;
            }
            panCanvas.selectAll("g .node rect")
                .style("fill", function (d) {
                    return sankeyNodeFill(graph.node(d));
                });
        };

        /** ADD SHAPE **/
        canvas.addItem = function () {
            graph.graph().transition = function (selection) {
                return selection.transition().duration(300);
            };
            canvas.render();
            panCanvas.call(render, graph);
            var miniMapInterval = setInterval(function () {
                if (sankeyPanMinimap) {
                    sankeyPanMinimap.refresh();
                }
            }, 100);
            setTimeout(function () {
                clearInterval(miniMapInterval);
            }, 500);
            updateDimensions();
        };

        /** RENDER **/
        canvas.render = function () {
            updateDimensions();
            svgDefs
                .select(".clipPath .background")
                .attr("width", width)
                .attr("height", height);
            svg
                .attr("width", width + (wrapperBorder * 2))
                .attr("height", plotTopInset + height + (wrapperBorder * 2));

            outerWrapper
                .select(".background")
                .attr("width", width + wrapperBorder * 2)
                .attr("height", height + wrapperBorder * 2);

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

            if (sankeyPanMinimap) {
                sankeyPanMinimap.resize(height + plotTopInset);
                sankeyPanMinimap.refresh();
                sankeyPanMinimap.onMainZoom(lastMainTransform);
                canvas.applySankeyMinimapVisibility();
            }
        };

        canvas.reset = function () {
            zoom.transform(panCanvas, d3.zoomIdentity);
            svg.property("__zoom", d3.zoomIdentity);
            innerWrapper.property("__zoom", d3.zoomIdentity);
            lastMainTransform = d3.zoomIdentity;
            if (sankeyPanMinimap) {
                sankeyPanMinimap.onMainZoom(d3.zoomIdentity);
            }
        };

        canvas.update = function (minimapZoomTransform) {
            innerWrapper.call(zoom.transform, minimapZoomTransform);
            innerWrapper.property("__zoom", minimapZoomTransform);
            lastMainTransform = minimapZoomTransform;
            if (sankeyPanMinimap) {
                sankeyPanMinimap.onMainZoom(minimapZoomTransform);
            }
            updateCanvasZoomExtents();
        };

        canvas.zoomTo = function (zoomTo) {
            canvas.update(zoomTo);
        };

        canvas.getMainTransform = function () {
            try {
                var innerT = d3.zoomTransform(innerWrapper.node());
                if (innerT && (innerT.k !== 1 || innerT.x !== 0 || innerT.y !== 0)) {
                    return innerT;
                }
                var panT = d3.zoomTransform(panCanvas.node());
                if (panT && (panT.k !== 1 || panT.x !== 0 || panT.y !== 0)) {
                    return panT;
                }
            } catch (err) {
                /* fall through */
            }
            return lastMainTransform;
        };

        canvas.zoomToNode = function (nodeId, options = {}) {
            const node = graph.node(nodeId)
            const canvasWidth = new Number(panCanvas.attr("width")) || globalWidth;
            const canvasHeight = new Number(panCanvas.attr("height")) || (globalHeight || 600);
            const scale = 1;
            const {e: x, f: y} = node.elem.transform.baseVal[0].matrix
            const xOffset = canvasWidth / 2;
            const yOffset = canvasHeight / 2;
            canvas.zoomTo(d3.zoomIdentity.scale(scale).translate(((x * -scale) + xOffset), ((y * -scale) + yOffset)
            ))
        }

        updateCanvasZoomExtents();
    }


    //============================================================
    // Accessors
    //============================================================

    canvas.width = function (value) {
        if (!arguments.length) return width;
        width = parseInt(value, 10);
        return this;
    };

    canvas.height = function (value) {
        if (!arguments.length) return height;
        height = parseInt(value, 10);
        return this;
    };

    return canvas;
};

/**
 * Word-wrap for dagre plain-text edge labels: dagre-d3 splits on "\\n" into tspans.
 * maxLen approximates "not wider than the node" when chosen from node label widths.
 */
/** Sankey wrap/label helpers live in sankey_graph_style.js. */


/** GRAPH **/
const cartographer = function () {
    let data;
    var sankeyDemandIds = {};
    // call to render to ensure sizing is correct.
    canvas.render();

    cartographer.update_svg_style = function (svg) {
        window.style_element_text = svg
    }

    cartographer.renderGraph = function (options = {}) {
        const renderOptions = Object.assign({
            center: true,
        }, options)
        //draws graph into canvas
        canvas.addItem();

        // add node selection items (graph explorer; Sankey dropped this chrome)
        if (!nodeSelection.empty()) {
            const nodeSelectionOptions = nodeSelection.selectAll("option")
                .data(graph.nodes());
            nodeSelectionOptions
                .enter()
                .append("option")
                .merge(nodeSelectionOptions)
                .attr("value", function (d) {
                    return d;
                })
                .text(function (d) {
                    const node = graph.node(d);
                    return node.name;
                });
            nodeSelectionOptions.exit().remove();
        }

        // Attach listeners to dagre's node elements. Do not rebind .data() by
        // index — that swaps visit ids onto the wrong boxes (labels stay
        // correct, clicks/hovers/Open process do not).
        var nodes = panCanvas.selectAll("g.node");
        nodes.on("click", handleMouseClick);
        if (is_sankey_mode) {
            nodes.on("contextmenu", handleContextMenu);
        }

        if (is_sankey_mode) {
            nodes.on("mousemove", handleMouseOverNode)
                .on("mouseleave", handleMouseOutNode);

            // change node fill based on impact
            if (canvas.refreshThemeFills) {
                canvas.refreshThemeFills();
            }
        }

        // listener for mouse-hovers
        var edges = panCanvas.selectAll("g .edgePath");
        if (is_sankey_mode) {
            edges.on("mousemove", handleMouseOverEdge)
                .on("mouseleave", handleMouseOutEdge);
            panCanvas.selectAll("g.edgeLabel")
                .on("mousemove", handleMouseOverEdge)
                .on("mouseleave", handleMouseOutEdge);
        } else {
            edges.on("mouseover", handleMouseOverEdge)
                .on("mouseout", handleMouseOutEdge);
        }

        if (is_sankey_mode) {
            edges.attr("stroke-width", function (d) {
                var ed = graph.edge(d) || {};
                return ed._strokeWidth || ed.weight || 1;
            })

            // re-scale arrowheads to fit into edge (they become really big otherwise)
            markers = d3.selectAll("marker")
                .attr("viewBox", "0 0 60 60");  // basically zoom out on the arrowhead

            // fix arrowhead urls
            d3.selectAll("path").attr("marker-end", function (data) {
                if (!this.attributes["marker-end"]) return null;
                else return "url(" + /url\(.*?(#.*?)\)/.exec(this.attributes["marker-end"].textContent)[1] + ")";
            });
        }

        if (is_sankey_mode) {
            nodes.each(function (d) {
                var n = graph.node(d);
                if (!sankeyShowTriangle(n)) {
                    d3.select(this).selectAll(".triangle").remove();
                    return;
                }
                var triangles = d3.select(this).selectAll(".triangle").data([d]);
                var tri = "translate(0, 35) rotate(180)";
                if (typeof abSankeyTriangleTransform === "function") {
                    tri = abSankeyTriangleTransform(graph_direction, n.width, n.height);
                }
                triangles.enter().append("path").merge(triangles)
                    .attr("class", "triangle")
                    .attr("d", d3.symbol().type(d3.symbolTriangle).size(36))
                    .attr("transform", tri)
                    .style("pointer-events", "none");
            });
        }

        if (interactive) {
            const dataExpanded = function (d) {
                if (!graph.node(d)) {
                    return null
                }
                return graph.node(d).expanded ? "1" : "0"
            }
            let transformTriangle
            switch (ab_graph_direction) {
                case "TB":
                    transformTriangle = () => {
                        return "translate(0, -35)"
                    }
                    break
                case "BT":
                    transformTriangle = () => {
                        return "translate(0, 35) rotate(180)"
                    }
                    break
                case "RL":
                    transformTriangle = (rect) => {
                        return `translate(${rect.width.baseVal.value / 2 + 5}, 5) rotate(90)`
                    }
                    break
                case "LR":
                    transformTriangle = (rect) => {
                        return `translate(-${rect.width.baseVal.value / 2 + 5}, 5) rotate(-90)`
                    }
                    break
            }
            nodes.each(
                function (d) {
                    var triangles = d3.select(this).selectAll('.triangle').data([d]);
                    var rect = d3.select(this).select('rect').node();
                    triangles.enter().append("path").merge(triangles).attr("class", "triangle").attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
                        .attr("transform", transformTriangle(rect)).attr("data-expanded", dataExpanded)
                }
            )
        }

        if (renderOptions.restoreTransform) {
            canvas.zoomTo(renderOptions.restoreTransform);
        } else if (renderOptions.center) {
            const {width: graphWidth, height: graphHeight} = graph.graph();
            const canvasWidth = new Number(panCanvas.attr("width")) || globalWidth;
            const canvasHeight = new Number(panCanvas.attr("height")) || (globalHeight || 600);
            const heightRatio = canvasHeight / graphHeight;
            const widthRatio = canvasWidth / (graphWidth * 1.05);
            const scale = clamp(Math.min(heightRatio, widthRatio, 1), .25, .5)
            const node = d3.select("g.node").node();
            if (node === null) {
                return;
            }
            const {e: x, f: y} = node.transform.baseVal[0].matrix
            const count = d3.selectAll("g.node").size();
            let ty, xOffset, yOffset;
            switch (graph.graph().rankdir) {
                case "TB":
                case "BT":
                    xOffset = canvasWidth / 2;
                    yOffset = y;
                    break
                case "LR":
                case "RL":
                default:
                    xOffset = x + 25;
                    yOffset = (canvasHeight / 2);
            }
            switch (count) {
                case 1:
                    ty = ((y * -scale) + (canvasHeight / 2));
                    break
                default:
                    ty = ((y * -scale) + yOffset)
            }
            canvas.zoomTo(d3.zoomIdentity.scale(scale).translate(((x * -scale) + xOffset), ty))
        }
    }

    // Allow update of graph by parsing a JSON document.
    cartographer.update_graph = function (json_data) {
        console.log("Updating Graph");
        var savedTransform = (is_sankey_mode && canvas.getMainTransform)
            ? canvas.getMainTransform()
            : null;
        data = JSON.parse(json_data);
        resetSankeyColorScale(data);
        if (is_sankey_mode && data.nodes) {
            data._sankeyEdgeWrapCols = inferSankeyEdgeLabelMaxCols(data);
        }
        var headingEl = document.getElementById("heading");
        if (data.title && headingEl) {
            headingEl.innerHTML = data.title;
        }
        // Reset graph to empty
        graph = new dagre.graphlib.Graph({multigraph: true}).setGraph(getGraphConfig());
        console.log(JSON.stringify(graph))

        // nodes --> graph
        data.nodes.forEach(buildGraphNode);
        console.log("Nodes successfully loaded...");

        sankeyDemandIds = (typeof abDemandIdSet === "function")
            ? abDemandIdSet(data.nodes)
            : {};
        data.edges.forEach(buildGraphEdge);
        console.log("Edges successfully loaded...")
        var preserve = is_sankey_mode && data.preserve_view && savedTransform
            && (savedTransform.k !== 1 || savedTransform.x !== 0 || savedTransform.y !== 0);
        cartographer.renderGraph({
            center: !preserve,
            restoreTransform: preserve ? savedTransform : null,
        });
    };

    cartographer.applySankeyEdgeLabels = function () {
        if (!is_sankey_mode || typeof data === "undefined" || !data || !data.edges) {
            return;
        }
        data.edges.forEach(buildGraphEdge);
        cartographer.renderGraph({ center: false });
    };

    cartographer.setRankdir = function (dir) {
        graph_direction = (typeof abNormalizeRankdir === "function")
            ? abNormalizeRankdir(dir)
            : ((dir === "LR" || dir === "RL") ? "RL" : "BT");
        window.ab_graph_direction = graph_direction;
        if (typeof data === "undefined" || !data) {
            return;
        }
        graph.setGraph(getGraphConfig());
        sankeyDemandIds = (typeof abDemandIdSet === "function")
            ? abDemandIdSet(data.nodes)
            : {};
        data.nodes.forEach(buildGraphNode);
        data.edges.forEach(buildGraphEdge);
        cartographer.renderGraph({center: true});
    };

    const buildGraphNode = function (n) {
        if (n.is_aggregate && n.aggregate_key) {
            n.name = n.aggregate_key;
        }
        if (!is_sankey_mode) {
            n.label = formatNodeTextPlain(n['name'], n['location']);
            delete n.labelType;
        } else {
            var innerWidth = inferSankeyNodeInnerWidthPx(n);
            var wrapCols = inferSankeyNodeWrapColsFromWidth(innerWidth);
            n.label = formatSankeyNodePlainTextLabel(n, wrapCols);
            delete n.labelType;
            n.width = innerWidth;
            n.height = AB_SANKEY_NODE_INNER_HEIGHT_PX;
            n.paddingLeft = AB_SANKEY_NODE_PADDING_X;
            n.paddingRight = AB_SANKEY_NODE_PADDING_X;
            n.paddingTop = AB_SANKEY_NODE_PADDING_Y;
            n.paddingBottom = AB_SANKEY_NODE_PADDING_Y;
        }
        if (n.visit_id == null || n.visit_id === "") {
            n.visit_id = n.id;
        }
        if (interactive) {
            n.expanded = n['expanded']
            n.collapsed = false;
        }
        graph.setNode(n['id'], n);
    };

    const buildGraphEdge = function (e) {
        var rec = Object.assign({}, e);
        rec.curve = d3.curveBasis;
        rec._strokeWidth = (typeof abEdgeStrokeWidth === "function")
            ? abEdgeStrokeWidth(e.weight)
            : Math.max(1, Number(e.weight) || 0);

        if (!is_sankey_mode) {
            rec.label = formatEdgeTextPlain(e['product'], max_string_length);
            delete rec.labelType;
            rec.arrowhead = "vee";
        } else {
            var joinLabel = formatSankeyTwoLineEdgeLabel(e);
            var wrapCols = (data && data._sankeyEdgeWrapCols) ? data._sankeyEdgeWrapCols : 12;
            rec.label = wrapSankeyEdgeLabelMultiline(joinLabel, wrapCols);
            delete rec.labelType;
            delete rec.arrowhead;
            if (typeof abLayoutEdgeWeight === "function") {
                rec.weight = abLayoutEdgeWeight(e, sankeyDemandIds);
            }
        }

        graph.setEdge(rec.source_id, rec.target_id, rec);
    };

    function toggleCollapse(nodeId, collapse = false) {
        const node = graph.node(nodeId);
        const edges = graph.nodeEdges(nodeId);
        if (node.collapsed) {
            // Expand the node
            data.edges.forEach(edge => {
                if (edge.target_id == node.id) {
                    buildGraphEdge(edge)
                    let addNode = data.nodes.find(n => n.id == edge.source_id);
                    if (addNode) {
                        buildGraphNode(addNode)
                        graph.node(addNode.id).collapsed = true;
                        toggleCollapse(addNode.id)
                    }
                }
            })
            node.collapsed = false
        } else {
            // Collapse the node
            edges.forEach(edge => {
                if (edge.w == node.id) {
                    graph.node(edge.v).collapsed = false;
                    toggleCollapse(edge.v)
                    graph.removeEdge(edge.v, edge.w);
                    graph.removeNode(edge.v);
                }
            });
            node.collapsed = true
        }

    }

    // Function called on click
    const handleMouseClick = function (event, node) {
        // make dictionary containing the node key and how the user clicked on it
        // see also mouse events: https://www.w3schools.com/jsref/obj_mouseevent.asp
        let gNode = graph.node(node)
        let click_id = (gNode.click_uid != null && gNode.click_uid !== "")
            ? gNode.click_uid
            : gNode.id;
        let click_dict = {
            "database": gNode.database,
            "id": click_id,
            "mouse": event.button,
            "keyboard": {
                "shift": event.shiftKey,
                "alt": event.altKey,
            }
        }
        if (interactive && gNode.expanded) {
            toggleCollapse(node)
            cartographer.renderGraph({center: true})
        }

        // pass click_dict (as json text) to python via bridge
        window.bridge.node_clicked(JSON.stringify(click_dict))
    };

    const handleContextMenu = function (event, node) {
        event.preventDefault();
        event.stopPropagation();
        hideNavigatorTip();
        let gNode = graph.node(node);
        if (!gNode) {
            return;
        }
        let click_dict = (typeof abOpenProcessPayload === "function")
            ? abOpenProcessPayload(gNode)
            : {
                visit_id: gNode.visit_id != null ? gNode.visit_id : gNode.id,
                unique_id: gNode.visit_id != null ? gNode.visit_id : gNode.id,
                activity_id: gNode.activity_id != null ? gNode.activity_id : null,
                database: gNode.database || "",
                code: gNode.code || "",
                is_aggregate: !!gNode.is_aggregate,
                constituent_uids: gNode.constituent_uids || [],
                mouse: 2
            };
        click_dict.id = click_dict.visit_id;
        click_dict.keyboard = {
            shift: event.shiftKey,
            alt: event.altKey
        };
        window.bridge.node_clicked(JSON.stringify(click_dict));
    };

    const showNavigatorTip = function (event, html, fallbackTop) {
        if (is_sankey_mode && typeof abPlaceHtmlTooltip === "function") {
            div.style("opacity", 1);
            abPlaceHtmlTooltip(div, event, html);
            return;
        }
        div.transition()
            .duration(200)
            .style("opacity", .9);
        div.html(html)
            .style("left", (event.pageX) + "px")
            .style("top", (event.pageY - fallbackTop) + "px");
    };

    const hideNavigatorTip = function () {
        if (is_sankey_mode) {
            div.attr("hidden", "hidden").style("opacity", 0);
            return;
        }
        div.transition()
            .duration(500)
            .style("opacity", 0);
    };

    const handleMouseOverNode = function (event, n) {
        node = graph.node(n);
        d3.select(node.elem)
            .style("opacity", .4);
        var unit = (data && data.unit) ? data.unit : "";
        var tipHtml = (typeof abContributionTooltipHtml === "function")
            ? abContributionTooltipHtml(node, unit)
            : String(node.tooltip || "").replace(/\n/g, "<br>");
        showNavigatorTip(event, tipHtml, 28);
    };

    const handleMouseOutNode = function (event, n) {
        node = graph.node(n);
        d3.select(node.elem)
            .style("opacity", 1);
        hideNavigatorTip();
    }

    const handleMouseOutEdge = function () {
        hideNavigatorTip();
    };

    const handleMouseOverEdge = function (event, e) {
        edge = graph.edge(e);
        var tipHtml = is_sankey_mode ? buildSankeyEdgeTooltipHtml(edge) : (edge.tooltip || "");
        showNavigatorTip(event, tipHtml, 56);
    };
};


/** RUN SCRIPT **/

//instantiation of canvas container+reset button
var canvas = d3.demo.canvas();
d3.select("#canvasqPWKOg").call(canvas);
window.abOnGraphThemeChanged = function () {
    if (canvas && canvas.refreshThemeFills) {
        canvas.refreshThemeFills();
    }
};

(function wireSankeyMinimapToggle() {
    if (!is_sankey_mode) {
        return;
    }
    var cb = document.getElementById("sankeyMinimapVisible");
    if (!cb) {
        return;
    }
    window.ab_show_sankey_minimap = cb.checked;
    cb.addEventListener("change", function () {
        window.ab_show_sankey_minimap = cb.checked;
        if (canvas.applySankeyMinimapVisibility) {
            canvas.applySankeyMinimapVisibility();
        }
    });
})();

(function wireResetZoom() {
    var resetSel = d3.select("#resetButtonqPWKOg");
    if (!resetSel.empty()) {
        resetSel.on("click", function () {
            canvas.reset();
        });
    }
})();

(function wireDownloadSvg() {
    var btn = d3.select("#downloadSVGtButtonqPWKOg");
    if (btn.empty()) {
        return;
    }
    btn.on("click", function () {
        var svgMarkup = buildNavigatorSvgExport();
        if (svgMarkup) {
            window.bridge.download_triggered(svgMarkup);
        }
    });
})();

// Construct 'render' object and initialize cartographer.
var render = dagreD3.render();
var graph = new dagre.graphlib.Graph({multigraph: true}).setGraph(getGraphConfig());
cartographer();

(function wireSankeyLabelOptionToggles() {
    if (!is_sankey_mode) {
        return;
    }
    function bindCheckbox(id, globalProp) {
        var el = document.getElementById(id);
        if (!el) {
            return;
        }
        window[globalProp] = el.checked;
        el.addEventListener("change", function () {
            window[globalProp] = el.checked;
            if (cartographer.applySankeyEdgeLabels) {
                cartographer.applySankeyEdgeLabels();
            }
        });
    }
    bindCheckbox("sankeyFlowsVisible", "ab_sankey_show_flows");
    bindCheckbox("sankeyImpactAbsoluteVisible", "ab_sankey_impact_absolute");
    bindCheckbox("sankeyImpactRelativeVisible", "ab_sankey_impact_relative");
    var rankSel = document.getElementById("sankeyRankdir");
    if (rankSel) {
        graph_direction = (typeof abNormalizeRankdir === "function")
            ? abNormalizeRankdir(rankSel.value)
            : ((rankSel.value === "LR" || rankSel.value === "RL") ? "RL" : "BT");
        window.ab_graph_direction = graph_direction;
        rankSel.addEventListener("change", function () {
            if (cartographer.setRankdir) {
                cartographer.setRankdir(rankSel.value);
            }
        });
    }
})();

/* END OF ADAPTED DEMO SCRIPT*/

/**
 * Build svg container and listen for zoom and drag calls
 */


// Tooltip: http://bl.ocks.org/d3noob/a22c42db65eb00d4e369
var div = d3.select("#canvasqPWKOg").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);
if (is_sankey_mode) {
    div.attr("hidden", "hidden");
}

var color = d3.scaleLinear()
    .domain([-99999999, -1, 0, 1, 99999999])
    .range(["green", "green", "white", "#4682d2", "#4682d2"]);

var nodeSelection = d3.select("select#nodeSelectPWK0g")

d3.select("#nodeSelectPWK0gExecute").on("click", function () {
    var selectedId = d3.select("#nodeSelectPWK0g").property("value");
    canvas.zoomToNode(selectedId, {scale: 1.5});
})

// break strings into multiple lines after certain length if necessary
function wrapText(str, length) {
    return str.replace(/.{15}\S*\s+/g, "$&@").split(/\s+@/).join("\n");
}

function roundNumber(number) {
    return number.toPrecision(3)
}

/** Plain-text node label (SVG tspans) for Tree and SVG export. */
function formatNodeTextPlain(name, location) {
    var lines = wrapText(String(name || "")).split("\n").filter(function (s) { return s.length; });
    var loc = String(location != null ? location : "").trim();
    if (loc) {
        lines.push(loc);
    }
    return lines.join("\n");
}

/** Plain-text edge label (SVG tspans) for Tree and SVG export. */
function formatEdgeTextPlain(product) {
    return wrapText(String(product || ""));
}

/**
 * Styles for a standalone SVG file. Sankey rules in navigator CSS are scoped to
 * body.ab-sankey-tab and do not apply after export; repeat the graph-relevant ones.
 */
function navigatorSvgExportStyles() {
    var base = window.style_element_text || "";
    var locFill = (typeof abGraphIsDark === "function" && abGraphIsDark()) ? "#b0b0b0" : "#666";
    var sankeySvgRules = is_sankey_mode
        ? "<style>" +
            "g.node text,g.node text tspan{font-size:12px;}" +
            "g.node text tspan:nth-last-child(2){fill:" + locFill + ";}" +
            "g.edgeLabel text,g.edgeLabel tspan{font-size:11px;}" +
            "</style>"
        : "";
    return base + sankeySvgRules;
}

/**
 * Export the dagre graph layer only (same nodes/labels as on screen), not the
 * AB viewport chrome (grey/white pan background, minimap, clip rect).
 */
function buildNavigatorSvgExport() {
    var output = document.querySelector(".panCanvas g.output");
    if (!output) {
        return null;
    }

    var bbox = output.getBBox();
    if (!(bbox.width > 0) || !(bbox.height > 0)) {
        return null;
    }

    var pad = 16;
    var vbX = bbox.x - pad;
    var vbY = bbox.y - pad;
    var vbW = bbox.width + pad * 2;
    var vbH = bbox.height + pad * 2;

    var svgNS = "http://www.w3.org/2000/svg";
    var out = document.createElementNS(svgNS, "svg");
    out.setAttribute("xmlns", svgNS);
    out.setAttribute("class", "svg canvas");
    out.setAttribute("width", String(vbW));
    out.setAttribute("height", String(vbH));
    out.setAttribute("viewBox", vbX + " " + vbY + " " + vbW + " " + vbH);

    out.insertAdjacentHTML("afterbegin", navigatorSvgExportStyles());

    var backdrop = document.createElementNS(svgNS, "rect");
    backdrop.setAttribute("x", String(vbX));
    backdrop.setAttribute("y", String(vbY));
    backdrop.setAttribute("width", String(vbW));
    backdrop.setAttribute("height", String(vbH));
    backdrop.setAttribute("fill", "#FFFFFF");
    out.appendChild(backdrop);
    out.appendChild(output.cloneNode(true));

    return new XMLSerializer().serializeToString(out);
}

// Connect bridge to 'update_graph' function through QWebChannel.
new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.bridge;
    window.bridge.graph_ready.connect(cartographer.update_graph);
    window.bridge.style.connect(cartographer.update_svg_style);
});

function rerenderGraphImp() {
    cartographer.renderGraph({center: true})
}

const rerenderGraph = debounce(rerenderGraphImp, 500)

window.addEventListener('resize', function (event) {
    rerenderGraph()
}, true);

if (is_sankey_mode) {
    setTimeout(function () {
        canvas.render();
        if (graph && typeof graph.nodes === "function" && graph.nodes().length) {
            rerenderGraphImp();
        }
    }, 0);
}
