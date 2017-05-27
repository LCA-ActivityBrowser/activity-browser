var diagram = sankeyDiagram()
    .width(1400)
    .height(800)
    .margins({ left: 200, right: 200, top: 10, bottom: 10 })
    .nodeTitle(function(d) { return d.data.title !== undefined ? d.data.title : d.id; })	  
    .linkColor(function(d) { return d.data.color; })
    .duration(500);

function update_sankey(json_data){
    var json_data = JSON.parse(json_data)
    d3.select('#sankey')
        .data([json_data])
        .call(diagram);
}

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
