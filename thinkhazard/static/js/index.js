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
      url: app.adminunitUrl + '?q=%QUERY',
      filter: function(parsedResponse) {
        return parsedResponse.data;
      }
    }
  });

  engine.initialize();

  $('#search-field').typeahead({
    highlight: true
  }, {
    displayKey: function(s) {
      var tokens = [s.admin0];
      if (s.admin1) {
        tokens.push(s.admin1);
      }
      if (s.admin2) {
        tokens.push(s.admin2);
      }
      return tokens.join(', ');
    },
    source: engine.ttAdapter()
  });

})();
