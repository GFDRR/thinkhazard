(function() {

  var map = new ol.Map({
    target: 'map',
    interactions: [],
    controls: [],
    layers: [
      new ol.layer.Tile({
        source: new ol.source.Stamen({
          layer: 'watercolor'
        }),
        opacity: 0.5
      })
    ],
    view: new ol.View({ })
  });
  map.getView().fitExtent(app.divisionBounds, map.getSize());

  var hazardLayer = new ol.layer.Image({});
  map.addLayer(hazardLayer);


  var bounds = app.divisionBounds;

  var extent = map.getView().calculateExtent(map.getSize());

  var vector = new ol.layer.Vector({
    source: new ol.source.Vector({
      url: app.mapUrl,
      format: new ol.format.GeoJSON({
        defaultDataProjection: 'EPSG:3857'
      })
    })
  });
  map.addLayer(vector);
  window.source = vector.getSource();
})();
