console.log(`Starting Activity Navigator`);

const test_data = {
    "nodes": [
        {
            "id": "choc_proc",
            "name": "Chocolate Factory",
            "functions": [{"name": "Chocolate", "id": "chocolate"}]
        },
        {
            "id": "elec_proc",
            "name": "Combined Heat & Power",
            "location": "NL",
            "functions": [{"name": "Electricity", "id": "electricity"}, {"name": "Heat", "id": "heat"}]
        },
        {
            "id": "beans_proc",
            "name": "Chocolate Beans Market",
            "functions": [{"name": "Chocolate Beans", "id": "chocolate_beans"}]
        }
            ],
    "edges": [
        {
            "source_id": "elec_proc",
            "target_id": "choc_proc",
            "amount": 0.25,
            "unit": "kilowatt hour",
            "product": "Electricity",
            "product_id": "electricity",
    }, {
            "source_id": "beans_proc",
            "target_id": "choc_proc",
            "amount": 0.00612146666666667,
            "unit": "kilogram",
            "product_id": "chocolate_beans",
    }],
    "title": "transport, passenger car, electric"
}

const DEFAULTS = {
    NODE_WIDTH: 200,
    NODE_HEIGHT: 70,
    FONT: "16px sans-serif",
}


class Cartographer {
    data = {nodes: {}, edges: {}}

    constructor() {
        console.log("Initializing Cartographer")

        const panGroup = canvas.append("g")
            .attr("id", "pan-group")

        const zoom = d3.zoom()
            .scaleExtent([0.5, 5])
            .on("zoom", function() {
                panGroup.attr("transform", d3.event.transform);
            });

        canvas.call(zoom)

        const defaultTransform = d3.zoomIdentity.translate(50, 50);
        canvas.call(zoom.transform, defaultTransform);
    }

    renderGraph () {
        console.log("Rendering graph")

        graph = new dagre.graphlib
            .Graph({multigraph: true, compound: true})
            .setGraph({
                rankdir: "LR",
                ranker: "longest-path",
                ranksep: 100,
            });

        this.data.nodes.forEach(this.buildGraphNode);
        this.data.edges.forEach(this.buildGraphEdge);

        dagre.layout(graph)
        console.log(graph)

        const panGroup = canvas.select("#pan-group")
        panGroup.selectAll("*").remove() // clear old graph
        panGroup.call(dagreD3.render(), graph)

        graph.nodes().forEach(n => this.setupNode(graph.node(n)))
        graph.edges().forEach(n => this.setupEdge(graph.edge(n)))
    }

    // Allow update of graph by parsing a JSON document.
    update_graph (json_data) {
        console.log("Updating Graph");
        this.data = json_data;
        this.renderGraph();
    };

    buildGraphNode(node) {
        node.width = DEFAULTS.NODE_WIDTH
        node.height = DEFAULTS.NODE_HEIGHT + 25 * node.functions.length
        node.rank = 0

        if (node.functions.length === 0) {node.height = 25}

        node.paddingBottom = node.paddingTop = node.paddingLeft = node.paddingRight = 0

        graph.setNode(node.id, node);
    };

    buildGraphEdge(edge) {
        edge.curve = d3.curveBasis;
        graph.setEdge(edge['source_id'], edge['target_id'], edge);
    };

    setupNode(node){
        if(node.type === "expanded_node"){return this.setupExpandedNode(node)}
        if(node.type === "collapsed_function"){return this.setupCollapsedFunction(node)}
    }

    setupExpandedNode(node){
        const elem = d3.select(node.elem)

        elem.select(".label").remove()

        // Set the node title
        const lines = splitTextIntoLines(node.name, node.width - 8, DEFAULTS.FONT)

        lines.forEach((line, i) => {
            elem.append("text")
                .attr("x", node.width / -2 + 4)
                .attr("y", node.height / -2 + 18  + i * 20)
                .text(line);
        });

        // Set the title for each of the functions
        node.functions.forEach((fn, i) =>{
            const group = elem.append("g")
                .attr("id", fn.id)

            group.append("rect")
                .attr("width", node.width)
                .attr("height", 25)
                .attr("x", node.width / -2)
                .attr("y", (node.height / 2) - 25 * (i + 1))

            group.append("text")
                .attr("x", node.width / -2 + 4)
                .attr("y", (node.height / 2) - 25 * (i + 1) + 25 / 2 + 4)
                .text(fn.name)

            // style function box and outflows when hovering with mouse
            group.on("mouseenter", () => {
                const edgeIds = graph.nodeEdges(node.id)

                group.select("rect").style("fill", "red")

                edgeIds.forEach(e => {
                    const edge = graph.edge(e)
                    if(edge.function_id !== fn.id){return}
                    d3.select(edge.elem)
                        .style("fill", "red")
                        .style("stroke", "red")


                })
            })

            // reset style when leaving a function box with the mouse
            group.on("mouseleave", () => {
                group.select("rect").style("fill", null)

                const edgeIds = graph.edges()

                edgeIds.forEach(e => {
                    const edge = graph.edge(e)
                    d3.select(edge.elem)
                        .style("fill", null)
                        .style("stroke", null)


                })
            })
        })

        elem.on("contextmenu", ()=>{
            d3.event.preventDefault()
            window.backend.collapse_node(node.id.slice(2))
        })
    }

    setupCollapsedFunction(node){
        const elem = d3.select(node.elem)
        elem.select(".label").remove()

        elem.append("text")
            .attr("x", node.width / -2 + 4)
            .attr("y", node.height / -2 + 18)
            .text(node.name)

        elem.on("mouseenter", () => {
            const edgeIds = graph.nodeEdges(node.id)

            elem.select("rect").style("fill", "red")

            edgeIds.forEach(e => {
                const edge = graph.edge(e)
                if(edge.function_id !== node.id){return}
                d3.select(edge.elem)
                    .style("fill", "red")
                    .style("stroke", "red")


            })
        })
        elem.on("mouseleave", () => {
            elem.select("rect").style("fill", null)

            const edgeIds = graph.edges()

            edgeIds.forEach(e => {
                const edge = graph.edge(e)
                d3.select(edge.elem)
                    .style("fill", null)
                    .style("stroke", null)


            })
        })
        elem.on("click", () =>{
            window.backend.expand_node(node.id.slice(2))
        })
    }

    setupEdge(edge){
        const elem = d3.select(edge.elem)

        elem.on("mouseenter", ()=>{
            elem.style("fill", "red").style("stroke", "red")
            d3.select(`#${edge.function_id}`).select("rect").style("fill", "red")
        })

        elem.on("mouseleave", ()=>{
            elem.style("fill", null).style("stroke", null)
            d3.select(`#${edge.function_id}`).select("rect").style("fill", null)
        })
    }


}

function splitTextIntoLines(text, maxWidth, font) {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    context.font = font;

    const words = text.split(" ");
    let lines = [];
    let currentLine = words[0];

    for (let i = 1; i < words.length; i++) {
        const testLine = currentLine + " " + words[i];
        const metrics = context.measureText(testLine);

        if (metrics.width > maxWidth) {
            lines.push(currentLine);
            currentLine = words[i];
        } else {
            currentLine = testLine;
        }
    }
    lines.push(currentLine);
    return lines;
}

let graph
const canvas = d3.select("#canvas")
const carto = new Cartographer()

new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.bridge
    window.backend = channel.objects.backend

    window.bridge.update_graph.connect(json_data => carto.update_graph(JSON.parse(json_data)))
    window.bridge.is_ready()
})
//
// carto.update_graph(test_data)
