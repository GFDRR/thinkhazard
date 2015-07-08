(function() {


  //
  // Main
  //


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

  var vectorLayer = addVectorLayer(map, app.mapUrl);
  addSelectInteraction(map, vectorLayer);

  // change mouse cursor when over division
  map.on('pointermove', function(e) {
    var pixel = map.getEventPixel(e.originalEvent);
    var hit = map.hasFeatureAtPixel(pixel);
    map.getTargetElement().style.cursor = hit ? 'zoom-in' : '';
  });

  // drill down
  map.on('click', function(e) {
    var feature = map.forEachFeatureAtPixel(e.pixel, function(feature) {
      return feature;
    });
    if (feature) {
      var code = feature.get('code');
      window.location = app.reportpageUrl.replace('__divisioncode__', code);
    }
  });


  //
  // Functions
  //


  /**
   * @param {ol.Map} map
   * @param {string} url
   * @return {ol.layer.Vector}
   */
  function addVectorLayer(map, url) {
    var textStyle = new ol.style.Text({
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
    var fillColors = getFillColors(0.5);
    var fillStyle = new ol.style.Fill({
      color: ''
    });
    var styles = [
      new ol.style.Style({
        fill: fillStyle,
        stroke: new ol.style.Stroke({
          color: '#333',
          width: 1
        }),
        text: textStyle
      })
    ];
    var styleFn = function(feature) {
      textStyle.setText(feature.get('name'));
      var hazardLevel = feature.get('hazardLevel');
      var fillColor = hazardLevel in fillColors ?
          fillColors[hazardLevel] : 'rgba(1, 1, 1, 0.1)';
      fillStyle.setColor(fillColor);
      return styles;
    };
    var layer = new ol.layer.Vector({
      style: styleFn,
      source: new ol.source.Vector({
        url: url,
        format: new ol.format.GeoJSON({
          defaultDataProjection: 'EPSG:3857'
        })
      })
    });
    map.addLayer(layer);
    return layer;
  }


  /**
   * @param {ol.Map} map
   * @param {ol.layer.Vector} layer
   * @return {ol.interaction.Select}
   */
  function addSelectInteraction(map, layer) {
    var textStyle = new ol.style.Text({
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
    var fillColors = getFillColors(0.9);
    var fillStyle = new ol.style.Fill({
      color: ''
    });
    var styles = [
      new ol.style.Style({
        fill: fillStyle,
        stroke: new ol.style.Stroke({
          color: '#000000',
          width: 2
        }),
        text: textStyle
      })
    ];
    var styleFn = function(feature) {
      textStyle.setText(feature.get('name'));
      var hazardLevel = feature.get('hazardLevel');
      var fillColor = hazardLevel in fillColors ?
          fillColors[hazardLevel] : 'rgba(1, 1, 1, 0.5)';
      fillStyle.setColor(fillColor);
      return styles;
    };
    var interaction = new ol.interaction.Select({
      layers: [layer],
      condition: ol.events.condition.pointerMove,
      style: styleFn
    });
    map.addInteraction(interaction);
    return interaction;
  }


  /**
   * @param {number} opacity
   * @return {Object.<string, Array.<number>>}
   */
  function getFillColors(opacity) {
    return {
      'HIG': [217, 31, 44, opacity],
      'MED': [213, 124, 39, opacity],
      'LOW': [224, 176, 37, opacity],
      'NPR': [142, 157, 146, opacity]
    };
  }

})();
