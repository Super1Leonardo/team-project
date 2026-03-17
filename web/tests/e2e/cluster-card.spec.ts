import { expect, test } from '@playwright/test';

test.describe('cluster card', () => {
	test('opens article dialog with full content', async ({ page }) => {
		await page.goto('/e2e/cluster-card');

		await expect(page.getByRole('heading', { name: 'E2E Cluster Fixture' })).toBeVisible();
		await expect(page.getByText('Тестовый кластер')).toBeVisible();

		await page.getByRole('button', { name: /читать далее/i }).last().click();

		await expect(page.getByRole('dialog')).toBeVisible();
		await expect(page.getByText('Демо-карточка для e2e-проверки загрузки дублей.')).toBeVisible();
		await expect(page.getByRole('link', { name: /открыть оригинал/i })).toHaveAttribute(
			'href',
			'https://example.com/demo-cluster'
		);
	});

	test('loads duplicates through same-origin api and filters out representative mention', async ({
		page
	}) => {
		const duplicateRequests: string[] = [];

		await page.route('**/api/projects/2/mentions?**', async (route) => {
			duplicateRequests.push(route.request().url());
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([
					{
						id: 100,
						source_type: 'website',
						title: 'Тестовый кластер',
						text: 'Representative mention should be filtered out',
						published_at: '2026-03-17T09:36:50.000Z',
						relevance_score: 0.92
					},
					{
						id: 101,
						source_type: 'telegram',
						title: 'Дубль из телеграма',
						text: 'Похожая публикация',
						published_at: '2026-03-17T09:40:00.000Z',
						relevance_score: 0.88
					},
					{
						id: 102,
						source_type: 'rss',
						title: 'Дубль из RSS',
						text: 'Еще одна похожая публикация',
						published_at: '2026-03-17T09:42:00.000Z',
						relevance_score: 0.86
					}
				])
			});
		});

		await page.goto('/e2e/cluster-card?confidence=0.7&period=7d');
		await page.getByRole('button', { name: /ещё 2 источника/i }).click();

		await expect(page.getByText('Дубль из телеграма')).toBeVisible();
		await expect(page.getByText('Дубль из RSS')).toBeVisible();
		await expect(
			page.getByText('Representative mention should be filtered out')
		).not.toBeVisible();
		await expect(page.getByText('Похожие публикации не найдены.')).not.toBeVisible();

		expect(duplicateRequests).toHaveLength(1);

		const requestUrl = new URL(duplicateRequests[0]);
		expect(requestUrl.origin).toBe('http://127.0.0.1:4173');
		expect(requestUrl.pathname).toBe('/api/projects/2/mentions');
		expect(requestUrl.searchParams.get('dedup_group_id')).toBe('6');
		expect(requestUrl.searchParams.get('confidence')).toBe('0.7');
		expect(requestUrl.searchParams.get('period')).toBe('7d');
		expect(requestUrl.host).not.toContain('python:8000');
	});

	test('shows a stable error message when duplicate loading fails', async ({ page }) => {
		let requestCount = 0;

		await page.route('**/api/projects/2/mentions?**', async (route) => {
			requestCount += 1;
			await route.fulfill({
				status: 400,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'backend unavailable' })
			});
		});

		await page.goto('/e2e/cluster-card');
		await page.getByRole('button', { name: /ещё 2 источника/i }).click();

		await expect(page.getByText('backend unavailable')).toBeVisible();
		await expect(page.getByText('Загрузка дублей...')).not.toBeVisible();
		expect(requestCount).toBe(1);
	});
});
