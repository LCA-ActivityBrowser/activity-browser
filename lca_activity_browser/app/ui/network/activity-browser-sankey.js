var diagram = sankeyDiagram()
    .width(1400)
    .height(800)
    .margins({ left: 200, right: 200, top: 10, bottom: 10 })
    //.nodeTitle(function(d) { return d.data.title !== undefined ? d.data.title : d.id; })	  
    .linkColor(function(d) { return d.data.color; })
    .duration(500);

//http://bl.ocks.org/eesur/4e0a69d57d3bfc8a82c2
d3.selection.prototype.moveToFront = function() {  
    return this.each(function(){
        this.parentNode.appendChild(this);
      });
};

// Tooltip: http://bl.ocks.org/d3noob/a22c42db65eb00d4e369
var div = d3.select("body").append("div")	
    .attr("class", "tooltip")				
    .style("opacity", 0);

// from ipysankeywidget
function style(d) {
    return (d.data || {}).style;
}

function update_sankey(json_data){
    var json_data = JSON.parse(json_data)
    // update sankey with new data
    var sankey = d3.select('#sankey')
        .data([json_data])
        .call(diagram)
        .select('svg')
    // move mouseover element to front and display tooltip 
    sankey.selectAll('.link')
        .on('mouseover', function(d) {
            d3.select(this).moveToFront();
            div.transition()		
                .duration(200)		
                .style("opacity", .9);		
            div	.html(String(d.id))	
                .style("left", (d3.event.pageX) + "px")		
                .style("top", (d3.event.pageY - 28) + "px");	
        })
        .on("mouseout", function(d) {		
            div.transition()		
                .duration(500)		
                .style("opacity", 0);	
        });
    // brute force removal of link titles that show up as svg tooltips
    sankey.selectAll('title').remove()
    // node linewidth
    sankey.selectAll('line')
        .style('stroke', 'black')
        .style('stroke-width', function(d) { return style(d) === 'process' ? '5px' : '1px'; });
};

new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.bridge;
    window.bridge.sankey_ready.connect(update_sankey);
    window.bridge.viewer_ready();
});



diagram.on("selectLink", function(link){
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.bridge = channel.objects.bridge;
        window.bridge.lca_calc_finished.connect(update_sankey);
        window.bridge.link_selected(String(link.id));
        });	
});
