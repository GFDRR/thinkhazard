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
  // we don't need an image bigger than the division area
  var width = (bounds[2] - bounds[0]) / map.getView().getResolution();
  var height = (bounds[3] - bounds[1]) / map.getView().getResolution();

  var extent = map.getView().calculateExtent(map.getSize());
  var params = {
    width: Math.round(width),
    height: Math.round(height),
    divisioncode: app.divisionCode
  };
  if (app.hazardType) {
      params.hazardtype = app.hazardType;
  }
  var url = app.mapImgUrl + '?' + $.param(params);
  hazardLayer.setSource(new ol.source.ImageStatic({
    url: url,
    imageExtent: app.divisionBounds
  }));
})();
