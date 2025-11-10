const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch(
        // ignoreHTTPSErrors=true,
        // acceptInsecureCerts=true,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            // '--ignore-certificate-errors'
        ],
    );
    const page = await browser.newPage();
    await page.goto(
        'http://localhost:8081/aprona/piezometre/1/htmlpdf/',
        { 
            waitUntil: 'networkidle0'
        }
    );
    await page.pdf(
        {
            path: '../tmp/puppeteer-generate.pdf',
            format: 'A4',
            margin: {
                bottom: 50,
                left: 50,
                right: 50,
                top: 50
            } 
        }
    );

    await browser.close();
})();
