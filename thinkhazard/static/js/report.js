(function() {

  // Map element selector
  var mapSelector = '#map';

  // Array used as a temporary storage for event offsetX and offsetY
  var offsets = new Array(2);

  // Change the tab to active in the tablist when a item is selected
  // in the "overview" tabpanel
  $('#overview a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
    var target = this.href.split('#');
    $('ul.hazards a').filter('[href="#' + target[1] + '"]').tab('show');
  });

  // Reload the map when a hazard type is selected
  var hazardType;
  $('#hazard-types-list a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
    var hash = this.hash;
    hazardType = hash.substr(1);
    // FIXME show the hazard map
    $('#legend').show();
    window.location.hash = hash;
  });

  // detect any change on hash (history back for example)
  $(window).bind('hashchange', showTab);
  // Load the hazard if already defined URL hash
  if (window.location.hash) {
    showTab();
  }

  // Show the "overview" list when the division-name link is clicked
  $('#division-name').on('click', function() {
    if (hazardType) {
      showOverview();
    }
  });

  var map = new ol.Map({
    target: 'map',
    interactions: [],
    controls: [],
    layers: [
      new ol.layer.Tile({
        source: new ol.source.OSM()
      })
    ],
    view: new ol.View({ })
  });
  map.getView().fitExtent(division_bounds, map.getSize());

  $('.drillup').on('click', function(e) {
    var code = $(this).attr('data-code');
    showDivision(code);
    return false;
  });

  /**
   * Load page for given division code.
   */
  function showDivision(code) {
    var url = app.reportpageUrl + '?divisioncode=' + code;
    if (hazardType) {
      url  += '#' + hazardType;
    }
    window.location.href = url;
  }

  /**
   * Take the hash from URL to activate the tab corresponding to the hazard
   * type.
   */
  function showTab() {
    var hash = window.location.hash;
    if (hash !== '') {
      $('#hazard-types-list a[href=' + hash + ']').tab('show');
    } else {
      showOverview();
    }
  }

  /**
   * Show overview (default) tab.
   */
  function showOverview() {
    $('ul.hazards a').filter('[href="#overview"]').tab('show');
    hazardType = undefined;
    // FIXME show the overview map
    $('#legend').hide();
  }
})();
