import express from 'express';
import BrowserPool from './services/BrowserPool.js';

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const BASE_URL = process.env.BASE_URL;

// Global browser pool instance
const browserPool = new BrowserPool();

app.get('/generate-pdf', async (req, res) => {
    const path = req.query.path;
    if (!path) {
        return res.status(400).send('Missing parameter path.');
    }
    const url = `${BASE_URL}${path}`;
    
    let browser;
    let page;
    
    try {
        // Get browser from pool instead of launching new one
        browser = await browserPool.getBrowser();
        page = await browser.newPage();

        // Optional: Enable logging (uncomment if needed)
        // page.on('console', msg => {
        //     console.log(`PAGE CONSOLE [${msg.type()}]:`, msg.text());
        // });

        // page.on('pageerror', error => {
        //     console.error('PAGE ERROR:', error.message);
        // });

        // Navigate to the page
        let response;
        try {
            response = await page.goto(url, { 
                waitUntil: 'networkidle0',
                timeout: 30000 // 30 second timeout
            });
        } catch (navigationError) {
            console.error('Navigation error:', navigationError);
            return res.status(400).send(`Error loading page: ${navigationError.message}`);
        }

        // Check if page loaded correctly
        if (!response || !response.ok()) {
            const statusCode = response ? response.status() : 'unknown';
            console.error(`Page load failed for URL ${url} with status: ${statusCode}`);
            return res.status(502).send(`Page load failed with status: ${statusCode}`);
        }

        // Wait for CSS to be applied
        await new Promise(resolve => setTimeout(resolve, 200));

        // Emulate print media for @media print CSS
        await page.emulateMediaType('print');

        // Generate PDF
        let pdf;
        try {
            pdf = await page.pdf({
                format: 'A4',
                printBackground: true,
                preferCSSPageSize: false,
                margin: {
                    top: '20px',
                    bottom: '20px',
                    left: '20px',
                    right: '20px'
                }
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
        if (page) {
            try {
                await page.close();
            } catch (closeError) {
                console.error('Error closing page:', closeError);
            }
        }
        if (browser) {
            // Return browser to pool instead of closing it
            await browserPool.releasePage(browser);
        }
    }
});

// Health check endpoint
app.get('/health', async (req, res) => {
    try {
        const poolStatus = {
            initialized: browserPool.isInitialized,
            totalBrowsers: browserPool.browsers.length,
            browsersStatus: []
        };

        for (const browser of browserPool.browsers) {
            try {
                const isConnected = browser.isConnected();
                const pages = await browser.pages();
                const pageCount = browserPool.pageCount.get(browser) || 0;
                
                poolStatus.browsersStatus.push({
                    connected: isConnected,
                    actualPages: pages.length,
                    trackedPages: pageCount
                });
            } catch (error) {
                poolStatus.browsersStatus.push({
                    connected: false,
                    error: error.message
                });
            }
        }

        res.json({
            status: 'healthy',
            pool: poolStatus,
            uptime: process.uptime(),
            memory: process.memoryUsage()
        });
    } catch (error) {
        res.status(500).json({
            status: 'unhealthy',
            error: error.message
        });
    }
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('Received SIGINT, closing browser pool...');
    await browserPool.close();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('Received SIGTERM, closing browser pool...');
    await browserPool.close();
    process.exit(0);
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, async () => {
    console.log(`Server started on port ${PORT}`);
    // Initialize browser pool on startup
    try {
        await browserPool.initialize();
        console.log('Browser pool ready');
    } catch (error) {
        console.error('Failed to initialize browser pool:', error);
    }
});
