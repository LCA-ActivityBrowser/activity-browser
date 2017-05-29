var diagram = sankeyDiagram()
    .width(1400)
    .height(800)
    .margins({ left: 200, right: 200, top: 10, bottom: 10 })
    .nodeTitle(function(d) { return d.data.title !== undefined ? d.data.title : d.id; })	  
    .linkColor(function(d) { return d.data.color; })
    .duration(500);

//http://bl.ocks.org/eesur/4e0a69d57d3bfc8a82c2
d3.selection.prototype.moveToFront = function() {  
    return this.each(function(){
        this.parentNode.appendChild(this);
      });
};

function update_sankey(json_data){
    var json_data = JSON.parse(json_data)
    d3.select('#sankey')
        .data([json_data])
        .call(diagram)
        .select('svg')
            .selectAll('.link')
            .on('mouseover', function(d) {
                d3.select(this).moveToFront();
            });
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
