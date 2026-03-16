import { test, expect } from '@playwright/test';

test.describe('Главная страница (Лента)', () => {
	test('Рендерит ленту с ML-данными', async ({ page }) => {
		// Передаем флаг успешного мока прямо в URL
		await page.goto('/?__mock=success&confidence=0.7&period=7d');
		await expect(page.getByRole('heading', { name: 'Лента' })).toBeVisible();
		await expect(page.getByText('Сбой приложения')).toBeVisible();
	});

	test('Отображает ошибку, если API упал', async ({ page }) => {
		// Передаем флаг ошибки
		await page.goto('/?__mock=error');

		await expect(page.getByText('ML API недоступен')).toBeVisible();
	});
});