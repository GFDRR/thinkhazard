(function() {

  var engine = new Bloodhound({
    datumTokenizer: function(d) {
      var tokens = [d.admin0];
      if (d.admin1) {
        tokens.push(d.admin1);
      }
      if (d.admin2) {
        tokens.push(d.admin2);
      }
      return tokens;
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
      url: app.administrativedivisionUrl + '?q=%QUERY',
      wildcard: '%QUERY',
      filter: function(parsedResponse) {
        return parsedResponse.data;
      }
    }
  });

  engine.initialize();

  var $search = $('#search .search-field');
  var $divisionCode = $('#search .search-division-code');

  $search.typeahead({
    highlight: true
  }, {
    display: function(s) {
      return getSortedTokens(s).join(', ');
    },
    source: engine,
    limit: Infinity,
    templates: {
      suggestion: function(data) {
        var tokens = getSortedTokens(data);
        tokens[0] += '<small><em>';
        tokens[tokens.length - 1] += '</em></small>';
        return '<div>' + tokens.join(', ') + '</div>';
      }
    }
  });

  $search.on('typeahead:select', function(e, d) {
    $divisionCode.val(d.code);
    $('#search').trigger('submit');
  });
  $search.on('typeahead:autocomplete', function(e, s) {
    $divisionCode.val(s.code);
  });
  $search.on('typeahead:render', function(e, s) {
    if (s) {
      $divisionCode.val(s.code);
    }
  });
  $search.on('typeahead:asyncrequest', function(e) {
    // clear division code once a new request is sent
    $divisionCode.val('');
  });

  $('#search').on('submit', function(e) {
    var code = $divisionCode.val();
    if (code !== '') {
      window.location.href = app.reportpageUrl.replace('__divisioncode__',
          code);
    }
    return false;
  });

  /**
   */
  function getSortedTokens(s) {
    var tokens = [s.admin0];
    if (s.admin1) {
      tokens.unshift(s.admin1);
    }
    if (s.admin2) {
      tokens.unshift(s.admin2);
    }
    return tokens;
  }

})();
