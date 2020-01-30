(function() {
  var mq = '(max-width: 768px)';

  // Tells whether all the background layer tiles are loaded
  var tilesLoaded = false;

  // Tells whether the vector layer is displayed
  var vectorLoaded = false;

  //
  // Main
  //
  var sources = [
    'https://api.mapbox.com/styles/v1/stufraser1/cjftf111617x32spjhncapgm2/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1Ijoic3R1ZnJhc2VyMSIsImEiOiJQdnhvZTlnIn0.SEC9tGQDtw9yPQssVyF-8Q',
    'https://api.mapbox.com/styles/v1/gsdpm/civtq56ch000z2klqcuvgmzdw/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoiZ3NkcG0iLCJhIjoiY2lqbmN5eG9mMDBndHVmbTU5Mmg1djF6MiJ9.QqFCD7tcmccysN8GUClW8w'
  ].map(function(url) {
    return new ol.source.XYZ({ url: url });
  });
  waitForTiles();

  var map = new ol.Map({
    target: 'map',
    interactions: [],
    controls: [],
    layers: [ new ol.layer.Group({
      layers: sources.map(function(source) {
        return new ol.layer.Tile({ source: source });
      })
    }) ]
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
        if (window.status === 'finished') { return; }
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
    btnStatus(true);
    fetch(app.createPdfReportUrl, { method: 'POST'})
    .then(function(r) { return r.blob() })
    .then(function(data) {
      btnStatus(false);
      var blob = new Blob([data], {type: 'image/pdf'});
      let a = document.createElement("a");
      a.style = "display: none";
      document.body.appendChild(a);
      let url = window.URL.createObjectURL(blob);
      a.href = url;
      a.download = this.getAttribute('download')
      a.click();
      window.URL.revokeObjectURL(url);
    }.bind(this))
    .catch(function() {
      alert("Something went wrong");
      btnStatus(false);
    })
  });


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

    sources.forEach(function(source) {
      source.on('tileloadstart', function() {
        tilesLoading++;
      });
      source.on('tileloadend', function() {
        tilesLoaded++;
        update();
      });
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
  if ($('body').tooltip && !window.matchMedia(mq).matches) {
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
    $('#data-source-legend')
      .find('.service-warning').hide().end();
    $('#data-source-legend').find('.dl-horizontal').hide();
    $('#data-source-legend').find('.text-right').hide();
    $('#data-source-legend img').hide();
  });

  $('#data-source-legend').find('.dl-horizontal').hide();
  $('#data-source-legend').find('.text-right').hide();
  $('#data-source-legend img').hide();

  var dataSourceSource;
  var updateLegend = function(layerName, index) {
    dataSourceLayer.setVisible(false);
    $($('#data-source-legend img').get(index)).attr('src',
      'http://www.geonode-gfdrrlab.org/geoserver/hazard/ows' +
      '?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&FORMAT=image%2Fpng' +
      '&LAYER=' + layerName
    ).on('error', function() {
      console.warn('Error loading layer: ' + layerName);
      $('#data-source-legend').find('.service-warning').show().find('strong').text(
        $($('#data-source-legend .dl-horizontal').get(index)).attr('data-owner')
      );
      $(this).hide();
    }).on('load', function() {
      $($('#data-source-legend').find('.dl-horizontal').get(index)).show();
      $($('#data-source-legend').find('.text-right').get(index)).show();
      $(this).show();
      dataSourceLayer.setVisible(true);
    });
  };
  $('#data-source-map-btn a').on('click', function(e) {
    e.preventDefault();
    var index = ($(this).parent().prop("tagName")==='LI') ? $(this).parent().index() : 0;
    var attr = $($('.current-rp').get(index)).attr('data-name');
    dataSourceSource = new ol.source.ImageWMS({
      url: 'http://www.geonode-gfdrrlab.org/geoserver/hazard/ows',
      params: {'LAYERS': attr},
      serverType: 'geoserver'
    });
    dataSourceLayer.setSource(dataSourceSource);
    dataSourceLayer.setVisible(true);
    levelLayer.setVisible(false);
    updateLegend(attr, index);
    $('#level-map-btn').removeClass('hidden');
    $('#data-source-map-btn').addClass('hidden');
    $('#level-legend').addClass('hidden');
    $('#data-source-legend').removeClass('hidden');
  });

  $('.rp-chooser').on('click', function(e) {
    e.preventDefault();
    $(this).parent().find('.rp-chooser').removeClass('current-rp');
    $(this).addClass('current-rp');
    updateLegend(
      $(this).parent().find('.current-rp').attr('data-name'),
      $(this).parents('.dl-horizontal').first().index()/2
    );
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
  setTimeout(function() {
    $('.tt-input').on('blur', function() {
      $('.navbar').removeClass('search-focused');
    });
  }, 50);

  var mediaCheck = function() {
    var mapDiv = $('.map-block');
    if (!window.matchMedia) return;
    if (window.matchMedia(mq).matches) {
      mapDiv.insertAfter('.page-header.detail');
    } else {
      mapDiv.prependTo('.row .col-sm-5');
    }
    map.updateSize();
  };
  if (!app.pdf) {
    mediaCheck();
    $(window).on('resize', mediaCheck);
  }

  // On mobile, scroll horizontally to make active hazard visible
  if (window.matchMedia && window.matchMedia(mq).matches) {
    var active_li = $('.hazard-types-list li.active');
    if (active_li.length === 0) return;
    var left = active_li.position().left;
    var options;
    var el;
    if ($('.hazard-types-list li.active').hasClass('overview')) {
      el = $('.hazard-types-list li.active');
      el.css('margin-left', '100px');
      options = { marginLeft: 0 };
    } else {
      el = $('.hazard-types-list');
      el.scrollLeft(left - 100);
      options = { scrollLeft: left - 5 };
    }
    el.animate(options, 1000, 'easeOutBounce');
  }

  // Further resources
  $('.further-resources-more').click(function(e) {
    e.preventDefault();
    $('.further-resources').toggleClass('further-resources-open');
  });

  $('.legend dd:not(.notitle)').each(function(i, dd) {
    $(dd).attr('title', $.trim($(dd).text()));
  });

})();
