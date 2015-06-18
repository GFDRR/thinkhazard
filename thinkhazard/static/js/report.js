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

  var defaultTextStyle = new ol.style.Text({
    fill: new ol.style.Fill({
      color: 'black'
    }),
    scale: 0.9,
    stroke: new ol.style.Stroke({
      color: 'rgba(255, 255, 255, 0.6)',
      width: 5
    }),
    text: ''
  });

  var defaultStyles = [
    new ol.style.Style({
      fill: new ol.style.Fill({
        color: 'rgba(0, 0, 0, .1)'
      }),
      stroke: new ol.style.Stroke({
        color: '#000000',
        width: 1
      }),
      text: defaultTextStyle
    })
  ];

  var styleFn = function(feature) {
    defaultTextStyle.setText(feature.get('name'));
    return defaultStyles;
  };

  var hoverTextStyle = new ol.style.Text({
    text: '',
    scale: 1.2,
    stroke: new ol.style.Stroke({
      color: 'white',
      width: 5
    }),
    fill: new ol.style.Fill({
      color: 'black'
    })
  });

  var hoverStyles = [
    new ol.style.Style({
      fill: new ol.style.Fill({
        color: 'rgba(255, 120, 120, .3)'
      }),
      stroke: new ol.style.Stroke({
        color: '#FF5555',
        width: 1
      }),
      text: hoverTextStyle
    })
  ];

  var styleHoverFn = function(feature) {
    hoverTextStyle.setText(feature.get('name'));
    return hoverStyles;
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
