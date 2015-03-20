(function() {
  var map = new ol.Map({
    target: 'map',
    interactions: ol.interaction.defaults({
      mouseWheelZoom: false
    }),
    layers: [
      new ol.layer.Tile({
        source: new ol.source.OSM()
      })
    ],
    view: new ol.View({
      center: [0, 0],
      zoom: 5
    })
  });
})();
