(function (global) {
    "use strict";

    window.ab_sankey_show_flows = true;
    window.ab_sankey_impact_absolute = false;
    window.ab_sankey_impact_relative = false;

    const canvas = d3.select("#canvas");
    let payload = { nodes: [], edges: [] };
    let zoomBehavior = null;
    let panGroup = null;
    let dagreGraph = null;
    const dagreRender = (typeof dagreD3 !== "undefined" && dagreD3.render)
        ? dagreD3.render()
        : null;

    const DOT_R = 3.5;
    const NODE_W = 152;
    const NODE_H = 52;
    const NODE_LABEL_PAD = 2;
    const NODE_FONT = "12px sans-serif";
    const STUB_LEN = 90;
    const STUB_LINE_PX = 13;

    function formatAmount(amt) {
        const n = Number(amt);
        if (!isFinite(n)) {
            return "";
        }
        const a = Math.abs(n);
        if (a === 0) {
            return "0";
        }
        if (a < 0.01) {
            return n.toExponential(2)
                .replace(/(\.\d*?)0+e/, function (_, frac) {
                    return (frac === "." ? "" : frac) + "e";
                })
                .replace(/\.e/, "e");
        }
        let decimals = 4;
        if (a >= 100) {
            decimals = 2;
        } else if (a >= 1) {
            decimals = 3;
        }
        return n.toFixed(decimals).replace(/\.?0+$/, "");
    }

    function flowLabel(e) {
        const lines = [];
        if (e.product) {
            lines.push(String(e.product));
        }
        if (e.amount != null) {
            lines.push([formatAmount(e.amount), e.unit || ""].filter(Boolean).join(" "));
        } else if (e.unit) {
            lines.push(String(e.unit));
        }
        return lines.join("\n");
    }

    function wrapLabel(label, wrapCols) {
        const parts = String(label || "").split("\n");
        const product = (parts[0] || "").trim();
        const rest = parts.slice(1).filter(function (ln) { return String(ln).trim(); });
        let productWrapped = product;
        if (product && typeof global.wrapSankeyEdgeLabelMultiline === "function") {
            productWrapped = global.wrapSankeyEdgeLabelMultiline(product, wrapCols);
        }
        return [productWrapped].concat(rest).filter(Boolean).join("\n");
    }

    function sameProduct(a, b) {
        return a && b && a.product === b.product && a.unit === b.unit;
    }

    function flowDatum(el) {
        const raw = d3.select(el).datum();
        if (raw && raw.product != null) {
            return raw;
        }
        const ed = dagreGraph ? (dagreGraph.edge(raw) || {}) : {};
        return ed.data || ed;
    }

    function setSameProductHot(data) {
        panGroup.selectAll("g.edgePath").classed("hot", function () {
            return sameProduct(flowDatum(this), data);
        });
    }

    let measureCtx = null;

    function nodeLabelMaxPx() {
        return Math.max(8, NODE_W - NODE_LABEL_PAD * 2);
    }

    function measureLabel(text) {
        if (!measureCtx) {
            measureCtx = document.createElement("canvas").getContext("2d");
        }
        if (!measureCtx) {
            return String(text || "").length * 6;
        }
        measureCtx.font = NODE_FONT;
        return measureCtx.measureText(String(text || "")).width;
    }

    function truncToWidth(text, maxPx) {
        const cleaned = String(text || "").replace(/\s+/g, " ").trim();
        if (!cleaned) {
            return "";
        }
        if (measureLabel(cleaned) <= maxPx) {
            return cleaned;
        }
        const ell = "...";
        let lo = 1;
        let hi = cleaned.length;
        let best = ell;
        while (lo <= hi) {
            const mid = Math.floor((lo + hi) / 2);
            const cand = cleaned.slice(0, mid).replace(/[. ]+$/, "") + ell;
            if (measureLabel(cand) <= maxPx) {
                best = cand;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return best;
    }

    function wrapNameTwoLines(text, maxPx) {
        const cleaned = String(text || "").replace(/\s+/g, " ").trim();
        if (!cleaned) {
            return ["(unnamed)"];
        }
        if (measureLabel(cleaned) <= maxPx) {
            return [cleaned];
        }
        const words = cleaned.split(" ").filter(Boolean);
        if (words.length === 1) {
            return [truncToWidth(cleaned, maxPx)];
        }
        let bestIdx = 1;
        let bestScore = Number.POSITIVE_INFINITY;
        for (let i = 1; i < words.length; i++) {
            const l1 = words.slice(0, i).join(" ");
            const l2 = words.slice(i).join(" ");
            const overflow = Math.max(0, measureLabel(l1) - maxPx)
                + Math.max(0, measureLabel(l2) - maxPx);
            const score = overflow * 1000 + Math.abs(measureLabel(l1) - measureLabel(l2));
            if (score < bestScore) {
                bestScore = score;
                bestIdx = i;
            }
        }
        return [
            truncToWidth(words.slice(0, bestIdx).join(" "), maxPx),
            truncToWidth(words.slice(bestIdx).join(" "), maxPx),
        ].filter(Boolean);
    }

    function nodeLabelText(n) {
        const maxPx = nodeLabelMaxPx();
        const rawName = String(n.name || "(unnamed)").replace(/\s+/g, " ").trim() || "(unnamed)";
        const lines = wrapNameTwoLines(rawName, maxPx);
        const loc = String(n.location || "").trim();
        if (loc) {
            lines.push(truncToWidth(loc, maxPx));
        }
        return lines.join("\n");
    }

    function tipRow(label, value) {
        const esc = typeof global.escapeHtmlForSankeyTooltip === "function"
            ? global.escapeHtmlForSankeyTooltip
            : function (s) { return String(s); };
        return "<div><b>" + esc(label) + "</b> " + esc(value) + "</div>";
    }

    function nodeTooltipHtml(n) {
        if (!n) {
            return "";
        }
        let html = "";
        if (n.product) {
            html += tipRow("Product:", n.product);
        }
        if (n.name) {
            html += tipRow("Process:", n.name);
        }
        const loc = String(n.location || "").trim();
        if (loc) {
            html += tipRow("Location:", loc);
        }
        if (n.database) {
            html += tipRow("Database:", n.database);
        }
        return html;
    }

    function edgeTooltipHtml(e) {
        if (!e) {
            return "";
        }
        const rec = {
            product: e.product,
            amount: e.amount,
            amount_unit: e.amount_unit || e.unit,
        };
        let html = "";
        if (e.role === "substitution") {
            html += tipRow("Type:", "Substitution");
        }
        if (typeof global.buildSankeyEdgeTooltipHtml === "function") {
            return html + global.buildSankeyEdgeTooltipHtml(rec);
        }
        if (e.product) {
            html += tipRow("Product:", e.product);
        }
        if (e.amount != null) {
            html += tipRow("Flow amount:", [formatAmount(e.amount), e.unit || ""].filter(Boolean).join(" "));
        }
        return html;
    }

    function remainderLabel(n) {
        const count = Number(n && n.hidden_count) || 0;
        if (n && n.bucket === "consumers") {
            return count === 1 ? "1\nconsumer" : count + "\nconsumers";
        }
        if (n && n.bucket === "suppliers") {
            return count === 1 ? "1\nsupplier" : count + "\nsuppliers";
        }
        if (count === 1) {
            return "1 more\nprocess";
        }
        return count + " more\nprocesses";
    }

    function remainderTooltipHtml(n) {
        if (!n) {
            return "";
        }
        let html = "";
        if (n.product) {
            html += tipRow("Product:", n.product);
        }
        if (n.side) {
            html += tipRow("Side:", n.side);
        }
        const count = Number(n.hidden_count) || 0;
        let noun = "processes";
        if (n.bucket === "consumers") {
            noun = count === 1 ? "consumer" : "consumers";
        } else if (n.bucket === "suppliers") {
            noun = count === 1 ? "supplier" : "suppliers";
        } else if (count === 1) {
            noun = "process";
        }
        html += tipRow("Not shown:", count + " " + noun);
        html += "<div>Click to show up to 10 more</div>";
        return html;
    }

    function tooltipSel() {
        return d3.select("#tooltip");
    }

    function showTip(event, html) {
        if (!html) {
            hideTip();
            return;
        }
        if (typeof global.abPlaceHtmlTooltip === "function") {
            global.abPlaceHtmlTooltip(tooltipSel(), event, html);
            return;
        }
        tooltipSel().attr("hidden", null).html(html)
            .style("left", (event.pageX + 12) + "px")
            .style("top", (event.pageY + 12) + "px");
    }

    function hideTip() {
        tooltipSel().attr("hidden", "hidden");
    }

    function stubSegment(host, side, yOffset, labelLines, labelAbove) {
        const hw = (host.width || NODE_W) / 2;
        const hy = host.y + yOffset;
        const lines = Math.max(1, labelLines || 1);
        const ly = labelAbove
            ? hy - 6 - (lines - 1) * STUB_LINE_PX
            : hy + 14;
        if (side === "upstream") {
            return {
                x1: host.x - hw - STUB_LEN,
                y1: hy,
                x2: host.x - hw,
                y2: hy,
                lx: host.x - hw - STUB_LEN / 2,
                ly: ly,
            };
        }
        return {
            x1: host.x + hw,
            y1: hy,
            x2: host.x + hw + STUB_LEN,
            y2: hy,
            lx: host.x + hw + STUB_LEN / 2,
            ly: ly,
        };
    }

    function pairCoversStub(stub, flowEdges) {
        const hid = "p:" + stub.host_process_id;
        return flowEdges.some(function (e) {
            if (e.product !== stub.product || (e.unit || "") !== (stub.unit || "")) {
                return false;
            }
            if (stub.side === "downstream") {
                return e.source_id === hid;
            }
            return e.target_id === hid;
        });
    }

    function ensureMarkers(svg) {
        let defs = svg.select("defs");
        if (defs.empty()) {
            defs = svg.append("defs");
        }
        if (defs.select("#ge-arrow-blue").empty()) {
            defs.append("marker")
                .attr("id", "ge-arrow-blue")
                .attr("viewBox", "0 0 10 10")
                .attr("refX", 9)
                .attr("refY", 5)
                .attr("markerWidth", 7)
                .attr("markerHeight", 7)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M 0 0 L 10 5 L 0 10 z")
                .attr("fill", "var(--ab-graph-edge-label)");
        }
        if (defs.select("#ge-arrow-red").empty()) {
            defs.append("marker")
                .attr("id", "ge-arrow-red")
                .attr("viewBox", "0 0 10 10")
                .attr("refX", 9)
                .attr("refY", 5)
                .attr("markerWidth", 7)
                .attr("markerHeight", 7)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M 0 0 L 10 5 L 0 10 z")
                .attr("fill", "#c62828");
        }
        if (defs.select("#ge-arrow-green").empty()) {
            defs.append("marker")
                .attr("id", "ge-arrow-green")
                .attr("viewBox", "0 0 10 10")
                .attr("refX", 9)
                .attr("refY", 5)
                .attr("markerWidth", 7)
                .attr("markerHeight", 7)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M 0 0 L 10 5 L 0 10 z")
                .attr("fill", "#2e7d32");
        }
    }

    function flowClasses(data) {
        const cls = ["edgePath"];
        if (data && data.kind === "remainder") {
            cls.push("remainder");
        }
        if (data && data.role === "waste") {
            cls.push("waste");
        }
        if (data && data.role === "substitution") {
            cls.push("substitution");
        } else if (data && (data.center_functional || (data.is_center_host && data.functional_at))) {
            cls.push("functional");
        }
        return cls.join(" ");
    }

    function expandFunctional(data) {
        if (!window.backend || !data || !data.flow) {
            return;
        }
        const host = data.host_process_id || payload.center_id;
        window.backend.expand_flow(String(host), JSON.stringify(data.flow));
    }

    function drawFuncDot(parent, x, y) {
        parent.append("circle")
            .attr("class", "func-dot")
            .attr("cx", x)
            .attr("cy", y)
            .attr("r", DOT_R);
    }

    function fitGraphTransform(groupNode, width, height) {
        if (!groupNode) {
            return d3.zoomIdentity.translate(24, 24);
        }
        let bbox;
        try {
            bbox = groupNode.getBBox();
        } catch (err) {
            return d3.zoomIdentity.translate(24, 24);
        }
        if (!bbox.width || !bbox.height) {
            return d3.zoomIdentity.translate(width / 2, height / 2);
        }
        const pad = 36;
        const scale = Math.min(
            (width - pad * 2) / bbox.width,
            (height - pad * 2) / bbox.height,
            1.4
        );
        const tx = width / 2 - scale * (bbox.x + bbox.width / 2);
        const ty = height / 2 - scale * (bbox.y + bbox.height / 2);
        return d3.zoomIdentity.translate(tx, ty).scale(scale);
    }

    function applyFitTransform() {
        if (!zoomBehavior || !canvas.node()) {
            return;
        }
        const width = canvas.node().clientWidth || 800;
        const height = canvas.node().clientHeight || 500;
        canvas.call(zoomBehavior.transform, fitGraphTransform(panGroup && panGroup.node(), width, height));
    }

    function render(data) {
        const t0 = (typeof performance !== "undefined") ? performance.now() : 0;
        payload = data || { nodes: [], edges: [] };
        const processNodes = (payload.nodes || []).filter(function (n) {
            return n.kind === "process";
        });
        const remainderList = (payload.nodes || []).filter(function (n) {
            return n.kind === "remainder";
        });
        const flowEdges = (payload.edges || []).filter(function (e) {
            return e.kind === "flow";
        });
        const remainderEdges = (payload.edges || []).filter(function (e) {
            return e.kind === "remainder";
        });

        const width = canvas.node().clientWidth || 800;
        const height = canvas.node().clientHeight || 500;
        canvas.attr("width", width).attr("height", height);
        canvas.selectAll("*").remove();
        hideTip();
        ensureMarkers(canvas);

        panGroup = canvas.append("g").attr("id", "pan-group");
        zoomBehavior = d3.zoom().scaleExtent([0.15, 4]).on("zoom", function (event) {
            panGroup.attr("transform", event.transform);
            hideTip();
        });
        canvas.call(zoomBehavior);

        const Graph = (typeof dagre !== "undefined" && dagre.graphlib)
            ? dagre.graphlib.Graph
            : dagreD3.graphlib.Graph;
        dagreGraph = new Graph({ multigraph: true }).setGraph({
            rankdir: "LR",
            ranker: "tight-tree",
            ranksep: 48,
            nodesep: 36,
        });

        processNodes.forEach(function (n) {
            dagreGraph.setNode(n.id, {
                label: nodeLabelText(n),
                data: n,
                width: NODE_W,
                height: NODE_H,
                paddingLeft: 0,
                paddingRight: 0,
                paddingTop: 0,
                paddingBottom: 0,
                rx: 2,
                ry: 2,
                labelStyle: "font-size: 12px;",
            });
        });

        remainderList.forEach(function (n) {
            dagreGraph.setNode(n.id, {
                label: remainderLabel(n),
                data: n,
                width: NODE_W,
                height: NODE_H,
                paddingLeft: 0,
                paddingRight: 0,
                paddingTop: 0,
                paddingBottom: 0,
                rx: 2,
                ry: 2,
                class: "remainder",
                labelStyle: "font-size: 12px;",
            });
        });

        const wrapCols = typeof global.inferSankeyEdgeLabelMaxCols === "function"
            ? global.inferSankeyEdgeLabelMaxCols({ nodes: processNodes })
            : 12;

        flowEdges.forEach(function (e, i) {
            const rec = Object.assign({}, e);
            rec.curve = d3.curveBasis;
            rec.label = wrapLabel(flowLabel(e), wrapCols);
            rec.arrowhead = "vee";
            rec.class = flowClasses(e);
            rec.data = e;
            dagreGraph.setEdge(e.source_id, e.target_id, rec, "e" + i);
        });

        remainderEdges.forEach(function (e, i) {
            dagreGraph.setEdge(e.source_id, e.target_id, {
                curve: d3.curveBasis,
                label: " ",
                arrowhead: "vee",
                class: "edgePath remainder",
                data: e,
            }, "r" + i);
        });

        if (dagreRender) {
            panGroup.call(dagreRender, dagreGraph);
        } else {
            dagre.layout(dagreGraph);
        }

        panGroup.selectAll("g.edgePath").each(function () {
            const sel = d3.select(this);
            const datum = sel.datum();
            const ed = dagreGraph.edge(datum) || {};
            const data = ed.data || ed;
            sel.attr("class", flowClasses(data));
            const pts = ed.points || [];
            if (data.kind !== "remainder" && pts.length >= 2) {
                if (data.functional_at === "target") {
                    const end = pts[pts.length - 1];
                    drawFuncDot(sel, end.x, end.y);
                } else if (data.functional_at === "source") {
                    drawFuncDot(sel, pts[0].x, pts[0].y);
                }
            }
            if (data.center_functional) {
                sel.style("cursor", "pointer");
                sel.on("click", function (event) {
                    event.stopPropagation();
                    expandFunctional(data);
                });
            }
            sel.on("mouseenter", function (event) {
                if (data.kind === "remainder") {
                    return;
                }
                setSameProductHot(data);
                showTip(event, edgeTooltipHtml(data));
            });
            sel.on("mousemove", function (event) {
                if (data.kind === "remainder") {
                    return;
                }
                showTip(event, edgeTooltipHtml(data));
            });
            sel.on("mouseleave", function () {
                panGroup.selectAll("g.edgePath").classed("hot", false);
                hideTip();
            });
        });

        panGroup.selectAll("g.edgeLabel").each(function () {
            const sel = d3.select(this);
            const ed = dagreGraph.edge(sel.datum()) || {};
            const data = ed.data || ed;
            if (data.center_functional) {
                sel.classed("functional", true);
                sel.style("cursor", "pointer");
                sel.on("click", function (event) {
                    event.stopPropagation();
                    expandFunctional(data);
                });
            }
            sel.on("mouseenter", function (event) {
                setSameProductHot(data);
                showTip(event, edgeTooltipHtml(data));
            });
            sel.on("mousemove", function (event) {
                showTip(event, edgeTooltipHtml(data));
            });
            sel.on("mouseleave", function () {
                panGroup.selectAll("g.edgePath").classed("hot", false);
                hideTip();
            });
        });

        panGroup.selectAll("g.node").each(function (id) {
            const n = dagreGraph.node(id);
            const data = (n && n.data) || {};
            const ng = d3.select(this);
            n.width = NODE_W;
            n.height = NODE_H;
            ng.select("rect")
                .attr("width", NODE_W)
                .attr("height", NODE_H)
                .attr("x", -NODE_W / 2)
                .attr("y", -NODE_H / 2);
            if (data.kind === "remainder") {
                ng.classed("remainder", true);
                ng.style("cursor", "pointer");
                ng.on("mouseenter", function (event) {
                    showTip(event, remainderTooltipHtml(data));
                });
                ng.on("mousemove", function (event) {
                    showTip(event, remainderTooltipHtml(data));
                });
                ng.on("mouseleave", hideTip);
                ng.on("click", function (event) {
                    event.stopPropagation();
                    if (!window.backend) {
                        return;
                    }
                    if (data.flow) {
                        expandFunctional(data);
                        return;
                    }
                    if (data.side) {
                        window.backend.expand_listed_side(String(data.host_process_id), String(data.side));
                    }
                });
                return;
            }
            ng.classed("center", !!data.is_center);
            ng.classed("demand", !!data.is_center);
            ng.classed("selected", !!data.selected);
            if (data.location) {
                const tspans = ng.selectAll("text tspan").nodes();
                if (tspans.length) {
                    d3.select(tspans[tspans.length - 1]).classed("ab-loc", true);
                }
            }
            addSideControls(ng, n, data);
            if (data.multifunctional) {
                ng.append("text")
                    .attr("class", "ab-multi")
                    .attr("text-anchor", "end")
                    .attr("x", NODE_W / 2 - 5)
                    .attr("y", NODE_H / 2 - 5)
                    .text("M");
            }
            ng.on("mouseenter", function (event) {
                ng.style("opacity", 0.4);
                showTip(event, nodeTooltipHtml(data));
            });
            ng.on("mousemove", function (event) {
                showTip(event, nodeTooltipHtml(data));
            });
            ng.on("mouseleave", function () {
                ng.style("opacity", 1);
                hideTip();
            });
            ng.on("click", function (event) {
                event.stopPropagation();
                if (event.altKey && window.backend) {
                    window.backend.remove_process(String(data.process_id));
                    return;
                }
                if (window.backend) {
                    window.backend.select_process(String(data.process_id));
                }
            });
            ng.on("contextmenu", function (event) {
                event.preventDefault();
                event.stopPropagation();
                hideTip();
                if (window.backend) {
                    window.backend.open_process(String(data.process_id));
                }
            });
        });

        const stubList = (payload.edges || []).filter(function (e) {
            return e.kind === "stub"
                && e.is_center_host
                && e.functional_at
                && !pairCoversStub(e, flowEdges);
        });
        const stubsByHostSide = {};
        stubList.forEach(function (stub) {
            const key = stub.host_process_id + ":" + stub.side;
            stubsByHostSide[key] = stubsByHostSide[key] || [];
            stubsByHostSide[key].push(stub);
        });
        Object.keys(stubsByHostSide).forEach(function (key) {
            const stubs = stubsByHostSide[key];
            const hostNode = dagreGraph.node("p:" + stubs[0].host_process_id);
            if (!hostNode) {
                return;
            }
            const n = stubs.length;
            const labels = stubs.map(function (stub) {
                return wrapLabel(flowLabel(stub), wrapCols);
            });
            const maxLines = labels.reduce(function (mx, lab) {
                return Math.max(mx, String(lab || "").split("\n").filter(Boolean).length);
            }, 1);
            const gap = n <= 2
                ? Math.max(32, NODE_H * 0.7)
                : Math.max(48, maxLines * STUB_LINE_PX + 16);
            stubs.forEach(function (stub, idx) {
                const yOffset = (idx - (n - 1) / 2) * (n > 1 ? gap : 0);
                const labelAbove = true;
                const label = labels[idx];
                const labelLines = String(label || "").split("\n").filter(Boolean).length;
                const seg = stubSegment(hostNode, stub.side, yOffset, labelLines, labelAbove);
                const eg = panGroup.append("g")
                    .datum(stub)
                    .attr("class", flowClasses(stub) + " stub");
                eg.append("path")
                    .attr("class", "path")
                    .attr("d", "M" + seg.x1 + "," + seg.y1 + " H" + seg.x2);
                if (stub.functional_at === "target") {
                    drawFuncDot(eg, seg.x2, seg.y2);
                } else if (stub.functional_at === "source") {
                    drawFuncDot(eg, seg.x1, seg.y1);
                }
                if (label) {
                    const text = eg.append("text").attr("class", "edgeLabel")
                        .attr("text-anchor", "middle")
                        .attr("x", seg.lx).attr("y", seg.ly);
                    String(label).split("\n").forEach(function (ln, li) {
                        text.append("tspan")
                            .attr("x", seg.lx)
                            .attr("dy", li === 0 ? 0 : "1.05em")
                            .text(ln);
                    });
                }
                if (stub.expandable) {
                    eg.style("cursor", "pointer");
                    eg.on("click", function (event) {
                        event.stopPropagation();
                        expandFunctional(stub);
                    });
                }
                eg.on("mouseenter", function (event) {
                    setSameProductHot(stub);
                    showTip(event, edgeTooltipHtml(stub));
                });
                eg.on("mousemove", function (event) {
                    showTip(event, edgeTooltipHtml(stub));
                });
                eg.on("mouseleave", function () {
                    panGroup.selectAll("g.edgePath").classed("hot", false);
                    hideTip();
                });
            });
        });

        applyFitTransform();
        if (typeof console !== "undefined" && console.debug) {
            const n = ((payload.nodes || []).filter(function (nd) { return nd.kind === "process"; })).length;
            console.debug(
                "Graph explorer draw",
                (performance.now() - t0).toFixed(0),
                "ms,",
                n,
                "processes"
            );
        }
    }

    function addSideControls(ng, n, data) {
        if (!n) {
            return;
        }
        const hw = (n.width || 80) / 2;
        const hh = (n.height || NODE_H) / 2;
        const triSize = 80;
        const tri = d3.symbol().type(d3.symbolTriangle).size(triSize);
        // d3 triangle: centroid at origin; distance to base is 1/3 height.
        const toBase = Math.sqrt(triSize / (3 * Math.sqrt(3)));
        const toVertex = 2 * toBase;

        function ctrl(x, y, rotate, title, onClick, visible) {
            if (!visible || !window.backend) {
                return;
            }
            const path = ng.append("path")
                .attr("class", "ctrl")
                .attr("d", tri)
                .attr("transform", "translate(" + x + "," + y + ") rotate(" + rotate + ")");
            path.append("title").text(title);
            path.on("click", function (event) {
                event.stopPropagation();
                onClick();
            });
        }

        const yAt25 = -hh + NODE_H * 0.25;
        const leftBoth = data.expand_upstream && data.collapse_upstream;
        const rightBoth = data.expand_downstream && data.collapse_downstream;
        const leftExpY = leftBoth ? yAt25 - 8 : yAt25;
        const leftColY = leftBoth ? yAt25 + 8 : yAt25;
        const rightExpY = rightBoth ? yAt25 - 8 : yAt25;
        const rightColY = rightBoth ? yAt25 + 8 : yAt25;

        ctrl(-hw - toBase, leftExpY, -90, "Expand upstream", function () {
            window.backend.expand_side(String(data.process_id), "upstream");
        }, data.expand_upstream);
        ctrl(-hw - toVertex, leftColY, 90, "Collapse upstream", function () {
            window.backend.collapse_side(String(data.process_id), "upstream");
        }, data.collapse_upstream);
        ctrl(hw + toBase, rightExpY, 90, "Expand downstream", function () {
            window.backend.expand_side(String(data.process_id), "downstream");
        }, data.expand_downstream);
        ctrl(hw + toVertex, rightColY, -90, "Collapse downstream", function () {
            window.backend.collapse_side(String(data.process_id), "downstream");
        }, data.collapse_downstream);
    }

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Delete" || !window.backend) {
            return;
        }
        const sel = (payload.nodes || []).find(function (n) {
            return n.kind === "process" && n.selected && !n.is_center;
        });
        if (sel) {
            window.backend.remove_process(String(sel.process_id));
        }
    });

    global.abRenderGraphExplorer = render;
    global.abFitGraphExplorer = applyFitTransform;

    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.bridge = channel.objects.bridge;
        window.backend = channel.objects.backend;
        window.bridge.update_graph.connect(function (json_data) {
            render(JSON.parse(json_data));
        });
        window.bridge.is_ready();
    });
}(window));
