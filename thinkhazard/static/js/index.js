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
    local: [{
      admin0: 'Morocco'
    }, {
      admin0: 'Morocco',
      admin1: 'Chaouia-Ouardigha'
    }, {
      admin0: 'Morocco',
      admin1: 'Chaouia-Ouardigha',
      admin2: 'Ben Slimane'
    }, {
      admin0: 'Morocco',
      admin1: 'Chaouia-Ouardigha',
      admin2: 'Khouribga'
    }, {
      admin0: 'Morocco',
      admin1: 'Chaouia-Ouardigha',
      admin2: 'Settat'
    }, {
      admin0: 'Morocco',
      admin1: 'Chaouia-Ouardigha',
      admin2: 'Berrechid'
    }]
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
