/* Contribution Tree D3 preview — maps Python segment geometry onto SVG.
 * Do not rebuild hierarchy with d3.hierarchy / d3.partition.
 */
(function () {
    "use strict";

    var graphOpts = { minimap: false, flows: true, abs: true, rel: true, rankdir: "BT" };
    var payload = { mode: "icicle", kind: "partition", segments: [], style: {}, empty_message: "" };

    function graphControlsEl() {
        return document.getElementById("graph-controls");
    }

    function syncGraphControls() {
        var el = graphControlsEl();
        if (!el) {
            return;
        }
        if (payload.kind === "graph") {
            el.removeAttribute("hidden");
            document.documentElement.classList.add("ab-tree-graph");
            document.body.classList.add("ab-tree-graph");
        } else {
            el.setAttribute("hidden", "hidden");
            document.documentElement.classList.remove("ab-tree-graph");
            document.body.classList.remove("ab-tree-graph");
        }
    }

    function bindGraphControl(id, key) {
        var input = document.getElementById(id);
        if (!input) {
            return;
        }
        input.addEventListener("change", function () {
            graphOpts[key] = input.checked;
            render({ labelsOnly: key === "abs" || key === "rel" || key === "flows" });
        });
    }
    bindGraphControl("graphMinimap", "minimap");
    bindGraphControl("graphFlows", "flows");
    bindGraphControl("graphAbs", "abs");
    bindGraphControl("graphRel", "rel");
    (function syncMinimapFromDom() {
        var input = document.getElementById("graphMinimap");
        if (input) {
            graphOpts.minimap = !!input.checked;
        }
    })();
    (function bindRankdir() {
        var sel = document.getElementById("graphRankdir");
        if (!sel) {
            return;
        }
        graphOpts.rankdir = sel.value || "BT";
        sel.addEventListener("change", function () {
            graphOpts.rankdir = sel.value || "BT";
            render();
        });
    })();
    var svg = d3.select("#plot");
    var tooltip = d3.select("#tooltip");
    var emptyEl = d3.select("#empty");

    function applyStyle(style) {
        style = style || {};
        if (typeof window.abLockGraphTheme === "function") {
            window.abLockGraphTheme(!!style.dark);
        } else if (typeof window.abApplyGraphTheme === "function") {
            document.documentElement.setAttribute("data-ab-theme-locked", "1");
            window.abApplyGraphTheme(!!style.dark);
        }
        var bg = style.background || "#ffffff";
        var text = style.text || "#222222";
        var muted = style.muted || text;
        document.body.style.background = bg;
        document.body.style.color = text;
        emptyEl.style("color", muted);
        tooltip
            .style("background", bg)
            .style("color", text)
            .style("border", "1px solid " + (style.dark ? "#666666" : "#cccccc"));
    }

    function fillColor(d, maxDirect, dark) {
        var colorBy = payload.color_by || "direct";
        if (colorBy !== "direct" && d.color_key) {
                if (!payload._ordinal) {
                    var keys = (payload.segments || []).map(function (s) { return s.color_key; }).filter(Boolean);
                    payload._ordinal = typeof window.abOrdinalScale === "function"
                        ? window.abOrdinalScale(keys)
                        : d3.scaleOrdinal(d3.schemeTableau10).domain(Array.from(new Set(keys)));
                }
            return payload._ordinal(d.color_key);
        }
        if (typeof window.abDirectImpactFill === "function") {
            return window.abDirectImpactFill(d.direct_pct || 0, dark);
        }
        var sign = d.direct_sign;
        if (sign == null) {
            var pct = d.direct_pct || 0;
            sign = pct > 0 ? 1 : pct < 0 ? -1 : 0;
        }
        if (sign === 0) {
            return dark ? "#2a2a2a" : "#ffffff";
        }
        return sign < 0 ? "#2e8b57" : "#4682d2";
    }

    function showEmpty(message) {
        svg.selectAll("*").remove();
        if (message) {
            emptyEl.text(message).attr("hidden", null);
        } else {
            emptyEl.text("").attr("hidden", "hidden");
        }
    }

    function hideEmpty() {
        emptyEl.text("").attr("hidden", "hidden");
    }

    function hideTooltip() {
        tooltip.attr("hidden", "hidden");
    }

    function showTooltip(event, d) {
        if (d == null) {
            return;
        }
        var html;
        if (typeof window.abContributionTooltipHtml === "function") {
            html = window.abContributionTooltipHtml(d, payload.unit || "");
        } else {
            html = (d.tooltip || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }
        if (typeof window.abPlaceHtmlTooltip === "function") {
            window.abPlaceHtmlTooltip(tooltip, event, html);
            return;
        }
        tooltip
            .attr("hidden", null)
            .html(html)
            .style("left", (event.pageX + 12) + "px")
            .style("top", (event.pageY + 12) + "px");
    }

    function clickSegment(event, d) {
        if (d == null) {
            return;
        }
        if (window.bridge && typeof window.bridge.click_segment === "function") {
            window.bridge.click_segment(d.click_uid);
        }
    }

    function contextSegment(event, d) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        hideTooltip();
        if (d == null) {
            return;
        }
        if (window.bridge && typeof window.bridge.context_segment === "function") {
            var payload = (typeof abOpenProcessPayload === "function")
                ? abOpenProcessPayload(d)
                : {
                    visit_id: d.visit_id != null ? d.visit_id : d.unique_id,
                    unique_id: d.unique_id,
                    activity_id: d.activity_id,
                    database: d.database || "",
                    code: d.code || "",
                    is_aggregate: !!d.is_aggregate,
                    constituent_uids: d.constituent_uids || [],
                    mouse: 2
                };
            window.bridge.context_segment(JSON.stringify(payload));
        }
    }

    function bindSegment(selection) {
        selection
            .on("mousemove", showTooltip)
            .on("mouseleave", hideTooltip)
            .on("click", clickSegment)
            .on("contextmenu", contextSegment);
    }

    function fitLabel(text, maxChars) {
        if (!text) {
            return "";
        }
        var w = Math.max(1, maxChars);
        if (text.length <= w) {
            return text;
        }
        var cut = text.slice(0, Math.max(1, w - 1));
        var brk = Math.max(cut.lastIndexOf(","), cut.lastIndexOf(" "));
        if (brk >= 4) {
            cut = cut.slice(0, brk);
        }
        return cut.replace(/[, ]+$/, "") + "…";
    }

    function labelWorthShowing(display) {
        var stripped = String(display || "").replace(/[.…]/g, "").replace(/\s+/g, "");
        return stripped.length >= 3;
    }

    function layoutLines(text, charsPerLine, maxLines) {
        if (maxLines >= 2) {
            var comma = text.indexOf(",");
            if (comma >= 3) {
                var head = fitLabel(text.slice(0, comma).trim(), charsPerLine);
                var tail = fitLabel(text.slice(comma + 1).trim(), charsPerLine);
                if (labelWorthShowing(head) && (!tail || labelWorthShowing(tail))) {
                    return tail ? [head, tail] : [head];
                }
            }
        }
        return [fitLabel(text, charsPerLine)];
    }

    function segmentStroke(style) {
        var dark = !!(style && style.dark);
        var edge = style && style.edge;
        if (edge && edge !== "#fff" && edge !== "#ffffff" && edge !== "white") {
            return edge;
        }
        return dark ? "#c5c5c5" : "#333333";
    }

    function tierBoxStroke(style) {
        return (style && style.dark) ? "#6e6e6e" : "#d0d0d0";
    }

    function polarXY(angle, radius) {
        return [Math.sin(angle) * radius, -Math.cos(angle) * radius];
    }

    function sunburstFlipArc(midRad) {
        var deg = ((midRad * 180 / Math.PI) % 360 + 360) % 360;
        return deg > 90 && deg <= 270;
    }

    function sunburstLabelArc(a0, a1, radius, flip) {
        var p0 = polarXY(a0, radius);
        var p1 = polarXY(a1, radius);
        var large = Math.abs(a1 - a0) > Math.PI ? 1 : 0;
        if (flip) {
            return "M" + p1[0] + "," + p1[1]
                + " A" + radius + "," + radius + " 0 " + large + " 0 "
                + p0[0] + "," + p0[1];
        }
        return "M" + p0[0] + "," + p0[1]
            + " A" + radius + "," + radius + " 0 " + large + " 1 "
            + p1[0] + "," + p1[1];
    }

    function appendSunburstTextPath(textEl, pathId, content) {
        textEl.append("textPath")
            .attr("href", "#" + pathId)
            .attr("xlink:href", "#" + pathId)
            .attr("startOffset", "50%")
            .attr("text-anchor", "middle")
            .text(content);
    }

    function drawIcicle(g, segs, width, height, style, maxDirect) {
        var depth = Math.max(1, payload.plot_depth || (d3.max(segs, function (d) { return d.tier; }) + 1));
        var top = 22;
        var bottom = 8;
        var colW = width / depth;
        var plotH = Math.max(1, height - top - bottom);
        var dark = !!style.dark;
        var text = style.text || "#222";
        var edge = tierBoxStroke(style);

        g.selectAll(".ct-tier-label")
            .data(d3.range(depth))
            .enter()
            .append("text")
            .attr("class", "ct-tier-label")
            .attr("x", function (t) { return (t + 0.5) * colW; })
            .attr("y", 14)
            .attr("text-anchor", "middle")
            .attr("fill", text)
            .text(function (t) { return "Tier " + t; });

        var cellW = colW * 0.97;
        var nodes = g.selectAll(".ct-seg")
            .data(segs)
            .enter()
            .append("g")
            .attr("class", "ct-seg")
            .attr("transform", function (d) {
                return "translate(" + (d.tier * colW) + "," + (top + d.x0 * plotH) + ")";
            });

        bindSegment(nodes.append("rect")
            .attr("width", cellW)
            .attr("height", function (d) { return Math.max(1, (d.x1 - d.x0) * plotH - 1); })
            .attr("fill", function (d) { return fillColor(d, maxDirect, dark); })
            .attr("stroke", edge)
            .attr("stroke-width", 1));

        nodes.append("text")
            .attr("class", "ct-label")
            .attr("x", cellW / 2)
            .attr("y", function (d) { return Math.max(1, (d.x1 - d.x0) * plotH) / 2; })
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", text)
            .attr("font-size", 10)
            .each(function (d) {
                var h = (d.x1 - d.x0) * plotH;
                var el = d3.select(this);
                if (h < 12 || !d.label) {
                    return;
                }
                var chars = Math.max(3, Math.floor(cellW / 6.2));
                var loc = (d.location || "").trim();
                var two = h >= 26 && loc;
                el.append("tspan")
                    .attr("x", cellW / 2)
                    .attr("dy", two ? "-0.45em" : "0")
                    .text(fitLabel(d.label, chars));
                if (two) {
                    el.append("tspan")
                        .attr("x", cellW / 2)
                        .attr("dy", "1.15em")
                        .text(fitLabel(loc, chars));
                }
            });
    }

    function drawTierBars(g, segs, width, height, style, maxDirect) {
        var depth = Math.max(1, payload.plot_depth || (d3.max(segs, function (d) { return d.tier; }) + 1));
        var left = 52;
        var bottom = 8;
        var rowH = Math.max(1, height - bottom) / depth;
        var barH = rowH * 0.85;
        var plotW = Math.max(1, width - left);
        var dark = !!style.dark;
        var text = style.text || "#222";
        var edge = tierBoxStroke(style);

        g.selectAll(".ct-tier-label")
            .data(d3.range(depth))
            .enter()
            .append("text")
            .attr("class", "ct-tier-label")
            .attr("x", left - 6)
            .attr("y", function (t) { return t * rowH + rowH / 2; })
            .attr("text-anchor", "end")
            .attr("dominant-baseline", "middle")
            .attr("fill", text)
            .text(function (t) { return "Tier " + t; });

        var nodes = g.selectAll(".ct-seg")
            .data(segs)
            .enter()
            .append("g")
            .attr("class", "ct-seg")
            .attr("transform", function (d) {
                var y = d.tier * rowH + (rowH - barH) / 2;
                return "translate(" + (left + d.x0 * plotW) + "," + y + ")";
            });

        bindSegment(nodes.append("rect")
            .attr("width", function (d) { return Math.max(1, (d.x1 - d.x0) * plotW - 1); })
            .attr("height", barH)
            .attr("fill", function (d) { return fillColor(d, maxDirect, dark); })
            .attr("stroke", edge)
            .attr("stroke-width", 1));

        nodes.append("text")
            .attr("class", "ct-label")
            .attr("x", function (d) { return Math.max(1, (d.x1 - d.x0) * plotW) / 2; })
            .attr("y", barH / 2)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", text)
            .attr("font-size", 10)
            .each(function (d) {
                var w = (d.x1 - d.x0) * plotW;
                var el = d3.select(this);
                if (w < 28 || !d.label) {
                    return;
                }
                var chars = Math.max(3, Math.floor(w / 6.2));
                var loc = (d.location || "").trim();
                var two = barH >= 26 && loc;
                el.append("tspan")
                    .attr("x", Math.max(1, w) / 2)
                    .attr("dy", two ? "-0.45em" : "0")
                    .text(fitLabel(d.label, chars));
                if (two) {
                    el.append("tspan")
                        .attr("x", Math.max(1, w) / 2)
                        .attr("dy", "1.15em")
                        .text(fitLabel(loc, chars));
                }
            });
    }

    function labelSunburstSegment(inner, defs, d, radius, ringW, fill, halo, pathKey) {
        var frac = Math.abs(d.x1 - d.x0);
        var label = d.label || d.process || d.product || "";
        if (!label || frac < 0.018) {
            return;
        }
        var r0 = ringW * (d.tier + 0.1) * radius;
        var r1 = ringW * (d.tier + 0.9) * radius;
        var ringSpan = r1 - r0;
        if (ringSpan < 11) {
            return;
        }
        var a0 = d.x0 * 2 * Math.PI;
        var a1 = d.x1 * 2 * Math.PI;
        var rMid = (r0 + r1) / 2;
        var mid = (a0 + a1) / 2;
        var arcLen = rMid * Math.abs(a1 - a0);
        var fontSize = 10;
        var maxChars = Math.floor(arcLen / (fontSize * 0.58));
        if (maxChars < 4) {
            return;
        }
        var display = fitLabel(label, maxChars);
        if (!labelWorthShowing(display)) {
            return;
        }
        var loc = (d.location || "").trim();
        var two = ringSpan >= 22 && loc && maxChars >= 8;
        var flip = sunburstFlipArc(mid);
        var rName = two ? rMid - Math.min(6, ringSpan * 0.18) : rMid;
        var rLoc = rMid + Math.min(6, ringSpan * 0.18);
        var nameId = "sb-arc-" + pathKey;
        defs.append("path")
            .attr("id", nameId)
            .attr("d", sunburstLabelArc(a0, a1, rName, flip))
            .attr("fill", "none");
        var el = inner.append("text")
            .attr("class", "ct-label")
            .attr("font-family", "sans-serif")
            .attr("font-size", fontSize);
        appendHaloText(el, fill, halo).attr("stroke-width", halo ? 2.5 : 0);
        appendSunburstTextPath(el, nameId, display);
        if (two) {
            var locId = nameId + "-loc";
            var locText = fitLabel(loc, maxChars);
            if (labelWorthShowing(locText)) {
                defs.append("path")
                    .attr("id", locId)
                    .attr("d", sunburstLabelArc(a0, a1, rLoc, flip))
                    .attr("fill", "none");
                var locEl = inner.append("text")
                    .attr("class", "ct-label")
                    .attr("font-family", "sans-serif")
                    .attr("font-size", fontSize);
                appendHaloText(locEl, fill, halo).attr("stroke-width", halo ? 2.5 : 0);
                appendSunburstTextPath(locEl, locId, locText);
            }
        }
    }

    function appendHaloText(sel, fill, halo) {
        return sel
            .attr("fill", fill)
            .attr("stroke", halo || fill)
            .attr("stroke-width", halo ? 3 : 0)
            .attr("paint-order", "stroke")
            .style("stroke-linejoin", "round");
    }

    function drawSunburst(g, segs, width, height, style, maxDirect) {
        var depth = Math.max(1, payload.plot_depth || (d3.max(segs, function (d) { return d.tier; }) + 1));
        var cx = width / 2;
        var cy = height / 2;
        var radius = Math.min(width, height) * 0.48;
        var ringW = 1 / (depth + 1);
        var dark = !!style.dark;
        var text = style.text || "#222";
        var edge = segmentStroke(style);
        var halo = style.background || (dark ? "#2a2a2a" : "#ffffff");

        var inner = g.append("g").attr("transform", "translate(" + cx + "," + cy + ")");
        var defs = inner.append("defs");
        var t0 = performance.now();
        var arc = d3.arc()
            .startAngle(function (d) { return d.x0 * 2 * Math.PI; })
            .endAngle(function (d) { return d.x1 * 2 * Math.PI; })
            .innerRadius(function (d) { return ringW * (d.tier + 0.05) * radius; })
            .outerRadius(function (d) { return ringW * (d.tier + 0.95) * radius; });

        bindSegment(inner.selectAll(".ct-seg")
            .data(segs)
            .enter()
            .append("path")
            .attr("class", "ct-seg")
            .attr("d", arc)
            .attr("fill", function (d) { return fillColor(d, maxDirect, dark); })
            .attr("stroke", edge)
            .attr("stroke-width", 1));
        var pathsMs = performance.now() - t0;
        t0 = performance.now();

        segs.forEach(function (d, i) {
            labelSunburstSegment(inner, defs, d, radius, ringW, text, halo, i);
        });
        window.abLastDrawProfile = {
            pathsMs: pathsMs,
            labelsMs: performance.now() - t0,
            nSegs: segs.length
        };

        appendHaloText(inner.append("text")
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("font-family", "sans-serif")
            .attr("font-size", 10)
            .text("RF"), text, halo);
    }

    function spanOf(seg) {
        return Math.max(Math.abs((seg.x1 || 0) - (seg.x0 || 0)), 1e-12);
    }

    function nestSegments(segs) {
        var wraps = segs.map(function (seg) {
            return { segment: seg, children: [], isDirect: false };
        });
        var byTier = {};
        wraps.forEach(function (n) {
            var t = n.segment.tier || 0;
            (byTier[t] || (byTier[t] = [])).push(n);
        });
        var maxTier = d3.max(wraps, function (n) { return n.segment.tier || 0; }) || 0;
        var eps = 1e-5;
        function contains(parent, child) {
            return child.x0 >= parent.x0 - eps && child.x1 <= parent.x1 + eps;
        }
        for (var t = 0; t < maxTier; t++) {
            var parents = byTier[t] || [];
            var kids = byTier[t + 1] || [];
            kids.forEach(function (child) {
                var best = null;
                var bestSpan = Infinity;
                parents.forEach(function (p) {
                    if (contains(p.segment, child.segment)) {
                        var sp = spanOf(p.segment);
                        if (sp < bestSpan) {
                            bestSpan = sp;
                            best = p;
                        }
                    }
                });
                if (best) {
                    best.children.push(child);
                }
            });
        }
        function addDirect(n) {
            n.children.forEach(addDirect);
            if (!n.children.length) {
                return;
            }
            var own = spanOf(n.segment);
            var childSum = d3.sum(n.children, function (c) { return spanOf(c.segment); });
            var leftover = own - childSum;
            if (leftover > own * 0.02 && leftover > 1e-6) {
                n.children.push({
                    segment: n.segment,
                    children: [],
                    isDirect: true,
                    value: leftover
                });
            }
        }
        var roots = byTier[0] && byTier[0].length ? byTier[0] : wraps;
        roots.forEach(addDirect);
        if (roots.length === 1) {
            return roots[0];
        }
        return {
            segment: {
                label: "RF",
                tooltip: "",
                click_uid: 0,
                unique_id: 0,
                x0: 0,
                x1: 1,
                direct_pct: 0,
                tier: 0
            },
            children: roots,
            isDirect: false,
            isVirtualRoot: true
        };
    }

    function hierarchyFromSegments(segs) {
        return d3.hierarchy(nestSegments(segs))
            .sum(function (d) {
                if (d.children && d.children.length) {
                    return 0;
                }
                if (d.value) {
                    return d.value;
                }
                return spanOf(d.segment);
            })
            .sort(function (a, b) { return (b.value || 0) - (a.value || 0); });
    }

    function hierarchyLabel(d) {
        var seg = d.data && d.data.segment;
        return (seg && (seg.label || seg.process || seg.product)) || "";
    }

    function bindHierarchy(selection) {
        selection
            .on("mousemove", function (event, d) {
                if (d.data && d.data.isVirtualRoot) {
                    return;
                }
                var seg = d.data && d.data.segment;
                if (seg) {
                    showTooltip(event, seg);
                }
            })
            .on("mouseleave", hideTooltip)
            .on("click", function (event, d) {
                if (d.data && d.data.isVirtualRoot) {
                    return;
                }
                var seg = d.data && d.data.segment;
                if (seg) {
                    clickSegment(event, seg);
                }
            })
            .on("contextmenu", function (event, d) {
                if (d.data && d.data.isVirtualRoot) {
                    return;
                }
                var seg = d.data && d.data.segment;
                if (seg) {
                    contextSegment(event, seg);
                }
            });
    }

    function drawTreemap(g, segs, width, height, style, maxDirect) {
        var t0 = performance.now();
        var root = hierarchyFromSegments(segs);
        d3.treemap()
            .tile(d3.treemapSquarify)
            .size([width, height])
            .paddingInner(3)
            .paddingOuter(2)
            .paddingTop(16)
            (root);

        var dark = !!style.dark;
        var textColor = style.text || "#222";
        var edge = segmentStroke(style);
        var nodes = root.descendants().filter(function (d) {
            return !(d.data && d.data.isVirtualRoot);
        });
        var cells = g.selectAll(".ct-seg")
            .data(nodes)
            .enter()
            .append("g")
            .attr("class", "ct-seg")
            .attr("transform", function (d) {
                return "translate(" + d.x0 + "," + d.y0 + ")";
            });

        bindHierarchy(cells.append("rect")
            .attr("width", function (d) { return Math.max(0, d.x1 - d.x0); })
            .attr("height", function (d) { return Math.max(0, d.y1 - d.y0); })
            .attr("fill", function (d) {
                if (d.children) {
                    return "rgba(0,0,0,0)";
                }
                return fillColor(d.data.segment, maxDirect, dark);
            })
            .attr("stroke", edge)
            .attr("stroke-width", 1));

        cells.append("text")
            .attr("class", "ct-label")
            .attr("x", function (d) { return (d.x1 - d.x0) / 2; })
            .attr("y", function (d) {
                return d.children ? 11 : (d.y1 - d.y0) / 2;
            })
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", textColor)
            .attr("font-size", 10)
            .text(function (d) {
                var w = d.x1 - d.x0;
                var h = d.y1 - d.y0;
                if (w < 36 || h < 14) {
                    return "";
                }
                var label = hierarchyLabel(d);
                if (!label) {
                    return "";
                }
                var display = fitLabel(label, Math.max(3, Math.floor(w / 6.2)));
                return labelWorthShowing(display) ? display : "";
            });
        window.abLastDrawProfile = {
            layoutMs: performance.now() - t0,
            nSegs: segs.length,
            nCells: nodes.length
        };
    }

    function drawCirclePack(g, segs, width, height, style, maxDirect) {
        var size = Math.min(width, height);
        var root = hierarchyFromSegments(segs);
        d3.pack()
            .size([size, size])
            .padding(4)
            (root);

        var dark = !!style.dark;
        var textColor = style.text || "#222";
        var edge = segmentStroke(style);
        var inner = g.append("g")
            .attr("transform", "translate(" + ((width - size) / 2) + "," +
                ((height - size) / 2) + ")");

        var circles = inner.selectAll(".ct-seg")
            .data(root.descendants())
            .enter()
            .append("g")
            .attr("class", "ct-seg")
            .attr("transform", function (d) {
                return "translate(" + d.x + "," + d.y + ")";
            });

        bindHierarchy(circles.append("circle")
            .attr("r", function (d) { return Math.max(0, d.r); })
            .attr("fill", function (d) {
                if (d.data && d.data.isVirtualRoot) {
                    return "none";
                }
                if (d.children) {
                    return "rgba(255,255,255,0.04)";
                }
                return fillColor(d.data.segment, maxDirect, dark);
            })
            .attr("stroke", edge)
            .attr("stroke-width", 1));

        circles.append("text")
            .attr("class", "ct-label")
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", textColor)
            .attr("font-size", 10)
            .text(function (d) {
                if (d.children || d.r < 16) {
                    return "";
                }
                var label = hierarchyLabel(d);
                if (!label) {
                    return "";
                }
                var display = fitLabel(label, Math.max(3, Math.floor(d.r / 3.6)));
                return labelWorthShowing(display) ? display : "";
            });
    }

    var renderRetry = null;
    var renderRetryCount = 0;
    var resizeTimer = null;

    var lastVpW = 0;
    var lastVpH = 0;
    var forcedViewport = null;

    function applyViewportSize(width, height) {
        svg.attr("width", width).attr("height", height);
    }

    function viewportSize() {
        if (forcedViewport && forcedViewport.width >= 8 && forcedViewport.height >= 8) {
            var controls = graphControlsEl();
            var controlsH = 0;
            if (controls && !controls.hasAttribute("hidden")) {
                controlsH = controls.getBoundingClientRect().height || 0;
            }
            return {
                width: forcedViewport.width,
                height: Math.max(0, Math.floor(forcedViewport.height - controlsH)),
            };
        }
        var controls = graphControlsEl();
        var controlsH = 0;
        if (controls && !controls.hasAttribute("hidden")) {
            controlsH = controls.getBoundingClientRect().height || 0;
        }
        var host = document.documentElement;
        var width = host.clientWidth || window.innerWidth || 0;
        var height = (host.clientHeight || window.innerHeight || 0) - controlsH;
        return { width: Math.floor(width), height: Math.floor(Math.max(0, height)) };
    }

    function onViewportChanged(opts) {
        opts = opts || {};
        if (opts.width > 0 && opts.height > 0) {
            forcedViewport = {
                width: Math.floor(opts.width),
                height: Math.floor(opts.height),
            };
        }
        var size = viewportSize();
        var width = size.width;
        var height = size.height;
        if (width < 8 || height < 8) {
            scheduleRenderRetry({
                fitOnly: true,
                resetZoom: opts.resetZoom,
                force: opts.force,
                width: opts.width,
                height: opts.height,
            });
            return;
        }
        if (!opts.resetZoom && width === lastVpW && height === lastVpH) {
            return;
        }
        lastVpW = width;
        lastVpH = height;
        if (opts.resetZoom) {
            window.abContributionGraphUserZoomed = false;
        }
        if (payload.kind === "graph") {
            if (window.abContributionGraphUserZoomed && !opts.resetZoom) {
                applyViewportSize(width, height);
                return;
            }
            render({ fitOnly: true });
            return;
        }
        render();
    }

    function scheduleRenderRetry(opts) {
        if (renderRetry || renderRetryCount > 20) {
            return;
        }
        renderRetryCount += 1;
        renderRetry = setTimeout(function () {
            renderRetry = null;
            onViewportChanged(opts || { fitOnly: true });
        }, 50);
    }

    function render(opts) {
        opts = opts || {};
        var tRender = performance.now();
        var style = payload.style || {};
        applyStyle(style);
        syncGraphControls();
        svg.classed("ct-tiers", payload.mode === "icicle" || payload.mode === "tier_bars");
        if (payload.kind === "graph") {
            if (opts.labelsOnly && typeof window.abApplyContributionGraphEdgeLabels === "function") {
                if (window.abApplyContributionGraphEdgeLabels(svg, graphOpts)) {
                    return;
                }
            }
        }
        var size = viewportSize();
        var width = size.width;
        var height = size.height;
        if (opts.fitOnly && payload.kind === "graph" && width >= 8 && height >= 8
                && typeof window.abFitContributionGraph === "function") {
            if (window.abFitContributionGraph(svg, width, height)) {
                return;
            }
        }
        if (width < 8 || height < 8) {
            scheduleRenderRetry(opts);
            return;
        }
        renderRetryCount = 0;
        lastVpW = width;
        lastVpH = height;

        if (payload.kind === "graph") {
            var gnodes = payload.nodes || [];
            if (!gnodes.length) {
                svg.attr("width", width).attr("height", height);
                showEmpty(payload.empty_message || "");
                return;
            }
            hideEmpty();
            svg.attr("width", width).attr("height", height);
            var restore = null;
            if (payload.preserve_view && svg.node()) {
                restore = d3.zoomTransform(svg.node());
            }
            svg.selectAll("*").remove();
            svg.property("_ctGraphState", null);
            var drawOpts = Object.assign({}, graphOpts);
            if (restore && (restore.k !== 1 || restore.x !== 0 || restore.y !== 0)) {
                drawOpts.restoreTransform = restore;
            }
            if (typeof window.abDrawContributionGraph === "function") {
                window.abDrawContributionGraph(svg, payload, drawOpts);
            }
            window.abLastPlotProfile = Object.assign({
                kind: "graph",
                totalMs: performance.now() - tRender,
                nNodes: gnodes.length,
                nEdges: (payload.edges || []).length
            }, window.abLastGraphProfile || {});
            return;
        }

        svg.attr("width", width).attr("height", height);
        svg.selectAll("*").remove();

        var segs = payload.segments || [];
        if (!segs.length) {
            showEmpty(payload.empty_message || "");
            return;
        }
        hideEmpty();
        var g = svg.append("g");
        var maxDirect = payload.max_direct_pct || 100;
        if (payload.mode === "tier_bars") {
            drawTierBars(g, segs, width, height, style, maxDirect);
        } else if (payload.mode === "sunburst") {
            drawSunburst(g, segs, width, height, style, maxDirect);
        } else if (payload.mode === "treemap") {
            drawTreemap(g, segs, width, height, style, maxDirect);
        } else {
            drawIcicle(g, segs, width, height, style, maxDirect);
        }
        window.abLastPlotProfile = Object.assign({
            kind: "partition",
            mode: payload.mode,
            totalMs: performance.now() - tRender,
            nSegs: segs.length
        }, window.abLastDrawProfile || {});
    }

    function updatePlot(jsonText) {
        var t0 = performance.now();
        try {
            payload = JSON.parse(jsonText);
        } catch (err) {
            payload = { mode: "icicle", segments: [], empty_message: "Could not draw plot." };
        }
        var parseMs = performance.now() - t0;
        if (!(payload.kind === "graph" && payload.preserve_view)) {
            window.abContributionGraphUserZoomed = false;
        }
        lastVpW = 0;
        lastVpH = 0;
        render();
        if (window.abLastPlotProfile) {
            window.abLastPlotProfile.parseMs = parseMs;
            window.abLastPlotProfile.jsonChars = jsonText ? jsonText.length : 0;
        }
    }

    d3.select(window).on("resize", function () {
        if (resizeTimer) {
            clearTimeout(resizeTimer);
        }
        resizeTimer = setTimeout(function () {
            resizeTimer = null;
            onViewportChanged();
        }, 150);
    });

    window.abTreeViewportChanged = onViewportChanged;

    if (typeof QWebChannel === "function" && typeof qt !== "undefined") {
        new QWebChannel(qt.webChannelTransport, function (channel) {
            window.bridge = channel.objects.bridge;
            window.bridge.update_plot.connect(updatePlot);
            window.bridge.is_ready();
        });
    }

    window.abUpdateContributionTreePlot = updatePlot;

    window.buildContributionTreeSvgExport = function () {
        var plot = document.getElementById("plot");
        if (!plot) {
            return null;
        }
        var target = plot.querySelector("g.output")
            || plot.querySelector(".ct-graph-inner")
            || plot;
        var bbox;
        try {
            bbox = target.getBBox();
        } catch (err) {
            return null;
        }
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
        out.setAttribute("width", String(vbW));
        out.setAttribute("height", String(vbH));
        out.setAttribute("viewBox", vbX + " " + vbY + " " + vbW + " " + vbH);
        var bg = window.getComputedStyle(document.body).backgroundColor || "#ffffff";
        var backdrop = document.createElementNS(svgNS, "rect");
        backdrop.setAttribute("x", String(vbX));
        backdrop.setAttribute("y", String(vbY));
        backdrop.setAttribute("width", String(vbW));
        backdrop.setAttribute("height", String(vbH));
        backdrop.setAttribute("fill", bg);
        out.appendChild(backdrop);
        if (target === plot) {
            Array.prototype.forEach.call(plot.childNodes, function (child) {
                out.appendChild(child.cloneNode(true));
            });
        } else {
            out.appendChild(target.cloneNode(true));
        }
        return new XMLSerializer().serializeToString(out);
    };
})();
