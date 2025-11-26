import puppeteer from 'puppeteer';

// Configuration du pool de browsers
const BROWSER_POOL_SIZE = parseInt(process.env.BROWSER_POOL_SIZE) || 2;
const MAX_PAGES_PER_BROWSER = parseInt(process.env.MAX_PAGES_PER_BROWSER) || 10;
const BROWSER_IDLE_TIMEOUT = parseInt(process.env.BROWSER_IDLE_TIMEOUT) || 30000; // 30 secondes

export default class BrowserPool {
    constructor(size = BROWSER_POOL_SIZE) {
        this.size = size;
        this.browsers = [];
        this.available = [];
        this.pageCount = new Map(); // Track pages per browser
        this.lastUsed = new Map(); // Track last usage time
        this.isInitialized = false;
    }

    async initialize() {
        if (this.isInitialized) return;

        console.log(`Initializing browser pool with ${this.size} browsers...`);

        for (let i = 0; i < this.size; i++) {
            try {
                const browser = await this.createBrowser();
                this.browsers.push(browser);
                this.available.push(browser);
                this.pageCount.set(browser, 0);
                this.lastUsed.set(browser, Date.now());
                console.log(`Browser ${i + 1}/${this.size} created`);
            } catch (error) {
                console.error(`Failed to create browser ${i + 1}:`, error);
            }
        }
        
        this.isInitialized = true;
        console.log(`Browser pool initialized with ${this.browsers.length} browsers`);
        
        // Start cleanup timer
        this.startCleanupTimer();
    }

    async createBrowser() {
        return await puppeteer.launch({
            ignoreHTTPSErrors: true,
            acceptInsecureCerts: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                // '--ignore-certificate-errors',
                '--disable-dev-shm-usage',
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
                '--disable-ipc-flooding-protection'
            ]
        });
    }

    async getBrowser() {
        if (!this.isInitialized) {
            await this.initialize();
        }

        // Find available browser with least pages
        let selectedBrowser = null;
        let minPages = Infinity;

        for (const browser of this.browsers) {
            try {
                // Check if browser is still connected
                if (!browser.isConnected()) {
                    await this.replaceBrowser(browser);
                    continue;
                }

                const pageCount = this.pageCount.get(browser) || 0;
                if (pageCount < MAX_PAGES_PER_BROWSER && pageCount < minPages) {
                    minPages = pageCount;
                    selectedBrowser = browser;
                }
            } catch (error) {
                console.error('Error checking browser status:', error);
                await this.replaceBrowser(browser);
            }
        }

        if (!selectedBrowser) {
            // All browsers are at capacity, wait a bit and try again
            await new Promise(resolve => setTimeout(resolve, 100));
            return this.getBrowser();
        }

        this.pageCount.set(selectedBrowser, (this.pageCount.get(selectedBrowser) || 0) + 1);
        this.lastUsed.set(selectedBrowser, Date.now());
        
        return selectedBrowser;
    }

    async releasePage(browser) {
        const currentCount = this.pageCount.get(browser) || 0;
        this.pageCount.set(browser, Math.max(0, currentCount - 1));
    }

    async replaceBrowser(oldBrowser) {
        console.log('Replacing disconnected browser...');
        
        const index = this.browsers.indexOf(oldBrowser);
        if (index === -1) return;

        try {
            await oldBrowser.close();
        } catch (error) {
            console.error('Error closing old browser:', error);
        }

        try {
            const newBrowser = await this.createBrowser();
            this.browsers[index] = newBrowser;
            this.pageCount.set(newBrowser, 0);
            this.lastUsed.set(newBrowser, Date.now());
            this.pageCount.delete(oldBrowser);
            this.lastUsed.delete(oldBrowser);
            console.log('Browser replaced successfully');
        } catch (error) {
            console.error('Failed to replace browser:', error);
        }
    }

    startCleanupTimer() {
        setInterval(() => {
            const now = Date.now();
            this.browsers.forEach(async (browser) => {
                const pageCount = this.pageCount.get(browser) || 0;
                const lastUsed = this.lastUsed.get(browser) || 0;

                // If browser has no pages and hasn't been used recently
                if (pageCount === 0 && (now - lastUsed) > BROWSER_IDLE_TIMEOUT) {
                    try {
                        const pages = await browser.pages();
                        // Close any remaining pages except the default one
                        for (let i = 1; i < pages.length; i++) {
                            await pages[i].close();
                        }
                    } catch (error) {
                        console.error('Error during browser cleanup:', error);
                    }
                }
            });
        }, 10000); // Check every 10 seconds
    }

    async close() {
        console.log('Closing browser pool...');
        for (const browser of this.browsers) {
            try {
                await browser.close();
            } catch (error) {
                console.error('Error closing browser:', error);
            }
        }
        this.browsers = [];
        this.available = [];
        this.pageCount.clear();
        this.lastUsed.clear();
        this.isInitialized = false;
    }
}
