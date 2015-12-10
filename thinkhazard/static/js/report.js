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
        source: new ol.source.XYZ({
          url: 'https://{a-c}.tiles.mapbox.com/v4/ingenieroariel.m9a2h374/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoiaW5nZW5pZXJvYXJpZWwiLCJhIjoibXhDZ3pIMCJ9.qTmPYCbnUKtaNFkvKKysAQ'
        })
      })
    ]
  });
  var bounds = ol.proj.transformExtent(app.divisionBounds, 'EPSG:4326',
      'EPSG:3857');
  map.getView().fit(bounds, map.getSize());

  map.addControl(new ol.control.ScaleLine());

  var vectorLayer = addVectorLayer(map, app.mapUrl);

  if (app.leveltype < 3) {
    addSelectInteraction(map, vectorLayer);

    // change mouse cursor when over division
    map.on('pointermove', function(e) {
      var feature = map.forEachFeatureAtPixel(e.pixel, filterFn);
      map.getTargetElement().style.cursor = feature ? 'zoom-in' : '';

      $('#map .tooltip').empty().hide();
      if (feature) {
        var html = 'Zoom in to <b>' + feature.get('name') + '</b>';
        if (feature.get('hazardLevelMnemonic') != 'None') {
          html += '<br/><em>' + feature.get('hazardLevelTitle') + '</em>';
        }
        $('#map .tooltip').show()
          .css({
            top: e.pixel[1] + 10,
            left: e.pixel[0] + 10
          })
          .html(html);
      }
    });

    // drill down
    map.on('click', function(e) {
      var feature = map.forEachFeatureAtPixel(e.pixel, filterFn);
      if (feature) {
        var code = feature.get('code');
        window.location = app.reportpageUrl.replace('__divisioncode__', code);
      }
    });
  }


  //
  // Functions
  //


  /**
   * @param {ol.Map} map
   * @param {string} url
   * @return {ol.layer.Vector}
   */
  function addVectorLayer(map, url) {
    var styleFn = function(feature) {
      var fillColors = getFillColors(0.75);
      var transparent = 'rgba(1, 1, 1, 0)';
      var fillStyle = new ol.style.Fill({
        color: fillColors[feature.get('hazardLevelMnemonic')] || transparent
      });
      var styles = [
        new ol.style.Style({
          fill: fillStyle,
          stroke: new ol.style.Stroke({
            color: '#333',
            width: isSubDivision(feature) ? 0.5 : 1.5
          })
        })
      ];
      // More than one feature indicates that there are subdivision. We still
      // want to show the parent division but with no fill.
      if (layer.getSource().getFeatures().length > 1 &&
          !isSubDivision(feature)) {
        fillStyle.setColor(transparent);
      }
      return styles;
    };
    var layer = new ol.layer.Vector({
      style: styleFn,
      source: new ol.source.Vector({
        url: url + '?resolution=' + map.getView().getResolution(),
        format: new ol.format.GeoJSON({
          defaultDataProjection: 'EPSG:3857'
        })
      })
    });
    map.addLayer(layer);
    return layer;
  }


  /**
   * @param {ol.Feature} feature
   * @return {?ol.Feature}
   */
  function filterFn(feature) {
    if (isSubDivision(feature)) {
      return feature;
    }
  }


  /**
   * @param {ol.Feature} feature
   * @return {boolean}
   */
  function isSubDivision(feature) {
    return feature.get('code') != app.divisionCode;
  }


  /**
   * @param {ol.Map} map
   * @param {ol.layer.Vector} layer
   * @return {ol.interaction.Select}
   */
  function addSelectInteraction(map, layer) {
    var fillColors = getFillColors(1);
    var fillStyle = new ol.style.Fill({
      color: ''
    });
    var styles = [
      new ol.style.Style({
        fill: fillStyle,
        stroke: new ol.style.Stroke({
          color: '#000000',
          width: 2
        })
      })
    ];
    var styleFn = function(feature) {
      var hazardLevel = feature.get('hazardLevelMnemonic');
      var fillColor = hazardLevel in fillColors ?
          fillColors[hazardLevel] : 'rgba(255, 255, 255, 0.5)';
      fillStyle.setColor(fillColor);
      return styles;
    };
    var interaction = new ol.interaction.Select({
      layers: [layer],
      condition: ol.events.condition.pointerMove,
      style: styleFn,
      filter: isSubDivision
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
      'HIG': [217, 31, 45, opacity],
      'MED': [223, 113, 32, opacity],
      'LOW': [223, 156, 32, opacity],
      'VLO': [223, 187, 32, opacity]
    };
  }

})();
