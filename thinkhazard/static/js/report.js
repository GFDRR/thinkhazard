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
    ]
  });
  map.getView().fitExtent(app.divisionBounds, map.getSize());

  var extent = map.getView().calculateExtent(map.getSize());

  var defFill = new ol.style.Fill({color: 'rgba(0, 0, 0, .1)'});
  var defStroke = new ol.style.Stroke({
    color: '#000000',
    width: 1
  });
  var defTextStroke = new ol.style.Stroke({
    color: 'rgba(255, 255, 255, 0.6)',
    width: 5
    });
  var defTextFill = new ol.style.Fill({
    color: 'black'
  });
  var styleFn = function(feature) {
    return [new ol.style.Style({
      fill: defFill,
      stroke: defStroke,
      text: new ol.style.Text({
        text: feature.get('name'),
        scale: 0.9,
        stroke: defTextStroke,
        fill: defTextFill
      })
    })];
  };

  var hoverFill = new ol.style.Fill({
    color: 'rgba(255, 120, 120, .3)'
  });
  var hoverStroke = new ol.style.Stroke({
    color: '#FF5555',
    width: 1
  });
  var hoverTextStroke = new ol.style.Stroke({
    color: 'white',
    width: 5
  });
  var hoverFillStroke = new ol.style.Fill({
    color: 'black'
  });
  var styleHoverFn = function(feature) {
    return [new ol.style.Style({
      fill: hoverFill,
      stroke: hoverStroke,
      text: new ol.style.Text({
        text: feature.get('name'),
        scale: 1.2,
        stroke: hoverTextStroke,
        fill: hoverFillStroke
      })
    })];
  };

  var vector = new ol.layer.Vector({
    style: styleFn,
    source: new ol.source.Vector({
      url: app.mapUrl,
      format: new ol.format.GeoJSON({
        defaultDataProjection: 'EPSG:3857'
      })
    })
  });
  map.addLayer(vector);
  window.source = vector.getSource();

  var select = new ol.interaction.Select({
    layers: [vector],
    condition: ol.events.condition.pointerMove,
    style: styleHoverFn
  });
  map.addInteraction(select);

  // change mouse cursor when over division
  map.on('pointermove', function(e) {
    var pixel = map.getEventPixel(e.originalEvent);
    var hit = map.hasFeatureAtPixel(pixel);
    map.getTargetElement().style.cursor = hit ? 'zoom-in' : '';
  });
})();
