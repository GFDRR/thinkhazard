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
    limit: 10,
    remote: {
      url: app.administrativedivisionUrl + '?q=%QUERY',
      filter: function(parsedResponse) {
        return parsedResponse.data;
      }
    }
  });

  engine.initialize();

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

  $('#search-field').typeahead({
    highlight: true
  }, {
    displayKey: function(s) {
      return getSortedTokens(s).join(', ');
    },
    source: engine.ttAdapter(),
    templates: {
      suggestion: function(data) {
        var tokens = getSortedTokens(data);
        tokens[0] += '<small><em>';
        tokens[tokens.length - 1] += '</em></small>';
        return tokens.join(', ');
      }
    }
  });

  $('#search-field').on('typeahead:selected',
      function(e, d) {
        window.location.href = app.reportpageUrl + '?divisioncode=' + d.code;
      }
  );

})();
