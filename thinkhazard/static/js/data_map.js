function initDataMap(dataUrl) {
  var map = new L.Map('data-map', {
    zoomControl:true,
    maxBounds: [[-60, -185], [85, 185]]
  });

  map._layersMaxZoom=6;
  map._layersMinZoom=1.5;
  // map.dragging.disable();
  map.touchZoom.disable();
  map.doubleClickZoom.disable();
  map.scrollWheelZoom.disable();
  map.boxZoom.disable();
  map.keyboard.disable();


  var select = $('<select>', {
    'class': 'hazard_select form-control',
    'name': 'hazard_select'
  });

  //create select element within container (with id, so it can be referred to later
  for (var i = 0; i < app.hazardTypes.length; i++) {
    var type = app.hazardTypes[i];
    select.append($('<option>', {
      value: type[0],
      html: type[1]
    }));
  }

  setTimeout(function() {
    $('.modal-body').prepend(select);
  }, 200);

  // Get json through jquery

  $.getJSON(dataUrl, function(data) {
    var geojson = L.geoJson(data);

    select.on('change', changeHandler);

    // Change style based on dropdown

    function changeHandler(e) {
      setHazard(this.value);
    }

    function setHazard(hazard) {
      geojson.setStyle(function(feature) {
        return getStyle(feature, hazard);
      });

      geojson.eachLayer(function(layer) {
        bindPopup(layer, hazard);
      });
    }

    setHazard('FL');

    map.fitBounds(geojson.getBounds());
    geojson.addTo(map);
  });

  var colors = {
    'NAT': ['#2b5fa3', '#2175b5'],
    'REG': ['#3182bd', '#6baed6'],
    'GLO': ['#6baed6', '#bdd7e7']
  };

  // Create the Legend control

  var legend = L.control({position: 'bottomleft'});

  legend.onAdd = function (map) {

    // Add the content to the Legend Container

    var div = L.DomUtil.create('ul', 'legend');
    div.innerHTML += '<li><i style="background: ' + colors.GLO[1] + '"></i><span>' + i18n('Global') + '</span></li>';
    div.innerHTML += '<li><i style="background: ' + colors.REG[1] + '"></i><span>' + i18n('Regional') + '</span></li>';
    div.innerHTML += '<li><i style="background: ' + colors.NAT[1] + '"></i><span>' + i18n('National') + '</span></li>';
    div.innerHTML += '<li><i style="background: #FFFFFF"></i><span>' + i18n('No Data') + '</span></li>';

    return div;
  };

  // Add legend to map

  legend.addTo(map);

  function getStyle(feature, hazard) {
    var p = feature.properties;
    var color = '#afafaf';
    var fillColor = '#ffffff';

    var levels = ['NAT', 'REG', 'GLO'];
    var len = levels.length;
    for (var i = 0; i < len; i++) {
      var level = levels[i];
      if (p[hazard + '_' + level] !== null) {
        color = colors[level][0];
        fillColor = colors[level][1];
        break;
      }
    }
    return {
      weight: 1,
      color: color,
      fillColor: fillColor,
      lineJoin: 'bevel',
      opacity: 1,
      fillOpacity: 1
    };
  }

  function bindPopup(layer, type) {
    var p = layer.feature.properties;
    var info = [
      '<b>' + i18n('Country:') + ' </b>', p.name,
      '<br><b>' + i18n('Global:') + ' </b>', p[type + '_GLO'],
      '<br><b>' + i18n('Regional:') + ' </b>', p[type + '_REG'],
      '<br><b>' + i18n('National:') + ' </b>', p[type + '_NAT']
    ].join('');
    layer.bindPopup(info);
  }

  function i18n(string) {
    return app.dataMap.i18n[string];
  }
}
