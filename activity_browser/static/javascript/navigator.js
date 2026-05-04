let is_sankey_mode = window.ab_sankey_mode || false;
let interactive = window.ab_interactive || false;
let graph_direction = window.ab_graph_direction || "BT";
let mode = is_sankey_mode ? "Sankey" : "Navigator";

console.log(`Starting ${mode}, interactive: ${interactive}`);

// SETUP GRAPH
// https://github.com/dagrejs/graphlib/wiki/API-Reference

const clamp = function (num, min, max) {
    return Math.min(Math.max(num, min), max);
};

const getGraphConfig = function () {
    return {
        rankdir: graph_direction,
    };
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
function abCreateSankeyPanMinimap(opts) {
    var innerWrapper = opts.innerWrapper;
    var panCanvas = opts.panCanvas;
    var zoomMain = opts.zoomMain;
    var getVpW = opts.getVpW;
    var getVpH = opts.getVpH;

    var MM_W = 200;
    var MM_H = 130;
    var INSET = 5;
    var clipId = "abSankeyPmClip_qwpyza";

    var lastMain = d3.zoomIdentity;
    var overviewOx = INSET + 2;
    var overviewOy = INSET + 2;
    var overviewSc = 0.12;

    var root = opts.svg.append("g").attr("class", "ab-sankey-pan-minimap");

    var defs = root.append("defs");
    defs.append("clipPath")
        .attr("id", clipId)
        .append("rect")
        .attr("x", INSET)
        .attr("y", INSET)
        .attr("width", MM_W - 2 * INSET)
        .attr("height", MM_H - 2 * INSET);

    root.append("rect")
        .attr("class", "ab-sankey-pm-chrome")
        .attr("rx", 5)
        .attr("ry", 5)
        .attr("fill", "rgba(255,255,255,0.96)")
        .attr("stroke", "#333")
        .attr("stroke-width", 2)
        .attr("pointer-events", "none")
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", MM_W)
        .attr("height", MM_H);

    var layer = root.append("g")
        .attr("clip-path", "url(#" + clipId + ")");

    var graphWrap = layer.append("g")
        .attr("class", "ab-sankey-pm-graph")
        .attr("pointer-events", "none");

    var viewport = layer.append("rect")
        .attr("class", "ab-sankey-pm-viewport")
        .attr("fill", "rgba(245, 245, 245, 0.1)")
        .attr("stroke", "#c62828")
        .attr("stroke-width", 2)
        .attr("pointer-events", "all")
        .attr("rx", 2)
        .attr("ry", 2);

    function toTr(t) {
        if (!t || typeof t.k !== "number") {
            return d3.zoomIdentity;
        }
        return d3.zoomIdentity.translate(t.x, t.y).scale(t.k);
    }

    function zoomMainTo(t) {
        zoomMain.transform(panCanvas, t);
        innerWrapper.property("__zoom", t);
        lastMain = t;
        updateViewportRect(t);
        if (opts.onHostTransform) {
            opts.onHostTransform(t);
        }
    }

    function graphToMm(gx, gy) {
        return [overviewOx + gx * overviewSc, overviewOy + gy * overviewSc];
    }

    function mmToGraph(mx, my) {
        return [(mx - overviewOx) / overviewSc, (my - overviewOy) / overviewSc];
    }

    function updateViewportRect(T) {
        lastMain = T;
        var tr = toTr(T);
        var W = getVpW();
        var H = getVpH();
        var corners = [[0, 0], [W, 0], [W, H], [0, H]];
        var mmPts = corners.map(function (c) {
            var g = tr.invert(c);
            return graphToMm(g[0], g[1]);
        });
        var xs = mmPts.map(function (p) {
            return p[0];
        });
        var ys = mmPts.map(function (p) {
            return p[1];
        });
        var x0 = Math.min.apply(null, xs);
        var x1 = Math.max.apply(null, xs);
        var y0 = Math.min.apply(null, ys);
        var y1 = Math.max.apply(null, ys);
        viewport
            .attr("x", x0)
            .attr("y", y0)
            .attr("width", Math.max(4, x1 - x0))
            .attr("height", Math.max(4, y1 - y0));
    }

    var drag = d3.drag()
        .on("drag", function () {
            var dgx = d3.event.dx / overviewSc;
            var dgy = d3.event.dy / overviewSc;
            var tr = toTr(lastMain);
            var Tn = d3.zoomIdentity.translate(tr.x - dgx * tr.k, tr.y - dgy * tr.k).scale(tr.k);
            zoomMainTo(Tn);
        });

    viewport.call(drag);

    function wheelHandler(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var tr = toTr(lastMain);
        var pt = d3.mouse(layer.node());
        var gxy = mmToGraph(pt[0], pt[1]);
        var focal = tr.apply(gxy);
        var factor = ev.deltaY > 0 ? 0.92 : 1.08;
        var kNew = clamp(tr.k * factor, 0.25, 5);
        if (Math.abs(kNew - tr.k) < 1e-6) {
            return;
        }
        var fk = kNew / tr.k;
        var Tn = d3.zoomIdentity.translate(
            focal[0] + (tr.x - focal[0]) * fk,
            focal[1] + (tr.y - focal[1]) * fk
        ).scale(kNew);
        zoomMainTo(Tn);
    }

    layer.node().addEventListener("wheel", wheelHandler, { passive: false });

    function positionRoot(vh) {
        root.attr("transform", "translate(" + INSET + "," + (vh - MM_H - INSET) + ")");
    }

    function refreshGraphClone() {
        graphWrap.selectAll(".ab-sankey-pm-clone").remove();
        var node = panCanvas.node().cloneNode(true);
        node.removeAttribute("id");
        graphWrap.node().appendChild(node);
        d3.select(node).attr("class", "ab-sankey-pm-clone panCanvas").attr("transform", null);
        var bb = graphWrap.node().getBBox();
        var innerW = MM_W - 2 * INSET - 4;
        var innerH = MM_H - 2 * INSET - 4;
        var sx = innerW / Math.max(bb.width, 80);
        var sy = innerH / Math.max(bb.height, 60);
        overviewSc = Math.min(sx, sy, 0.28);
        overviewOx = INSET + 2 - bb.x * overviewSc;
        overviewOy = INSET + 2 - bb.y * overviewSc;
        graphWrap.attr("transform", "translate(" + overviewOx + "," + overviewOy + ") scale(" + overviewSc + ")");
        updateViewportRect(lastMain);
    }

    return {
        resize: function (vh) {
            positionRoot(vh);
        },
        onMainZoom: function (t) {
            updateViewportRect(t || d3.zoomIdentity);
        },
        refresh: refreshGraphClone,
        setVisible: function (on) {
            root.style("display", on ? null : "none");
        }
    };
}

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

        var zoomHandler = function () {
            var t = d3.event.transform;
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
                sankeyPanMinimap.setVisible(window.ab_show_sankey_minimap !== false);
            }
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
            zoom.transform(panCanvas, minimapZoomTransform);
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
function wrapWordsToMaxLineLength(str, maxLen) {
    if (!str) {
        return "";
    }
    str = String(str).replace(/\s+/g, " ").trim();
    if (maxLen < 6 || str.length <= maxLen) {
        return str;
    }
    var lines = [];
    var pos = 0;
    while (pos < str.length) {
        var end = Math.min(pos + maxLen, str.length);
        if (end >= str.length) {
            lines.push(str.slice(pos).trim());
            break;
        }
        var chunk = str.slice(pos, end);
        var lastSpace = chunk.lastIndexOf(" ");
        var cut = lastSpace > 0 ? lastSpace : maxLen;
        lines.push(str.slice(pos, pos + cut).trim());
        pos += cut;
        while (pos < str.length && str[pos] === " ") {
            pos++;
        }
    }
    return lines.join("\n");
}

function wrapSankeyEdgeLabelMultiline(text, maxLen) {
    if (!text) {
        return "";
    }
    return text.split("\n").map(function (ln) {
        return wrapWordsToMaxLineLength(ln, maxLen);
    }).join("\n");
}

/**
 * Edge label from toggles: Flows (product name), impacts absolute / relative (any subset).
 */
function formatSankeyTwoLineEdgeLabel(e) {
    /* Default on when unset (before wire runs or old HTML without toggles). */
    var showFlows = window.ab_sankey_show_flows !== false;
    var showAbs = window.ab_sankey_impact_absolute !== false;
    var showRel = window.ab_sankey_impact_relative !== false;
    var flow = (e.product || "").trim();
    var lines = [];
    if (showFlows && flow) {
        lines.push(flow);
    }
    var impactLines = [];
    if (e.impact_cumulative != null && e.impact_unit != null) {
        if (showAbs) {
            var x = Number(e.impact_cumulative);
            impactLines.push((Math.round(x * 1000) / 1000) + " " + e.impact_unit);
        }
        if (showRel) {
            var pctRaw = e.impact_pct_total != null ? Number(e.impact_pct_total) : 0;
            if (!isFinite(pctRaw)) {
                pctRaw = 0;
            }
            impactLines.push((Math.round(pctRaw * 10) / 10) + "%");
        }
    } else if (showAbs || showRel) {
        if (e._sankeyScoreLabel == null && typeof e.label === "string") {
            e._sankeyScoreLabel = e.label;
        }
        var fb = e._sankeyScoreLabel || "";
        if (fb) {
            impactLines.push(fb);
        }
    }
    var impactBlock = impactLines.join("\n");
    if (lines.length && impactBlock) {
        return lines[0] + "\n" + impactBlock;
    }
    if (lines.length) {
        return lines[0];
    }
    if (impactBlock) {
        return impactBlock;
    }
    return " ";
}

function inferSankeyEdgeLabelMaxCols(parsed) {
    if (!parsed || !parsed.nodes || !parsed.nodes.length) {
        return 12;
    }
    var maxFirst = 10;
    parsed.nodes.forEach(function (nd) {
        var lab = nd.label != null ? String(nd.label) : "";
        var nm = nd.name != null ? String(nd.name) : "";
        var first = lab.split("\n")[0] || "";
        var halfName = Math.ceil(nm.length / 2) || 0;
        maxFirst = Math.max(maxFirst, first.length, Math.min(30, halfName));
    });
    return Math.max(8, Math.min(22, maxFirst + 2));
}

/** Sankey node process name is capped to this many wrapped rows. */
var AB_SANKEY_NODE_NAME_MAX_ROWS = 2;
/** Sankey process node inner rectangle height is fixed; width adapts and is clamped to 1:1..3:1. */
var AB_SANKEY_NODE_MIN_ASPECT = 1;
var AB_SANKEY_NODE_MAX_ASPECT = 3;
/** Inner height (px) before padding. */
var AB_SANKEY_NODE_INNER_HEIGHT_PX = 50;
var AB_SANKEY_NODE_INNER_MIN_WIDTH_PX = Math.round(AB_SANKEY_NODE_INNER_HEIGHT_PX * AB_SANKEY_NODE_MIN_ASPECT);
var AB_SANKEY_NODE_INNER_MAX_WIDTH_PX = Math.round(AB_SANKEY_NODE_INNER_HEIGHT_PX * AB_SANKEY_NODE_MAX_ASPECT);
/** Approximate glyph width for node labels; used for width and wrap heuristics. */
var AB_SANKEY_NODE_CHAR_PX = 5;
/** Keep text 6px from node boundaries. */
var AB_SANKEY_NODE_PADDING_X = 6;
var AB_SANKEY_NODE_PADDING_Y = 6;

function inferSankeyNodeInnerWidthPx(n) {
    var nameLines = buildSankeyProcessNameLines(String(n.name != null ? n.name : "(unnamed)"));
    var maxLineLen = nameLines.reduce(function (mx, ln) {
        return Math.max(mx, ln.length);
    }, 8);
    var targetCols = Math.max(8, maxLineLen);
    var desired = Math.round(targetCols * AB_SANKEY_NODE_CHAR_PX + 12);
    return clamp(desired, AB_SANKEY_NODE_INNER_MIN_WIDTH_PX, AB_SANKEY_NODE_INNER_MAX_WIDTH_PX);
}

function inferSankeyNodeWrapColsFromWidth(innerWidthPx) {
    var usable = Math.max(8, innerWidthPx - 12);
    return clamp(Math.floor(usable / AB_SANKEY_NODE_CHAR_PX), 8, 36);
}

function sankeyNameMaxColsAt3to1() {
    return inferSankeyNodeWrapColsFromWidth(AB_SANKEY_NODE_INNER_MAX_WIDTH_PX);
}

function truncateSankeyNameToTwoRowsBudget(text, maxCols) {
    var maxChars = Math.max(8, maxCols * AB_SANKEY_NODE_NAME_MAX_ROWS);
    if (text.length <= maxChars) {
        return text;
    }
    return text.slice(0, Math.max(1, maxChars - 3)).replace(/[. ]+$/, "") + "...";
}

/** Whole-word split into up to two rows, balanced as evenly as possible. */
function splitSankeyNameEvenlyTwoRows(text, maxCols) {
    var words = text.split(" ").filter(function (w) { return w.length > 0; });
    if (!words.length) {
        return ["(unnamed)"];
    }
    if (words.length === 1) {
        if (words[0].length <= maxCols) {
            return [words[0]];
        }
        return [words[0].slice(0, Math.max(1, maxCols - 3)) + "..."];
    }

    var bestIdx = 1;
    var bestScore = Number.POSITIVE_INFINITY;
    for (var i = 1; i < words.length; i++) {
        var l1 = words.slice(0, i).join(" ");
        var l2 = words.slice(i).join(" ");
        var overflow = Math.max(0, l1.length - maxCols) + Math.max(0, l2.length - maxCols);
        var balance = Math.abs(l1.length - l2.length);
        var score = overflow * 1000 + balance;
        if (score < bestScore) {
            bestScore = score;
            bestIdx = i;
        }
    }

    var line1 = words.slice(0, bestIdx).join(" ").trim();
    var line2 = words.slice(bestIdx).join(" ").trim();

    if (line1.length > maxCols) {
        var c1 = line1.lastIndexOf(" ", maxCols);
        var head1;
        var tailFromL1;
        if (c1 > 0) {
            head1 = line1.slice(0, c1).trim();
            tailFromL1 = line1.slice(c1 + 1).trim();
        } else {
            head1 = line1.slice(0, maxCols).trim();
            tailFromL1 = line1.slice(maxCols).trim();
        }
        line1 = head1;
        if (tailFromL1) {
            line2 = (tailFromL1 + (line2 ? " " + line2 : "")).trim();
        }
    }
    if (line2.length > maxCols) {
        var c2 = line2.lastIndexOf(" ", Math.max(1, maxCols - 3));
        if (c2 > 0) {
            line2 = line2.slice(0, c2).trim().replace(/[. ]+$/, "") + "...";
        } else {
            line2 = line2.slice(0, Math.max(1, maxCols - 3)).replace(/[. ]+$/, "") + "...";
        }
    }
    return line2 ? [line1, line2] : [line1];
}

/** Build process-name lines from a strict 2-row budget at 3:1 max ratio. */
function buildSankeyProcessNameLines(rawName) {
    var text = String(rawName || "").replace(/\s+/g, " ").trim();
    if (!text) {
        return ["(unnamed)"];
    }
    var maxCols = sankeyNameMaxColsAt3to1();
    var trimmed = truncateSankeyNameToTwoRowsBudget(text, maxCols);
    return splitSankeyNameEvenlyTwoRows(trimmed, maxCols);
}

/** Sankey node label as plain text (SVG tspans). */
function formatSankeyNodePlainTextLabel(n, wrapCols) {
    var rawName = String(n.name != null ? n.name : "(unnamed)");
    var nameLines = buildSankeyProcessNameLines(rawName)
        .map(function (x) { return x.trim(); })
        .filter(function (x) { return x.length > 0; });
    if (!nameLines.length) {
        nameLines = ["(unnamed)"];
    }

    var loc = String(n.location != null ? n.location : "").trim();
    var lines = nameLines.slice();
    if (loc) {
        lines.push(loc);
    }

    var pctStr = "";
    if (n.direct_emissions_score_normalized != null) {
        var p = Number(n.direct_emissions_score_normalized);
        if (isFinite(p)) {
            pctStr = String(Math.round(p * 10000) / 100) + "%";
        }
    }
    if (pctStr) {
        lines.push(pctStr);
    }
    return lines.join("\n");
}


/** GRAPH **/
const cartographer = function () {
    let data;
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

        // add node selection items
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

        // Adds click listener, calling handleMouseClick func
        var nodes = panCanvas.selectAll("g .node").data(graph.nodes());
        nodes.on("click", handleMouseClick)

        if (is_sankey_mode) {
            nodes.on("mouseover", handleMouseOverNode)
            nodes.on("mouseout", handleMouseOutNode);

            // change node fill based on impact
            panCanvas.selectAll("g .node rect")
                .style("fill", function (d) {
                    // console.log(color(graph.node(d).direct_emissions_score_normalized));
                    return color(graph.node(d).direct_emissions_score_normalized);
                });
        }

        // listener for mouse-hovers
        var edges = panCanvas.selectAll("g .edgePath")
            .on("mouseover", handleMouseOverEdge)
            .on("mouseout", function (d) {
                div.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        if (is_sankey_mode) {
            edges.attr("stroke-width", function (d) {
                return (graph.edge(d) || {weight: 1}).weight;
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

        if (renderOptions.center) {
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
        data = JSON.parse(json_data);
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

        // edges --> graph
        data.edges.forEach(buildGraphEdge);
        console.log("Edges successfully loaded...")
        cartographer.renderGraph({center: true});
    };

    cartographer.applySankeyEdgeLabels = function () {
        if (!is_sankey_mode || typeof data === "undefined" || !data || !data.edges) {
            return;
        }
        data.edges.forEach(buildGraphEdge);
        cartographer.renderGraph({ center: false });
    };

    const buildGraphNode = function (n) {
        if (!is_sankey_mode) {
            n.label = formatNodeText(n['name'], n['location']);
            n.labelType = "html";
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
        if (interactive) {
            n.expanded = n['expanded']
            n.collapsed = false;
        }
        graph.setNode(n['id'], n);
    };

    const buildGraphEdge = function (e) {
        e.curve = d3.curveBasis;

        if (!is_sankey_mode) {
            e.label = formatEdgeText(e['product'], max_string_length);
            e.labelType = "html";
            e.arrowhead = "vee";
        } else {
            /* Sankey: plain-text labels only (see formatSankeyTwoLineEdgeLabel). */
            var joinLabel = formatSankeyTwoLineEdgeLabel(e);
            var wrapCols = (data && data._sankeyEdgeWrapCols) ? data._sankeyEdgeWrapCols : 12;
            e.label = wrapSankeyEdgeLabelMultiline(joinLabel, wrapCols);
            delete e.labelType;
            delete e.arrowhead;
        }

        graph.setEdge(e['source_id'], e['target_id'], e);
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
    const handleMouseClick = function (node) {
        // make dictionary containing the node key and how the user clicked on it
        // see also mouse events: https://www.w3schools.com/jsref/obj_mouseevent.asp
        let gNode = graph.node(node)
        let click_dict = {
            "database": gNode.database,
            "id": gNode.id,
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

    const handleMouseOverNode = function (n) {
        node = graph.node(n);
        d3.select(node.elem)
            .style("opacity", .4);
        div.transition()
            .duration(200)
            .style("opacity", .9);
        div.html(node.tooltip)
            .style("left", (d3.event.pageX) + "px")
            .style("top", (d3.event.pageY - 28) + "px");
    };

    const handleMouseOutNode = function (n) {
        node = graph.node(n);
        d3.select(node.elem)
            .style("opacity", 1);
        div.transition()
            .duration(500)
            .style("opacity", 0);
    }

    const handleMouseOverEdge = function (e) {
        edge = graph.edge(e);
        div.transition()
            .duration(200)
            .style("opacity", .9);
        div.html(edge.tooltip)
            .style("left", (d3.event.pageX) + "px")
            .style("top", (d3.event.pageY - 28) + "px");
    };
};


/** RUN SCRIPT **/

//instantiation of canvas container+reset button
var canvas = d3.demo.canvas();
d3.select("#canvasqPWKOg").call(canvas);

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

d3.select("#downloadSVGtButtonqPWKOg").on("click", function () {

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
})();

/* END OF ADAPTED DEMO SCRIPT*/

/**
 * Build svg container and listen for zoom and drag calls
 */


// Tooltip: http://bl.ocks.org/d3noob/a22c42db65eb00d4e369
var div = d3.select("#canvasqPWKOg").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

var color = d3.scaleLinear()
    .domain([-99999999, -1, 0, 1, 99999999])
    .range(["green", "green", "white", "red", "red"]);

var nodeSelection = d3.select("select#nodeSelectPWK0g")

d3.select("#nodeSelectPWK0gExecute").on("click", function () {
    var selectedId = d3.select("#nodeSelectPWK0g").property("value");
    canvas.zoomToNode(selectedId, {scale: 1.5});
})

// break strings into multiple lines after certain length if necessary
function wrapText(str, length) {
    return str.replace(/.{15}\S*\s+/g, "$&@").split(/\s+@/).join(is_sankey_mode ? "\n" : "<br>")
}

function roundNumber(number) {
    return number.toPrecision(3)
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
