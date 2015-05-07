(function() {

  var grid;
  var keys;
  var data;
  var currentCursor;
  var timeoutId = -1;
  var mapSelector = '#map';
  var hazardType;

  // Change the tab to active in the tablist when a item is selected
  // in the "default" tabpanel
  $('#default a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
    var target = this.href.split('#');
    $('ul.hazards a').filter('[href="#' + target[1] + '"]').tab('show');
  });

  // Reload the map when a hazard type is selected
  $('#hazard-types-list a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
    var target = this.href.split('#');
    hazardType = target[1];
    addMap();
  });

  // Add a new map to the page when the window changes size
  $(window).resize(function() {
    if (timeoutId != -1) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(addMap, 500);
  });

  // Change the mouse cursor when an administrative division is detected
  $('#map').on('mousemove', function(e) {

    var w = $(this).width();
    var h = $(this).height();

    if (!currentCursor) {
      currentCursor = $(this).css('cursor');
    }

    var offsetX = e.offsetX;
    var offsetY = e.offsetY;

    // event.offsetX and event.offsetY are not defined in Firefox < 39.
    // See https://bugzilla.mozilla.org/show_bug.cgi?id=69787
    if (offsetX === undefined || offsetY === undefined) {
      var targetOffset = $(e.target).offset();
      offsetX = e.pageX - targetOffset.left;
      offsetY = e.pageY - targetOffset.top;
    }

    var xRelative = offsetX / w;
    var yRelative = offsetY / h;

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

    var offsetX = e.offsetX;
    var offsetY = e.offsetY;

    // event.offsetX and event.offsetY are not defined in Firefox < 39.
    // See https://bugzilla.mozilla.org/show_bug.cgi?id=69787
    if (offsetX === undefined || offsetY === undefined) {
      var targetOffset = $(e.target).offset();
      offsetX = e.pageX - targetOffset.left;
      offsetY = e.pageY - targetOffset.top;
    }

    var xRelative = offsetX / w;
    var yRelative = offsetY / h;
    var data = getDataForPosition(xRelative, yRelative);
    if (data) {
      window.location.href = app.reportpageUrl + '?divisioncode=' + data.code;
    }
  });

  // Add the map to the page
  addMap();

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
   * Add the map image to the DOM and load the corresponding UTFGrid.
   */
  function addMap() {

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

    timeoutId = -1;
  }

})();
