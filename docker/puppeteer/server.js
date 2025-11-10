const express = require('express');
const puppeteer = require('puppeteer');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const BASE_URL = process.env.BASE_URL

app.get('/generate-pdf', async (req, res) => {
    const path = req.query.path;
    if (!path) {
        return res.status(400).send('Missing parameter path.');
    }
    const url = `${BASE_URL}${path}`
    let browser
    try {
        browser = await puppeteer.launch({
            ignoreHTTPSErrors: true,
            acceptInsecureCerts: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--ignore-certificate-errors'
            ]
        });
        const page = await browser.newPage();

        // // Logger toutes les requêtes réseau
        // page.on('request', request => {
        //     console.log(`→ REQUEST: ${request.resourceType()} ${request.method()} ${request.url()}`);
        // });

        // page.on('response', response => {
        //     const status = response.status();
        //     const url = response.url();
        //     const resourceType = response.request().resourceType();
            
        //     console.log(`← RESPONSE: ${status} ${resourceType} ${url}`);
        // });

        // page.on('requestfailed', request => {
        //     const url = request.url();
        //     const resourceType = request.resourceType();
        //     const failure = request.failure();
            
        //     console.error(`❌ REQUEST FAILED: ${resourceType} ${url} - ${failure ? failure.errorText : 'Unknown error'}`);
        // });

        // // Logger les erreurs et messages de la console de la page
        // page.on('console', msg => {
        //     console.log(`PAGE CONSOLE [${msg.type()}]:`, msg.text());
        // });
        
        // page.on('pageerror', error => {
        //     console.error('PAGE ERROR:', error.message);
        // });
        
        // // Logger les requêtes qui échouent (404, etc.)
        // page.on('response', response => {
        //     const status = response.status();
        //     const url = response.url();
        //     const resourceType = response.request().resourceType();
            
        //     if (status >= 400) {
        //         console.error(`❌ FAILED REQUEST: ${status} ${resourceType} ${url}`);
        //     }
        // });
        
        // page.on('requestfailed', request => {
        //     const url = request.url();
        //     const resourceType = request.resourceType();
        //     const failure = request.failure();
            
        //     console.error(`❌ REQUEST FAILED: ${resourceType} ${url} - ${failure ? failure.errorText : 'Unknown error'}`);
        // });
        
        // Gestion d'erreurs spécifique pour la navigation
        let response;
        try {
            response = await page.goto(url, { waitUntil: 'networkidle0' });
        } catch (navigationError) {
            console.error('Navigation error:', navigationError);
            return res.status(400).send(`Error loading page: ${navigationError.message}`);
        }

        // Vérifier si la page s'est chargée correctement
        if (!response || !response.ok()) {
            const statusCode = response ? response.status() : 'unknown';
            console.error(`Page load failed for URL ${url} with status: ${statusCode}`);
            return res.status(502).send(`Page load failed with status: ${statusCode}`);
        }

        // Attendre un peu plus pour s'assurer que tous les CSS sont appliqués
        await new Promise(resolve => setTimeout(resolve, 200));

        // Émuler le media type 'print' pour activer les CSS @media print
        await page.emulateMediaType('print');

        // Gestion d'erreurs spécifique pour la génération PDF
        let pdf;
        try {
            pdf = await page.pdf({
                format: 'A4',
                // margin: {
                //     bottom: 50,
                //     left: 50,
                //     right: 50,
                //     top: 50
                // },
                printBackground: true,  // Important : inclure les couleurs et images de fond CSS
                preferCSSPageSize: false  // Utiliser le format A4 plutôt que celui défini en CSS
            });
        } catch (pdfError) {
            console.error('PDF generation error:', pdfError);
            return res.status(500).send(`Error generating PDF: ${pdfError.message}`);
        }

        res.contentType('application/pdf');
        res.send(Buffer.from(pdf));
    } catch (error) {
        console.error('Unexpected error while generating PDF:', error);
        res.status(500).send(`Unexpected error: ${error.message}`);
    } finally {
        if (browser) {
            try {
                await browser.close();
            } catch (closeError) {
                console.error('Error closing browser:', closeError);
            }
        }
    }
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
    console.log(`Server started on port ${PORT}`);
});
