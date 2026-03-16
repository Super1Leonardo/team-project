import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './tests', // Тесты будут лежать здесь
	fullyParallel: true,
	reporter: 'html',
	use: {
		baseURL: 'http://localhost:5173',
		trace: 'on-first-retry'
	},
	webServer: {
		command: 'bun run dev',
		url: 'http://localhost:5173',
		reuseExistingServer: !process.env.CI
	},
	projects: [
		{
			name: 'Google Chrome',
			use: {
				...devices['Desktop Chrome'],
				channel: 'chrome' // <-- ТОТ САМЫЙ ФИКС: используем установленный в ОС браузер
			}
		}
	]
});