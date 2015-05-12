(function() {

  // UTFGrid data
  var grid;
  var keys;
  var data;

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
    addMap(hazardType);
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
      $('ul.hazards a').filter('[href="#overview"]').tab('show');
      hazardType = undefined;
      addMap(hazardType);
      $('#legend').hide();
    }
  });

  // Add a new map to the page when the window changes size
  var timeoutId;
  $(window).resize(function() {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(function() {
      addMap(hazardType);
    }, 500);
  });

  // Change the mouse cursor when an administrative division is detected
  var currentCursor;
  $('#map').on('mousemove', function(e) {

    var w = $(this).width();
    var h = $(this).height();

    if (!currentCursor) {
      currentCursor = $(this).css('cursor');
    }

    getEventOffsets(e, offsets);

    var xRelative = offsets[0] / w;
    var yRelative = offsets[1] / h;

    var data = getDataForPosition(xRelative, yRelative);

    if (data && currentCursor != 'pointer') {
      currentCursor = 'pointer';
      $(this).css('cursor', currentCursor);
    } else if (!data && currentCursor != 'auto') {
      currentCursor = 'auto';
      $(this).css('cursor', currentCursor);
    }
  });

  // Listen to click events on the map and reload the page for the clicked
  // administrative division
  $('#map').on('click', function(e) {
    var w = $(this).width();
    var h = $(this).height();

    getEventOffsets(e, offsets);

    var xRelative = offsets[0] / w;
    var yRelative = offsets[1] / h;
    var data = getDataForPosition(xRelative, yRelative);
    if (data) {
      showDivision(data.code);
    }
  });

  // Add the map to the page
  addMap(hazardType);

  $('.drillup').on('click', function(e) {
    var code = $(this).attr('data-code');
    showDivision(code);
    return false;
  });

  /**
   * Return the UTFGrid data for a position (x, y). `null` is returned
   * if there's no grid or there's no feature at this position.
   */
  function getDataForPosition(x, y) {
    if (grid) {
      var row = grid[Math.floor(y * grid.length)];
      if (row) {
        var code = row.charCodeAt(Math.floor(x * row.length));
        if (code >= 93) {
          code--;
        }
        if (code >= 35) {
          code--;
        }
        code -= 32;
        var key = keys[code];
        if (key) {
          return data[key];
        }
      }
    }
    return null;
  }

  /**
   * Get offsetX and offsetY from the event object.
   *
   * event.offsetX and event.offsetY are not defined in Firefox < 39.
   * See https://bugzilla.mozilla.org/show_bug.cgi?id=69787
   */
  function getEventOffsets(evt, offsets) {
    var offsetX = evt.offsetX;
    var offsetY = evt.offsetY;
    if (offsetX === undefined || offsetY === undefined) {
      var targetOffset = $(evt.target).offset();
      offsetX = evt.pageX - targetOffset.left;
      offsetY = evt.pageY - targetOffset.top;
    }
    offsets[0] = offsetX;
    offsets[1] = offsetY;
  }

  /**
   * Add the map image to the DOM and load the corresponding UTFGrid.
   */
  function addMap(hazardType) {

    var divisionCode = app.divisionCode;

    var w = $(mapSelector).width();
    var h = $(mapSelector).height();

    var imgUrl = app.mapImgUrl + '?width=' + w + '&height=' + h +
        '&divisioncode=' + divisionCode;
    if (hazardType) {
        imgUrl += '&hazardtype=' + hazardType;
    }

    $(mapSelector + ' > img').replaceWith('<img src="' + imgUrl + '" />');

    grid = undefined;
    keys = undefined;
    data = undefined;

    var utfUrl = app.mapUtfUrl + '?width=' + w + '&height=' + h +
        '&divisioncode=' + divisionCode;
    if (hazardType) {
        utfUrl += '&hazardtype=' + hazardType;
    }
    $.ajax(utfUrl).then(function(json) {
      grid = json.grid;
      keys = json.keys;
      data = json.data;
    });
  }

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
    $('#hazard-types-list a[href=' + window.location.hash + ']').tab('show');
  }
})();
