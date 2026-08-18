/* Tree-plot node-link renderer. Uses Sankey visual grammar (sankey_graph_style.js).
 * Consumes ``d3_graph_payload`` JSON. Does not recompute adjust policy.
 */
(function (global) {
    "use strict";

    function boxFill(d, colorBy, ordinal) {
        if (colorBy && colorBy !== "direct" && d.color_key) {
            return ordinal(d.color_key);
        }
        var pct = d.direct_pct;
        if (pct == null && d.direct_emissions_score_normalized != null) {
            pct = Number(d.direct_emissions_score_normalized) * 100;
        }
        var dark = typeof global.abGraphIsDark === "function" && global.abGraphIsDark();
        return global.abDirectImpactFill(pct || 0, dark);
    }

    function showTriangle(d) {
        return !d.is_aggregate && (d.has_hidden_suppliers || d.can_collapse);
    }

    function nodeLabelText(n) {
        var rec = {
            name: n.is_aggregate && n.aggregate_key ? n.aggregate_key : n.name,
            location: n.location,
            direct_emissions_score_normalized: n.direct_emissions_score_normalized,
            direct_pct: n.direct_pct,
        };
        if (typeof global.formatSankeyNodePlainTextLabel === "function") {
            var innerWidth = global.inferSankeyNodeInnerWidthPx(rec);
            var wrapCols = global.inferSankeyNodeWrapColsFromWidth(innerWidth);
            return global.formatSankeyNodePlainTextLabel(rec, wrapCols);
        }
        var lines = [rec.name || " "];
        if (rec.location) {
            lines.push(String(rec.location));
        }
        if (n.direct_pct != null && isFinite(n.direct_pct)) {
            lines.push((Math.round(n.direct_pct * 100) / 100) + "%");
        }
        return lines.join("\n");
    }

    function edgeClass(e) {
        if (e.class === "benefit" || e.class === "impact") {
            return e.class;
        }
        return (e.path_sign || 0) < 0 ? "benefit" : "impact";
    }

    function edgeLabelBox(label) {
        var lines = String(label || "").split("\n").filter(Boolean);
        if (!lines.length) {
            return { width: 0, height: 0 };
        }
        var maxC = 0;
        lines.forEach(function (ln) { maxC = Math.max(maxC, ln.length); });
        return {
            width: Math.max(24, maxC * 6.6),
            height: Math.max(14, lines.length * 13 + 4),
        };
    }

    function edgeLabelAnchor(ed) {
        if (ed && ed.x != null && ed.y != null && isFinite(ed.x) && isFinite(ed.y)) {
            return { x: ed.x, y: ed.y };
        }
        var pts = (ed && ed.points) || [];
        if (pts.length >= 2) {
            var a = pts[0];
            var b = pts[pts.length - 1];
            return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        }
        return pts[0] || { x: 0, y: 0 };
    }

    global.abDrawContributionGraph = function (svg, payload, opts) {
        opts = opts || {};
        var nodes = payload.nodes || [];
        var edges = payload.edges || [];
        var colorBy = payload.color_by || "direct";
        var unit = payload.unit || "";
        var keys = nodes.map(function (n) { return n.color_key; }).filter(Boolean);
        var ordinal = typeof global.abOrdinalScale === "function"
            ? global.abOrdinalScale(keys)
            : d3.scaleOrdinal(d3.schemeTableau10).domain(Array.from(new Set(keys)));

        global.ab_sankey_show_flows = opts.flows !== false;
        global.ab_sankey_impact_absolute = opts.abs !== false;
        global.ab_sankey_impact_relative = opts.rel !== false;

        var wrapCols = 12;
        if (typeof global.inferSankeyEdgeLabelMaxCols === "function") {
            wrapCols = global.inferSankeyEdgeLabelMaxCols({ nodes: nodes });
        }

        var graphCfg = {
            rankdir: typeof global.abNormalizeRankdir === "function"
                ? global.abNormalizeRankdir(opts.rankdir)
                : (opts.rankdir === "BT" ? "BT" : "RL"),
            ranksep: (opts.rankdir === "LR" || opts.rankdir === "RL") ? 44 : 36,
            nodesep: 18,
        };
        if (nodes.length >= 80) {
            graphCfg.ranker = "tight-tree";
        }
        var Graph = (typeof dagre !== "undefined" && dagre.graphlib)
            ? dagre.graphlib.Graph
            : dagreD3.graphlib.Graph;
        var g = new Graph({ multigraph: true }).setGraph(graphCfg);

        var padX = global.AB_SANKEY_NODE_PADDING_X || 6;
        var padY = global.AB_SANKEY_NODE_PADDING_Y || 6;
        var innerH = global.AB_SANKEY_NODE_INNER_HEIGHT_PX || 50;

        nodes.forEach(function (n) {
            var rec = {
                name: n.is_aggregate && n.aggregate_key ? n.aggregate_key : n.name,
                location: n.location,
            };
            var innerWidth = typeof global.inferSankeyNodeInnerWidthPx === "function"
                ? global.inferSankeyNodeInnerWidthPx(rec)
                : 80;
            g.setNode(String(n.id), {
                label: nodeLabelText(n),
                data: n,
                class: n.class || "production",
                width: innerWidth + 2 * padX,
                height: innerH + 2 * padY,
            });
        });
        var demandIds = typeof global.abDemandIdSet === "function"
            ? global.abDemandIdSet(nodes)
            : {};
        edges.forEach(function (e, i) {
            var layoutW = typeof global.abLayoutEdgeWeight === "function"
                ? global.abLayoutEdgeWeight(e, demandIds)
                : (e.weight || 1);
            var joinLabel = typeof global.formatSankeyTwoLineEdgeLabel === "function"
                ? global.formatSankeyTwoLineEdgeLabel(e)
                : "";
            var label = typeof global.wrapSankeyEdgeLabelMultiline === "function"
                ? global.wrapSankeyEdgeLabelMultiline(joinLabel, wrapCols)
                : joinLabel;
            var box = edgeLabelBox(label);
            g.setEdge(String(e.source_id), String(e.target_id), {
                data: e,
                weight: layoutW,
                class: edgeClass(e),
                label: label,
                width: box.width,
                height: box.height,
                labelpos: "c",
            }, "e" + i);
        });

        var svgW = +svg.attr("width") || 800;
        var svgH = +svg.attr("height") || 500;
        var inner = svg.append("g").attr("class", "output panCanvas ct-graph-inner");
        var t0 = performance.now();
        dagre.layout(g);
        var layoutMs = performance.now() - t0;
        t0 = performance.now();

        var line = d3.line()
            .x(function (p) { return p.x; })
            .y(function (p) { return p.y; })
            .curve(d3.curveBasis);

        g.edges().forEach(function (e) {
            var ed = g.edge(e);
            var data = ed.data || {};
            var eg = inner.append("g")
                .datum(e)
                .attr("class", "edgePath " + (ed.class || edgeClass(data)));
            eg.append("path")
                .attr("class", "path")
                .attr("d", line(ed.points || []))
                .attr("fill", "none")
                .attr("stroke-width", typeof global.abEdgeStrokeWidth === "function"
                    ? global.abEdgeStrokeWidth(data.weight)
                    : Math.max(1, data.weight || 0));
        });

        g.nodes().forEach(function (id) {
            var n = g.node(id);
            var data = n.data || {};
            var ng = inner.append("g")
                .datum(id)
                .attr("class", "node " + (n.class || "production")
                    + ((data.class || n.class) === "demand" ? " demand" : ""))
                .attr("transform", "translate(" + n.x + "," + n.y + ")");
            ng.append("rect")
                .attr("x", -n.width / 2)
                .attr("y", -n.height / 2)
                .attr("width", n.width)
                .attr("height", n.height)
                .attr("rx", 2)
                .attr("ry", 2)
                .style("fill", boxFill(data, colorBy, ordinal));
            var text = ng.append("text")
                .attr("text-anchor", "middle")
                .attr("dominant-baseline", "middle");
            String(n.label || " ").split("\n").forEach(function (lineText, i, arr) {
                text.append("tspan")
                    .attr("x", 0)
                    .attr("dy", i === 0 ? ((1 - arr.length) * 0.55 + 0.35) + "em" : "1.1em")
                    .text(lineText);
            });
            if (showTriangle(data)) {
                var dir = typeof global.abNormalizeRankdir === "function"
                    ? global.abNormalizeRankdir(opts.rankdir)
                    : (opts.rankdir === "BT" ? "BT" : "RL");
                var h = n.height || 50;
                var w = n.width || 80;
                var tri = "translate(0, " + (h / 2) + ") rotate(180)";
                if (dir === "RL") {
                    tri = "translate(" + (w / 2) + ", 0) rotate(90)";
                }
                ng.append("path")
                    .attr("class", "triangle")
                    .attr("d", d3.symbol().type(d3.symbolTriangle).size(36))
                    .attr("transform", tri)
                    .style("pointer-events", "none");
            }
        });

        g.edges().forEach(function (e) {
            var ed = g.edge(e);
            var data = ed.data || {};
            var joinLabel = typeof global.formatSankeyTwoLineEdgeLabel === "function"
                ? global.formatSankeyTwoLineEdgeLabel(data)
                : "";
            var label = typeof global.wrapSankeyEdgeLabelMultiline === "function"
                ? global.wrapSankeyEdgeLabelMultiline(joinLabel, wrapCols)
                : joinLabel;
            ed.label = label;
            if (!label) {
                return;
            }
            var mid = edgeLabelAnchor(ed);
            var lines = String(label).split("\n");
            var lg = inner.append("g")
                .datum(e)
                .attr("class", "edgeLabel")
                .attr("transform", "translate(" + mid.x + "," + mid.y + ")");
            var text = lg.append("text")
                .attr("text-anchor", "middle")
                .attr("dominant-baseline", "middle");
            lines.forEach(function (lineText, i, arr) {
                text.append("tspan")
                    .attr("xml:space", "preserve")
                    .attr("x", 0)
                    .attr("dy", i === 0 ? ((1 - arr.length) * 0.55) + "em" : "1.1em")
                    .text(lineText);
            });
        });

        inner.on("click", function (event) {
            var nodeEl = event.target.closest("g.node");
            if (!nodeEl) {
                return;
            }
            var n = g.node(d3.select(nodeEl).datum());
            var data = (n && n.data) || {};
            if (window.bridge && typeof window.bridge.click_segment === "function") {
                window.bridge.click_segment(data.click_uid);
            }
        });
        inner.on("contextmenu", function (event) {
            event.preventDefault();
            event.stopPropagation();
            var nodeEl = event.target.closest("g.node");
            if (!nodeEl) {
                return;
            }
            d3.select("#tooltip").attr("hidden", "hidden");
            var n = g.node(d3.select(nodeEl).datum());
            var data = (n && n.data) || {};
            if (window.bridge && typeof window.bridge.context_segment === "function") {
                var payload = (typeof global.abOpenProcessPayload === "function")
                    ? global.abOpenProcessPayload(data)
                    : {
                        visit_id: data.visit_id != null ? data.visit_id : data.id,
                        unique_id: data.visit_id != null ? data.visit_id : data.id,
                        activity_id: data.activity_id,
                        database: data.database || "",
                        code: data.code || "",
                        is_aggregate: !!data.is_aggregate,
                        constituent_uids: data.constituent_uids || [],
                        mouse: 2
                    };
                window.bridge.context_segment(JSON.stringify(payload));
            }
        });
        inner.on("mousemove", function (event) {
            var nodeEl = event.target.closest("g.node");
            var edgeEl = event.target.closest("g.edgePath, g.edgeLabel");
            var tip = d3.select("#tooltip");
            var html = "";
            if (nodeEl) {
                var n = g.node(d3.select(nodeEl).datum());
                var data = (n && n.data) || {};
                html = typeof global.abContributionTooltipHtml === "function"
                    ? global.abContributionTooltipHtml(data, unit)
                    : (data.tooltip || "");
            } else if (edgeEl) {
                var ed = g.edge(d3.select(edgeEl).datum());
                var edgeData = (ed && ed.data) || ed || {};
                html = typeof global.buildSankeyEdgeTooltipHtml === "function"
                    ? global.buildSankeyEdgeTooltipHtml(edgeData)
                    : (edgeData.tooltip || "");
            } else {
                tip.attr("hidden", "hidden");
                return;
            }
            if (typeof global.abPlaceHtmlTooltip === "function") {
                global.abPlaceHtmlTooltip(tip, event, html);
            } else {
                tip.attr("hidden", null)
                    .html(html)
                    .style("left", (event.pageX + 12) + "px")
                    .style("top", (event.pageY + 12) + "px");
            }
        });
        inner.on("mouseleave", function () {
            d3.select("#tooltip").attr("hidden", "hidden");
        });
        var drawMs = performance.now() - t0;

        var graphW = g.graph().width || 1;
        var graphH = g.graph().height || 1;
        var scale = Math.min(1, (svgW * 0.92) / graphW, (svgH * 0.88) / graphH);
        scale = Math.max(0.25, scale);
        var tx = (svgW - graphW * scale) / 2;
        var ty = (svgH - graphH * scale) / 2 + 8;
        var initial = d3.zoomIdentity.translate(tx, ty).scale(scale);
        if (opts.restoreTransform && opts.restoreTransform.k) {
            initial = opts.restoreTransform;
        }

        var minimap = null;
        var zoom = d3.zoom().scaleExtent([0.25, 5]).on("zoom", function (event) {
            inner.attr("transform", event.transform);
            var stNow = svg.property("_ctGraphState");
            if (!(stNow && stNow.fitting)) {
                global.abContributionGraphUserZoomed = true;
            }
            if (minimap) {
                minimap.onMainZoom(event.transform);
            }
        });
        svg.property("_ctGraphState", {
            g: g,
            inner: inner,
            zoom: zoom,
            graphW: graphW,
            graphH: graphH,
            wrapCols: wrapCols,
            fitting: true,
        });
        svg.call(zoom);
        svg.call(zoom.transform, initial);
        svg.property("_ctGraphState").fitting = false;
        if (opts.restoreTransform) {
            global.abContributionGraphUserZoomed = true;
        }
        global.abLastGraphProfile = {
            layoutMs: layoutMs,
            drawMs: drawMs,
            dagreMs: layoutMs + drawMs,
            nNodes: nodes.length,
            nEdges: edges.length
        };

        if (opts.minimap && typeof global.abCreateSankeyPanMinimap === "function") {
            minimap = global.abCreateSankeyPanMinimap({
                svg: svg,
                innerWrapper: svg,
                panCanvas: inner,
                zoomMain: {
                    transform: function (_sel, t) {
                        svg.call(zoom.transform, t);
                    },
                },
                getVpW: function () { return svgW; },
                getVpH: function () { return svgH; },
            });
            minimap.resize(svgH);
            minimap.onMainZoom(initial);
            setTimeout(function () {
                if (minimap) {
                    minimap.refresh();
                }
            }, 40);
        }
    };

    global.abApplyContributionGraphEdgeLabels = function (svgSel, opts) {
        opts = opts || {};
        var st = svgSel.property("_ctGraphState");
        if (!st || !st.g || !st.inner || !st.inner.node() || !st.inner.node().isConnected) {
            return false;
        }
        global.ab_sankey_show_flows = opts.flows !== false;
        global.ab_sankey_impact_absolute = opts.abs !== false;
        global.ab_sankey_impact_relative = opts.rel !== false;
        var wrapCols = st.wrapCols || 12;
        st.g.edges().forEach(function (e) {
            var ed = st.g.edge(e);
            var data = ed.data || {};
            var joinLabel = typeof global.formatSankeyTwoLineEdgeLabel === "function"
                ? global.formatSankeyTwoLineEdgeLabel(data)
                : "";
            ed.label = typeof global.wrapSankeyEdgeLabelMultiline === "function"
                ? global.wrapSankeyEdgeLabelMultiline(joinLabel, wrapCols)
                : joinLabel;
        });
        st.inner.selectAll("g.edgeLabel text").each(function (e) {
            var ed = st.g.edge(e);
            var lines = String((ed && ed.label) || " ").split("\n");
            var text = d3.select(this);
            var tspans = text.selectAll("tspan").data(lines);
            tspans.exit().remove();
            tspans.enter().append("tspan")
                .attr("xml:space", "preserve")
                .attr("x", 0);
            text.selectAll("tspan")
                .attr("x", 0)
                .attr("dy", function (_, i) {
                    return i === 0 ? ((1 - lines.length) * 0.55) + "em" : "1.1em";
                })
                .text(function (d) { return d; });
        });
        return true;
    };

    global.abFitContributionGraph = function (svgSel, width, height) {
        var st = svgSel.property("_ctGraphState");
        if (!st || !st.zoom || !st.graphW || !st.graphH) {
            return false;
        }
        svgSel.attr("width", width).attr("height", height);
        st.fitting = true;
        var scale = Math.min(1, (width * 0.92) / st.graphW, (height * 0.88) / st.graphH);
        scale = Math.max(0.25, scale);
        var tx = (width - st.graphW * scale) / 2;
        var ty = (height - st.graphH * scale) / 2 + 8;
        svgSel.call(st.zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
        st.fitting = false;
        return true;
    };
})(window);
