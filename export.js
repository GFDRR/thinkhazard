phantom.casperPath = './node_modules/casperjs'
phantom.injectJs(phantom.casperPath +'/bin/bootstrap.js')

const casper = require('casper').create()
const args = require('system').args

casper.start()

casper.page.paperSize = {
  format: 'A4',
  orientation: 'portrait'
}

var target = args.slice(-2)[0]
var file_name = args.slice(-1)[0]

casper.thenOpen(target, function () {
  casper.wait(2000, function() {
    this.captureSelector(file_name, '.map', {
      quality: 90
    })
  })
})

casper.run()
