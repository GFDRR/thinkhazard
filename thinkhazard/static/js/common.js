(function() {
  $('.navbar .languages li a').on('click', function() {
      $.ajax({
          url: $(this).attr('href'),
          complete: function(t) {
              location.reload();
          }
      });
      return false;
  });
})();
