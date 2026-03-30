(function() {

  var searchEngine = new Bloodhound({
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
      url: app.administrativedivisionUrl + '?q=%QUERY',
      wildcard: '%QUERY',
      filter: function(parsedResponse) {
        return parsedResponse.data;
      }
    }
  });

  var $search = $('#search .search-field');
  var $divisionUrl = $('#search .search-division-url');

  $search.typeahead({
    highlight: true
  }, {
    name: 'search-results',
    display: function(s) {
      return getSortedTokens(s).join(', ');
    },
    source: searchEngine,
    limit: Infinity,
    templates: {
      suggestion: function(data) {
        var tokens = getSortedTokens(data);
        tokens[0] += '<small><em>';
        tokens[tokens.length - 1] += '</em></small>';
        var content = tokens.join(', ');
        var tag = getResultTag(data);
        if (tag) {
          content += tag;
        }
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

  function getResultTag(data) {
    if (data.mnemonic === 'COU') {
      return '<span class="result-tag country">Country</span>';
    }
    if (data.mnemonic === 'URB' && data.is_capital) {
      return '<span class="result-tag capital">Capital</span>';
    }
    if (data.mnemonic === 'URB') {
      return '<span class="result-tag ghsl">GHSL Urban Center</span>';
    }
    return '<span class="result-tag admindiv">ADM DIVISION</span>';
  }

})();
