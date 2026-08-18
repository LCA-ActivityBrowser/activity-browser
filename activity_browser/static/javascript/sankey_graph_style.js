/* Shared Sankey / tree-plot visual grammar (labels, node size, minimap).
 * Loaded by sankey_navigator.html and contribution_tree_plot.html.
 * Graph explorer does not load this file.
 */
(function (global) {
    "use strict";

    function clamp(num, min, max) {
        return Math.min(Math.max(num, min), max);
    }
    global.clamp = global.clamp || clamp;

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
        .on("drag", function (event) {
            var dgx = event.dx / overviewSc;
            var dgy = event.dy / overviewSc;
            var tr = toTr(lastMain);
            var Tn = d3.zoomIdentity.translate(tr.x - dgx * tr.k, tr.y - dgy * tr.k).scale(tr.k);
            zoomMainTo(Tn);
        });

    viewport.call(drag);

    function wheelHandler(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var tr = toTr(lastMain);
        var pt = d3.pointer(ev, layer.node());
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
    var parts = text.split("\n");
    var flow = (parts[0] || "").trim();
    var rest = parts.slice(1);

    function wrapFlowMaxTwoRows(str, cols) {
        var cleaned = String(str || "").replace(/\s+/g, " ").trim();
        if (!cleaned) {
            return "";
        }
        if (cleaned.length <= cols) {
            return cleaned;
        }
        var c1 = cleaned.lastIndexOf(" ", cols);
        var line1 = (c1 > 0 ? cleaned.slice(0, c1) : cleaned.slice(0, cols)).trim();
        var tail = (c1 > 0 ? cleaned.slice(c1 + 1) : cleaned.slice(cols)).trim();
        if (!tail) {
            return line1;
        }
        if (tail.length <= cols) {
            return line1 + "\n" + tail;
        }
        var c2 = tail.lastIndexOf(" ", Math.max(1, cols - 3));
        var line2 = (c2 > 0 ? tail.slice(0, c2) : tail.slice(0, Math.max(1, cols - 3))).trim();
        return line1 + "\n" + line2.replace(/[. ]+$/, "") + "...";
    }

    var out = [];
    if (flow) {
        out.push(wrapFlowMaxTwoRows(flow, maxLen));
    }
    rest.forEach(function (ln) {
        var w = wrapWordsToMaxLineLength(ln, maxLen);
        if (w) {
            out.push(w);
        }
    });
    return out.join("\n");
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
            impactLines.push(abFormatImpactAbs(x) + " " + e.impact_unit);
        }
        if (showRel) {
            var pctRaw = e.impact_pct_total != null ? Number(e.impact_pct_total) : 0;
            if (!isFinite(pctRaw)) {
                pctRaw = 0;
            }
            impactLines.push(abFormatPct(pctRaw) + "%");
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

function escapeHtmlForSankeyTooltip(s) {
    if (s == null) {
        return "";
    }
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

/** Edge hover HTML for tree/Sankey ribbons: same fields and number format as node hover. */
function buildSankeyEdgeTooltipHtml(e) {
    if (!e) {
        return "";
    }
    var html = "";
    var dark = typeof abGraphIsDark === "function" && abGraphIsDark();
    var flow = (e.product || "").trim();
    if (flow) {
        html += abTipRow("Product:", flow, { boldLabel: true });
    }
    if (e.amount != null && isFinite(Number(e.amount))) {
        var u = (e.amount_unit != null && String(e.amount_unit).trim()) || "";
        html += abTipRow(
            "Flow amount:",
            abFormatImpactAbs(e.amount) + (u ? " " + u : ""),
            { boldLabel: true }
        );
    }
    var pathPct = e.impact_pct_total;
    var iunit = e.impact_unit || "";
    if (pathPct != null && isFinite(Number(pathPct))) {
        html += abTipRow(
            "Path impact:",
            abFormatPct(pathPct) + "% (" +
                abFormatImpactAbs(e.impact_cumulative) +
                (iunit ? " " + iunit : "") +
                ")",
            {
                color: typeof abPathImpactTextColor === "function"
                    ? abPathImpactTextColor(pathPct, dark)
                    : undefined,
                boldLabel: true,
            }
        );
    }
    if (!html) {
        return e.tooltip ? String(e.tooltip) : "";
    }
    return html;
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

function truncateSankeyLineToCols(text, maxCols) {
    var cleaned = String(text || "").replace(/\s+/g, " ").trim();
    if (!cleaned) {
        return "";
    }
    var cols = Math.max(1, maxCols);
    if (cleaned.length <= cols) {
        return cleaned;
    }
    var budget = Math.max(1, cols - 3);
    var cut = cleaned.lastIndexOf(" ", budget);
    var head = (cut > 0 ? cleaned.slice(0, cut) : cleaned.slice(0, budget)).trim();
    return head.replace(/[. ]+$/, "") + "...";
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
        var cols = (wrapCols != null && isFinite(Number(wrapCols)))
            ? Number(wrapCols)
            : sankeyNameMaxColsAt3to1();
        lines.push(truncateSankeyLineToCols(loc, cols));
    }

    var pctStr = "";
    var p = null;
    if (n.direct_emissions_score_normalized != null) {
        p = Number(n.direct_emissions_score_normalized);
    } else if (n.direct_pct != null) {
        p = Number(n.direct_pct) / 100;
    }
    if (p != null && isFinite(p)) {
        pctStr = abFormatPct(p * 100) + "%";
    }
    if (pctStr) {
        lines.push(pctStr);
    }
    return lines.join("\n");
}

    function abGraphIsDark() {
        if (document.documentElement.classList.contains("ab-dark")) {
            return true;
        }
        if (document.documentElement.classList.contains("ab-light")) {
            return false;
        }
        return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    }

    function abApplyGraphTheme(dark) {
        var on = dark == null ? abGraphIsDark() : !!dark;
        document.documentElement.classList.toggle("ab-dark", on);
        document.documentElement.classList.toggle("ab-light", !on);
        document.documentElement.style.colorScheme = on ? "only dark" : "only light";
        if (document.body) {
            document.body.classList.toggle("ab-dark", on);
        }
        abSankeyDirectFill._scale = null;
        abSankeyDirectFill._key = null;
    }

    function abLockGraphTheme(dark) {
        document.documentElement.setAttribute("data-ab-theme-locked", "1");
        abApplyGraphTheme(!!dark);
        if (typeof global.abOnGraphThemeChanged === "function") {
            global.abOnGraphThemeChanged(!!dark);
        }
    }

    function abSankeyDirectFill(normalized) {
        var v = Number(normalized);
        if (!isFinite(v) || v === 0) {
            return abGraphIsDark() ? "#3a3a3a" : "#ffffff";
        }
        return abDirectImpactFill(v * 100, abGraphIsDark());
    }

    function abSankeyTriangleTransform(rankdir, nodeWidth, nodeHeight) {
        var dir = abNormalizeRankdir(rankdir);
        var w = nodeWidth || 80;
        var h = nodeHeight || 50;
        if (dir === "RL") {
            return "translate(" + (w / 2 + 8) + ", 0) rotate(90)";
        }
        if (dir === "TB") {
            return "translate(0, " + (-h / 2 - 8) + ")";
        }
        return "translate(0, " + (h / 2 + 10) + ") rotate(180)";
    }

    function abDemandIdSet(nodes) {
        var ids = {};
        (nodes || []).forEach(function (n) {
            if (n && n.class === "demand" && n.id != null) {
                ids[String(n.id)] = true;
            }
        });
        return ids;
    }

    function abLayoutEdgeWeight(e, demandIds) {
        /* Bias dagre FAS so supplier→RF stays the forward edge. In BT that
         * places the reference flow at the top (sink) and suppliers below. */
        var w = Number(e && e.weight) || 1;
        if (!demandIds) {
            return w;
        }
        if (demandIds[String(e.target_id)]) {
            return Math.max(w, 10);
        }
        if (demandIds[String(e.source_id)]) {
            return 0.001;
        }
        return w;
    }

    var AB_SANKEY_EDGE_MIN_STROKE = 1;
    var AB_SANKEY_EDGE_LAYOUT_MAX = 40;
    var AB_SANKEY_EDGE_MAX_STROKE = 48;

    function abEdgeStrokeWidth(weight) {
        var t = Math.abs(Number(weight) || 0) / AB_SANKEY_EDGE_LAYOUT_MAX;
        return Math.max(AB_SANKEY_EDGE_MIN_STROKE, t * AB_SANKEY_EDGE_MAX_STROKE);
    }

    function abNormalizeRankdir(dir) {
        /* Horizontal = RF on the left (dagre RL). Legacy "LR" maps the same way. */
        return (dir === "LR" || dir === "RL") ? "RL" : "BT";
    }

    function abLogIntensity(value, columnMax) {
        var absv = Math.abs(Number(value) || 0);
        var hi = Math.abs(Number(columnMax) || 0);
        if (!(hi > 0) || absv === 0) {
            return 0;
        }
        var lo = Math.max(hi * 0.01, 1e-12);
        if (lo >= hi) {
            return absv >= hi ? 1 : 0;
        }
        var v = Math.min(Math.max(absv, lo), hi);
        return (Math.log(v) / Math.LN10 - Math.log(lo) / Math.LN10) /
            (Math.log(hi) / Math.LN10 - Math.log(lo) / Math.LN10);
    }

    function abDirectImpactSign(directPct) {
        var pct = Number(directPct) || 0;
        if (pct > 0) {
            return 1;
        }
        if (pct < 0) {
            return -1;
        }
        return 0;
    }

    /* Direct fill vs total score (100%). Log scale; floor keeps small shares visible. */
    function abDirectImpactFill(directPct, dark) {
        var sign = abDirectImpactSign(directPct);
        if (sign === 0) {
            return dark ? "#2a2a2a" : "#ffffff";
        }
        var t = abLogIntensity(directPct, 100);
        var alpha = (0.38 + 0.62 * t).toFixed(3);
        if (sign < 0) {
            return dark
                ? "rgba(102,187,106," + alpha + ")"
                : "rgba(30,122,69," + alpha + ")";
        }
        return dark
            ? "rgba(66,165,245," + alpha + ")"
            : "rgba(21,101,192," + alpha + ")";
    }

    function abDirectImpactTextColor(directPct, dark) {
        var sign = abDirectImpactSign(directPct);
        if (sign === 0) {
            return dark ? "#cccccc" : "#444444";
        }
        var t = abLogIntensity(directPct, 100);
        var mute = dark
            ? (sign < 0 ? "#7a9e7e" : "#64b5f6")
            : (sign < 0 ? "#5a9e72" : "#5b8ec9");
        var full = dark
            ? (sign < 0 ? "#66bb6a" : "#42a5f5")
            : (sign < 0 ? "#1e7a45" : "#1565c0");
        if (typeof d3 !== "undefined" && d3.interpolateRgb) {
            return d3.interpolateRgb(mute, full)(t);
        }
        return full;
    }

    function abPathImpactTextColor(pathPct, dark) {
        var sign = abDirectImpactSign(pathPct);
        if (sign === 0) {
            return dark ? "#cccccc" : "#444444";
        }
        var t = abLogIntensity(pathPct, 100);
        var mute = dark
            ? (sign < 0 ? "#7a9e7e" : "#c47a7a")
            : (sign < 0 ? "#8bb89a" : "#d08a8a");
        var full = dark
            ? (sign < 0 ? "#66bb6a" : "#ef5350")
            : (sign < 0 ? "#1e7a45" : "#c62828");
        if (typeof d3 !== "undefined" && d3.interpolateRgb) {
            return d3.interpolateRgb(mute, full)(t);
        }
        return full;
    }

    var AB_CATEGORICAL_COLORS = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
        "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab",
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
        "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
        "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
        "#3182bd", "#e6550d", "#31a354", "#756bb1", "#636363",
        "#6baed6", "#fd8d3c", "#74c476", "#9e9ac8", "#969696"
    ];

    function abOrdinalScale(keys) {
        var uniq = Array.from(new Set((keys || []).filter(Boolean)));
        var colors = AB_CATEGORICAL_COLORS.slice();
        if (typeof d3 !== "undefined") {
            ["schemeTableau10", "schemeSet3", "schemePaired", "schemeDark2", "schemeSet2"].forEach(function (name) {
                if (d3[name] && d3[name].length) {
                    d3[name].forEach(function (c) {
                        if (colors.indexOf(c) === -1) {
                            colors.push(c);
                        }
                    });
                }
            });
        }
        var i = 0;
        while (colors.length < uniq.length && typeof d3 !== "undefined" && d3.interpolateRainbow) {
            colors.push(d3.interpolateRainbow((i + 0.5) / (uniq.length + 1)));
            i += 1;
        }
        return d3.scaleOrdinal(colors).domain(uniq);
    }

    function abFormatImpactAbs(value) {
        var n = Number(value);
        if (!isFinite(n)) {
            return "0";
        }
        var a = Math.abs(n);
        if (a >= 100) {
            return n.toFixed(2);
        }
        if (a >= 1) {
            return n.toFixed(3);
        }
        if (a >= 0.01) {
            return n.toFixed(4);
        }
        return n.toExponential(2);
    }

    function abFormatPct(value) {
        var n = Number(value);
        if (!isFinite(n)) {
            return "0.00";
        }
        return n.toFixed(2);
    }

    var AB_AGGREGATE_LABELS = {
        product: "Product",
        name: "Process",
        location: "Location",
        unit: "Unit",
        database: "Database",
    };

    function abTipRow(label, value, opts) {
        opts = opts || {};
        var esc = escapeHtmlForSankeyTooltip;
        var style = opts.color ? " style=\"color:" + opts.color + "\"" : "";
        var lab = opts.boldLabel
            ? "<b>" + esc(label) + "</b>"
            : esc(label);
        var val = opts.boldValue
            ? "<b>" + esc(value) + "</b>"
            : esc(value);
        return "<div" + style + ">" + lab + " " + val + "</div>";
    }

    function abContributionTooltipHtml(d, unit) {
        if (!d) {
            return "";
        }
        unit = unit || d.unit || "";
        var html = "";
        var dark = abGraphIsDark();
        if (d.is_aggregate) {
            var field = d.aggregate_by || "";
            var aggLabel = AB_AGGREGATE_LABELS[field] || field;
            if (aggLabel && d.aggregate_key) {
                html += abTipRow(aggLabel + ":", d.aggregate_key, { boldLabel: true });
            }
            var n = (d.constituent_uids || []).length;
            if (n) {
                html += "<div>Processes: " + n + "</div>";
            }
            var products = d.constituent_products || [];
            products.slice(0, 5).forEach(function (name) {
                html += "<div>• " + escapeHtmlForSankeyTooltip(name) + "</div>";
            });
            if (products.length > 5) {
                html += "<div>… and " + (products.length - 5) + " more</div>";
            }
        } else {
            if (d.product) {
                html += abTipRow("Product:", d.product, { boldLabel: true });
            }
            var process = d.process || d.name;
            if (process) {
                html += abTipRow("Process:", process, { boldLabel: true });
            }
            var loc = String(d.location || "").trim();
            if (loc) {
                html += abTipRow("Location:", loc, { boldLabel: true });
            }
            if (d.database) {
                html += abTipRow("Database:", d.database, { boldLabel: true });
            }
        }
        if (d.tier != null && d.tier !== "") {
            html += "<div>Tier: " + escapeHtmlForSankeyTooltip(String(d.tier)) + "</div>";
        }
        var pathPct = d.path_pct != null ? d.path_pct : d.cumulative_pct;
        var pathScore = d.cumulative_score;
        if (pathPct != null && isFinite(Number(pathPct))) {
            html += abTipRow(
                "Path impact:",
                abFormatPct(pathPct) + "% (" +
                    abFormatImpactAbs(pathScore) +
                    (unit ? " " + unit : "") +
                    ")",
                { color: abPathImpactTextColor(pathPct, dark), boldLabel: true }
            );
        }
        var directPct = Number(d.direct_pct) || 0;
        var directColor = abDirectImpactTextColor(directPct, dark);
        html += abTipRow(
            "Direct impact:",
            abFormatPct(directPct) + "% (" +
                abFormatImpactAbs(d.direct_emissions_score) +
                (unit ? " " + unit : "") +
                ")",
            { color: directColor, boldLabel: true }
        );
        return html;
    }

    function abPlaceHtmlTooltip(sel, event, html) {
        if (!sel || !sel.node) {
            return;
        }
        var node = sel.node();
        if (!node) {
            return;
        }
        sel.attr("hidden", null).html(html || "");
        var tw = node.offsetWidth || 0;
        var th = node.offsetHeight || 0;
        var pad = 8;
        var vw = window.innerWidth || tw;
        var vh = window.innerHeight || th;
        var x = event.pageX + 12;
        var y = event.pageY + 12;
        if (x + tw > vw - pad) {
            x = event.pageX - tw - 12;
        }
        if (x < pad) {
            x = pad;
        }
        if (y + th > vh - pad) {
            y = event.pageY - th - 12;
        }
        if (y < pad) {
            y = pad;
        }
        sel.style("left", x + "px").style("top", y + "px");
    }

    function abOpenProcessPayload(d) {
        d = d || {};
        var visit = (d.visit_id != null && d.visit_id !== "")
            ? d.visit_id
            : (d.unique_id != null && d.unique_id !== ""
                ? d.unique_id
                : (d.click_uid != null && d.click_uid !== "" ? d.click_uid : d.id));
        return {
            visit_id: visit,
            unique_id: visit,
            activity_id: d.activity_id != null ? d.activity_id : null,
            database: d.database || "",
            code: d.code || "",
            is_aggregate: !!d.is_aggregate,
            constituent_uids: d.constituent_uids || [],
            mouse: 2
        };
    }

    global.abGraphIsDark = abGraphIsDark;
    global.abApplyGraphTheme = abApplyGraphTheme;
    global.abLockGraphTheme = abLockGraphTheme;
    global.abSankeyTriangleTransform = abSankeyTriangleTransform;
    global.abNormalizeRankdir = abNormalizeRankdir;
    global.abDemandIdSet = abDemandIdSet;
    global.abLayoutEdgeWeight = abLayoutEdgeWeight;
    global.abEdgeStrokeWidth = abEdgeStrokeWidth;
    global.abCreateSankeyPanMinimap = abCreateSankeyPanMinimap;
    global.wrapWordsToMaxLineLength = wrapWordsToMaxLineLength;
    global.wrapSankeyEdgeLabelMultiline = wrapSankeyEdgeLabelMultiline;
    global.formatSankeyTwoLineEdgeLabel = formatSankeyTwoLineEdgeLabel;
    global.escapeHtmlForSankeyTooltip = escapeHtmlForSankeyTooltip;
    global.buildSankeyEdgeTooltipHtml = buildSankeyEdgeTooltipHtml;
    global.inferSankeyEdgeLabelMaxCols = inferSankeyEdgeLabelMaxCols;
    global.inferSankeyNodeInnerWidthPx = inferSankeyNodeInnerWidthPx;
    global.inferSankeyNodeWrapColsFromWidth = inferSankeyNodeWrapColsFromWidth;
    global.buildSankeyProcessNameLines = buildSankeyProcessNameLines;
    global.formatSankeyNodePlainTextLabel = formatSankeyNodePlainTextLabel;
    global.abSankeyDirectFill = abSankeyDirectFill;
    global.abLogIntensity = abLogIntensity;
    global.abDirectImpactFill = abDirectImpactFill;
    global.abDirectImpactTextColor = abDirectImpactTextColor;
    global.abPathImpactTextColor = abPathImpactTextColor;
    global.abOrdinalScale = abOrdinalScale;
    global.abFormatImpactAbs = abFormatImpactAbs;
    global.abFormatPct = abFormatPct;
    global.abContributionTooltipHtml = abContributionTooltipHtml;
    global.abPlaceHtmlTooltip = abPlaceHtmlTooltip;
    global.abOpenProcessPayload = abOpenProcessPayload;
    global.AB_SANKEY_NODE_INNER_HEIGHT_PX = AB_SANKEY_NODE_INNER_HEIGHT_PX;
    global.AB_SANKEY_NODE_PADDING_X = AB_SANKEY_NODE_PADDING_X;
    global.AB_SANKEY_NODE_PADDING_Y = AB_SANKEY_NODE_PADDING_Y;

    if (document.documentElement.getAttribute("data-ab-theme-locked") !== "1") {
        document.documentElement.classList.add("ab-light");
        abApplyGraphTheme(false);
    }
    if (window.matchMedia) {
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (ev) {
            if (document.documentElement.getAttribute("data-ab-theme-locked") === "1") {
                return;
            }
            abApplyGraphTheme(ev.matches);
        });
    }
})(typeof window !== "undefined" ? window : globalThis);
