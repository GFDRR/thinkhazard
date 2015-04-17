(function() {
  $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    var target = this.href.split('#');
    $('ul.hazards a').filter('[href="#'+target[1]+'"]').tab('show');
  });
})();
