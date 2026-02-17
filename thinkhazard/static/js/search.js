(function() {

  var admDivEngine = new Bloodhound({
    datumTokenizer: function(d) {
      return Bloodhound.tokenizers.whitespace(
        d.admin3 || d.admin2 || d.admin1 || d.admin0);
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    identity: function(d) {
      return d.code;
    },
    sufficient: 11,
    remote: {
      url: app.administrativedivisionUrl + '?urban=false&q=%QUERY',
      wildcard: '%QUERY',
      filter: function(parsedResponse) {
        return parsedResponse.data;
      }
    }
  });

  var urbanEngine = new Bloodhound({
    datumTokenizer: function(d) {
      return Bloodhound.tokenizers.whitespace(
        d.admin3 || d.admin2 || d.admin1 || d.admin0);
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    identity: function(d) {
      return d.code;
    },
    sufficient: 11,
    remote: {
      url: app.administrativedivisionUrl + '?urban=true&q=%QUERY',
      wildcard: '%QUERY',
      filter: function(parsedResponse) {
        return parsedResponse.data;
      },
    },
  });

  var $search = $('#search .search-field');
  var $divisionUrl = $('#search .search-division-url');

  $search.typeahead({
    highlight: true
  }, {
    name: 'urban',
    display: function(s) {
      return getSortedTokens(s).join(', ');
    },
    source: urbanEngine,
    limit: Infinity,
    templates: {
      header: '<div class="tt-header urban">URBAN</div>',
      suggestion: function(data) {
        var tokens = getSortedTokens(data);
        tokens[0] += '<small><em>';
        tokens[tokens.length - 1] += '</em></small>';
        var content = tokens.join(', ');
        return '<div>' + content + '</div>';
      },
      footer: '<div class="tt-footer"><hr/></div>',
    }
  }, {
    name: 'admin-div',
    display: function(s) {
      return getSortedTokens(s).join(', ');
    },
    source: admDivEngine,
    limit: Infinity,
    templates: {
      header: '<div class="tt-header admindiv">ADM DIVISION</div>',
      suggestion: function(data) {
        var tokens = getSortedTokens(data);
        tokens[0] += '<small><em>';
        tokens[tokens.length - 1] += '</em></small>';
        var content = tokens.join(', ');
        return '<div>' + content + '</div>';
      },
    }
  });

  $search.on('typeahead:select', function(e, d) {
    $divisionUrl.val(d.url);
    $('#search').trigger('submit');
  });
  $search.on('typeahead:autocomplete', function(e, s) {
    $divisionUrl.val(s.url);
  });
  $search.on('typeahead:render', function(e, s) {
    if (s) {
      $divisionUrl.val(s.url);
    }
  });
  $search.on('typeahead:asyncrequest', function(e) {
    // clear division code once a new request is sent
    $divisionUrl.val('');
  });

  $('#search').on('submit', function(e) {
    var url = $divisionUrl.val();
    if (url !== '') {
      window.location.href = url;
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
    if (s.admin3) {
      tokens.unshift(s.admin3);
    }
    return tokens;
  }

})();
