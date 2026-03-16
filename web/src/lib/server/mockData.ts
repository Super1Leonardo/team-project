import type { Cluster } from "$lib/components/ArticleList.svelte";

// 1. Данные для главной страницы (Лента)
export const mockClusters: Cluster[] = [
  {
    id: "cl-10492",
    title: "Массовый сбой в платежном шлюзе",
    source: "Telegram: Финтех Инсайды",
    publishedAt: "2026-03-14T09:45:00Z",
    sentiment: "negative",
    mlScore: 0.65,
    hasRiskWords: true,
    text:
      "Клиенты массово жалуются на невозможность провести оплату через терминалы...",
    url: "https://t.me/fintech_insider/1234",
    duplicates: [
      {
        title: "Терминалы не принимают карты",
        source: "VK: Подслушано Бизнес",
        publishedAt: "2026-03-14T09:50:00Z",
        mlScore: 0.82,
      },
      {
        title: "Ошибка 500 при попытке оплаты",
        source: "Twitter / X",
        publishedAt: "2026-03-14T09:55:00Z",
        mlScore: 0.91,
      },
    ],
  },
  {
    id: "cl-10493",
    title: "Запуск новой программы лояльности «Кешбэк 10%»",
    source: "РБК Инвестиции",
    publishedAt: "2026-03-14T10:20:00Z",
    sentiment: "positive",
    mlScore: 0.98,
    hasRiskWords: false,
    text: "Банк анонсировал беспрецедентные условия по дебетовым картам...",
    url: "https://rb.ru/invest/loyalty",
    duplicates: [{
      title: "Обзор нового кешбэка от Brand Bank",
      source: "Habr",
      publishedAt: "2026-03-14T10:45:00Z",
      mlScore: 0.88,
    }],
  },
  {
    id: "cl-10494",
    title: "Плановые технические работы 15 марта",
    source: "Официальный сайт",
    publishedAt: "2026-03-14T11:00:00Z",
    sentiment: "neutral",
    mlScore: 0.85,
    hasRiskWords: true,
    text:
      "Завтра с 02:00 до 04:00 по московскому времени возможны краткосрочные прерывания...",
    url: "https://brandradar.example.com/announcements/maintenance",
    duplicates: [],
  },
  {
    id: "cl-10495",
    title: "Слухи о покупке крупного ритейлера",
    source: "Bloomberg Online",
    publishedAt: "2026-03-14T11:30:00Z",
    sentiment: "neutral",
    mlScore: 0.42,
    hasRiskWords: true,
    text: "В сети появилась информация о возможных переговорах...",
    url: "https://bloomberg.com/news/articles/2026-03-14/acquisition-rumors",
    duplicates: [{
      title: "Акции ВкусМаркета растут на слухах о сделке",
      source: "Telegram: Market Watch",
      publishedAt: "2026-03-14T11:40:00Z",
      mlScore: 0.75,
    }],
  },
];

// 2. Агрегированные данные для страницы Аналитики (Таймлайн)
export const mockAnalyticsTimeline = [
  {
    date: "2026-03-08",
    positive: 120,
    negative: 15,
    neutral: 45,
    mlConfidence: 0.92,
  },
  {
    date: "2026-03-09",
    positive: 132,
    negative: 18,
    neutral: 50,
    mlConfidence: 0.89,
  },
  // Spike-алерт: дата, когда произошел инцидент (много негатива)
  {
    date: "2026-03-10",
    positive: 101,
    negative: 189,
    neutral: 40,
    mlConfidence: 0.95,
  },
  {
    date: "2026-03-11",
    positive: 145,
    negative: 40,
    neutral: 55,
    mlConfidence: 0.91,
  },
  {
    date: "2026-03-12",
    positive: 160,
    negative: 22,
    neutral: 60,
    mlConfidence: 0.94,
  },
  {
    date: "2026-03-13",
    positive: 150,
    negative: 18,
    neutral: 58,
    mlConfidence: 0.93,
  },
  {
    date: "2026-03-14",
    positive: 170,
    negative: 12,
    neutral: 45,
    mlConfidence: 0.96,
  },
];
