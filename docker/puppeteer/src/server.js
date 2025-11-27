import express from 'express';
import { Cluster } from 'puppeteer-cluster';

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const BASE_URL = process.env.BASE_URL;
const MAX_CONCURRENCY = parseInt(process.env.MAX_CONCURRENCY) || 15;

const cluster = await Cluster.launch({
    concurrency: Cluster.CONCURRENCY_PAGE,
    maxConcurrency: MAX_CONCURRENCY,
    puppeteerOptions: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-first-run',
            '--safebrowsing-disable-auto-update',
            '--disable-ipc-flooding-protection',
        ]
    }
});

await cluster.task(async ({ page, data: url }) => {
    // Optional: Enable logging (uncomment if needed)
    // page.on('console', msg => {
    //     console.log(`PAGE CONSOLE [${msg.type()}]:`, msg.text());
    // });

    // page.on('pageerror', error => {
    //     console.error('PAGE ERROR:', error.message);
    // });

    // Navigate to the page
    const response = await page.goto(url, {
        waitUntil: 'networkidle0',
        timeout: 30000 // 30 second timeout
    });

    // Check if page loaded correctly
    if (!response || !response.ok()) {
        const statusCode = response ? response.status() : 'unknown';
        throw new Error(`Page load failed for URL ${url} with status: ${statusCode}`)
    }

    // Wait for CSS to be applied
    await new Promise(resolve => setTimeout(resolve, 200));

    // Emulate print media for @media print CSS
    await page.emulateMediaType('print');

    // Generate PDF
    return page.pdf({
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
});


app.get('/generate-pdf', async (req, res) => {
    const path = req.query.path;
    if (!path) {
        return res.status(400).send('Missing parameter path.');
    }
    const url = `${BASE_URL}${path}`;
    try {
        const pdf = await cluster.execute(url);
        res.contentType('application/pdf');
        res.send(Buffer.from(pdf));
    } catch (error) {
        console.error('Unexpected error while generating PDF:', error);
        res.status(500).send(`Unexpected error: ${error.message}`);
    }
});

// Health check endpoint
app.get('/health', async (req, res) => {
    try {
        res.json({
            status: 'healthy',
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
    await cluster.close();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('Received SIGTERM, closing browser pool...');
    await cluster.close();
    process.exit(0);
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, async () => {
    console.log(`Server started on port ${PORT}`);
});
