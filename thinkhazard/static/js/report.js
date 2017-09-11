(function() {

  // Tells whether all the background layer tiles are loaded
  var tilesLoaded = false;

  // Tells whether the vector layer is displayed
  var vectorLoaded = false;

  //
  // Main
  //
  var source = new ol.source.XYZ({
    url: 'https://api.mapbox.com/styles/v1/stufraser1/cj3g19csf00062sjso7dfj4ns/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1Ijoic3R1ZnJhc2VyMSIsImEiOiJQdnhvZTlnIn0.SEC9tGQDtw9yPQssVyF-8Q'
  });
  waitForTiles();

  var map = new ol.Map({
    target: 'map',
    interactions: [],
    controls: [],
    layers: [
      new ol.layer.Tile({
        source: source
      })
    ]
  });

  var bounds = ol.proj.transformExtent(app.divisionBounds, 'EPSG:4326',
      'EPSG:3857');
      map.getView().fit(bounds, map.getSize(), {
        padding: [30, 0, 0, 0]
      });

  map.addControl(new ol.control.ScaleLine());

  var neighboursLayer = addNeighboursVectorLayer(map, app.neighboursUrl);
  var levelLayer;
  if (app.hazardType) {
    levelLayer = addLevelLayer(map, app.mapUrl);
  }
  var adminLayer = addAdminLayer(map, app.mapUrl);

  addSelectInteraction(map, [adminLayer, neighboursLayer]);

  var tooltipEl = $('#map .map-tooltip');

  var hitTolerance = 3;

  // change mouse cursor when over division
  map.on('pointermove', function(e) {
    var feature = map.forEachFeatureAtPixel(e.pixel, filterFn, {
      hitTolerance: hitTolerance
    });
    var cursor = '';

    tooltipEl.empty().removeClass('neighbour').hide();
    if (feature) {
      var html;
      if (feature.get('neighbour')) {
        cursor = 'pointer';
        tooltipEl.addClass('neighbour');
        if (app.goToString) {
          html = app.goToString.replace('name_of_location',
              '<b>' + feature.get('name') + '</b>');
        }
      } else {
        cursor = 'zoom-in';
        if (app.zoomInString) {
          html = app.zoomInString.replace('name_of_location',
              '<b>' + feature.get('name') + '</b>');
        }
      }
      if (feature.get('hazardLevelMnemonic') &&
          feature.get('hazardLevelMnemonic') != 'None') {
        html += '<br/><em>' + app.levelString[feature.get('hazardLevelTitle')] + '</em>';
      }
      tooltipEl.show()
        .css({
          top: e.pixel[1] + 10,
          left: e.pixel[0] + 10
        })
        .html(html);
    }
    map.getTargetElement().style.cursor = cursor;

  });

  map.getViewport().addEventListener('mouseout', function(evt) {
    tooltipEl.hide();
  });

  // drill down
  map.on('click', function(e) {
    var feature = map.forEachFeatureAtPixel(e.pixel, filterFn, {
      hitTolerance: hitTolerance
    });
    if (feature) {
      var url = feature.get('url');
      if (app.hazardType) {
        url += '/' + app.hazardType;
      }
      window.location = url;
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
  function addNeighboursVectorLayer(map, url) {
    var styleFn = function(feature) {
      var styles = [
        new ol.style.Style({
          fill: new ol.style.Fill({
            color: 'rgba(1, 1, 1, 0)'
          }),
          stroke: new ol.style.Stroke({
            color: '#337ab7',
            width: 0.2
          })
        })
      ];
      return styles;
    };

    var extent = ol.proj.transformExtent(
      map.getView().calculateExtent(map.getSize()), 'EPSG:3857', 'EPSG:4326');
    url = [
      url,
      '?resolution=' + map.getView().getResolution(),
      '&bbox=' + extent
    ].join('');
    var source = new ol.source.Vector({
      url: url,
      format: new ol.format.GeoJSON({
        defaultDataProjection: 'EPSG:3857'
      })
    });
    var layer = new ol.layer.Vector({
      style: styleFn,
      source: source
    });
    map.addLayer(layer);
    source.on('addfeature', function(event) {
      var f = event.feature;
      f.set('neighbour', true);
    });
    return layer;
  }


  /**
   * @param {ol.Map} map
   * @param {string} url
   * @return {ol.layer.Vector}
   */
  function addAdminLayer(map, url) {
    var styleFn = function(feature) {
      var styles = [
        new ol.style.Style({
          stroke: new ol.style.Stroke({
            color: '#333',
            width: isSubDivision(feature) ? 0.5 : 1.5
          })
        })
      ];
      return styles;
    };

    var source = new ol.source.Vector({
      url: url + '?resolution=' + map.getView().getResolution(),
      format: new ol.format.GeoJSON({
        defaultDataProjection: 'EPSG:3857'
      })
    });
    var layer = new ol.layer.Vector({
      style: styleFn,
      source: source
    });
    map.addLayer(layer);
    source.on('addfeature', function() {
      map.on('postcompose', function(event) {
        vectorLoaded = true;
        checkFinished();
      });
    });
    return layer;
  }


  /**
   * @param {ol.Map} map
   * @param {string} url
   * @return {ol.layer.Vector}
   */
  function addLevelLayer(map, url) {
    var styleFn = function(feature) {
      var fillColors = getFillColors(0.75);
      var transparent = 'rgba(1, 1, 1, 0)';
      var fillStyle = new ol.style.Fill({
        color: fillColors[feature.get('hazardLevelMnemonic')]
      });
      var styles = [
        new ol.style.Style({
          fill: fillStyle
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
    var source = new ol.source.Vector({
      url: url + '?resolution=' + map.getView().getResolution(),
      format: new ol.format.GeoJSON({
        defaultDataProjection: 'EPSG:3857'
      })
    });
    var layer = new ol.layer.Vector({
      style: styleFn,
      source: source
    });
    map.addLayer(layer);
    source.on('addfeature', function() {
      map.on('postcompose', function(event) {
        vectorLoaded = true;
        checkFinished();
      });
    });
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
   * @param {Array.<ol.layer.Vector>} layers
   * @return {ol.interaction.Select}
   */
  function addSelectInteraction(map, layers) {
    var strokeStyle = new ol.style.Stroke({
      color: '',
      width: 2
    });

    var styles = [
      new ol.style.Style({
        stroke: strokeStyle
      })
    ];
    var styleFn = function(feature) {
      var strokeColor = feature.get('neighbour') ? '#333' : '#000000';
      strokeStyle.setColor(strokeColor);
      var strokeWidth = feature.get('neighbour') ? 1 : 2;
      strokeStyle.setWidth(strokeWidth);
      return styles;
    };
    var interaction = new ol.interaction.Select({
      layers: layers,
      condition: ol.events.condition.pointerMove,
      style: styleFn,
      filter: isSubDivision,
      hitTolerance: hitTolerance
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
      'HIG': [189, 0, 38, opacity],
      'MED': [240, 59, 32, opacity],
      'LOW': [253, 141, 60, opacity],
      'VLO': [254, 204, 92, opacity]
    };
  }

  $('#download').on('click', function(e) {
    e.preventDefault();
    $.post(app.createPdfReportUrl)
      .done(function(data) {
        btnStatus(true);
        checkPdfStatus(data.report_id);
      })
      .error(function() {
        alert("Something went wrong");
        btnStatus(false);
      });
  });

  function checkPdfStatus(id) {
    var url = app.getReportStatusUrl.replace(999, id);
    $.get(url, {salt: new Date().getTime()})
      .done(function(data) {
        if (data.status == 'running') {
          window.setTimeout(function() {
            checkPdfStatus(id);
          }, 1000);
        } else {
          btnStatus(false);
          downloadPdf(id);
        }
      })
      .error(function() {
        alert("Something went wrong");
        btnStatus(false);
      });
  }

  function downloadPdf(id) {
    window.location.href = app.getPdfReportUrl.replace(999, id);
  }

  // status:
  // true: generating, false: finished
  function btnStatus(status) {
    $('#download').find('.fa-spin').toggleClass('hide', !status);
    $('#download').find('.icon-download-arrow').toggleClass('hide', status);
    $('#download').attr('disabled', status);
  }

  function waitForTiles() {
    var tilesLoading = 0;
    var tilesLoaded = 0;

    var update = function() {
      if (tilesLoading == tilesLoaded) {
        onTilesLoaded();
      }
    };

    source.on('tileloadstart', function(event) {
      tilesLoading++;
    });
    source.on('tileloadend', function(event) {
      tilesLoaded++;
      update();
    });
  }

  function onTilesLoaded() {
    tilesLoaded = true;
    checkFinished();
  }

  function checkFinished() {
    if (vectorLoaded && tilesLoaded) {
      window.status = 'finished';
      $('#map').addClass('finished');
    }
  }

  $('.data-source a').on('click', function(e) {
    e.preventDefault();
    $('#data-source-modal').modal('show').find('.modal-body').load($(this).attr('href'));
  });

  // initialize tooltips
  if ($('body').tooltip) {
    $('body').tooltip({
      container: 'body',
      trigger: 'hover',
      selector: '[data-toggle="tooltip"]'
    });
  }

  var blkImgSrc = new ol.source.ImageStatic({
    imageExtent: map.getView().calculateExtent(map.getSize()),
    url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
  });
  var dataSourceLayer = new ol.layer.Image({
    source: blkImgSrc
  });
  map.addLayer(dataSourceLayer);
  $('#level-map-btn').on('click', function(e) {
    e.preventDefault();

    var el = $(this);
    dataSourceLayer.setVisible(false);
    levelLayer.setVisible(true);
    $('#data-source-map-btn').removeClass('hidden');
    el.addClass('hidden');
    $('#level-legend').removeClass('hidden');
    $('#data-source-legend').addClass('hidden');
  });

  var dataSourceSource;
  var updateLegend = function(layerName) {
    $('#data-source-legend img').attr('src',
      'http://www.geonode-gfdrrlab.org/geoserver/hazard/ows' +
      '?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&FORMAT=image%2Fpng' +
      '&LAYER=' + layerName
    ).on('error', function() {
      $('#data-source-legend')
        .find('.service-warning').show().end()
        .children('div').hide().end();
      $(this).hide();
    });
  };
  $('#data-source-map-btn a').on('click', function(e) {
    e.preventDefault();
    dataSourceSource = new ol.source.ImageWMS({
      url: 'http://www.geonode-gfdrrlab.org/geoserver/hazard/ows',
      params: {'LAYERS': $('.current-rp').attr('data-name')},
      serverType: 'geoserver'
    });
    updateLegend($('.current-rp').attr('data-name'));
    dataSourceLayer.setSource(dataSourceSource);
    dataSourceLayer.setVisible(true);
    levelLayer.setVisible(false);
    $('#level-map-btn').removeClass('hidden');
    $('#data-source-map-btn').addClass('hidden');
    $('#level-legend').addClass('hidden');
    $('#data-source-legend').removeClass('hidden');
  });

  $('.rp-chooser').on('click', function(e) {
    e.preventDefault();
    $('.rp-chooser').removeClass('current-rp');
    $(this).addClass('current-rp');
    updateLegend($('.current-rp').attr('data-name'));
    dataSourceSource.updateParams({
      LAYERS: $(this).attr('data-name')
    });
  });

  $('.search .input-group-addon').on('click', function() {
    $('.navbar').toggleClass('search-focused');
    if ($('.navbar').hasClass('search-focused')) {
      $('.tt-input').focus();
    }
  });
  $('.tt-input').on('blur', function() {
    $('.navbar').removeClass('search-focused');
  });

})();
