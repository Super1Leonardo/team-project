export interface Source {
  id: number;
  project_id: number;
  source_type: "telegram" | "vk" | "dzen" | "rss";
  source_config: {
    channel?: string;
    group_id?: number;
    domain?: string;
    feed_url?: string;
  };
  is_active: boolean;
  poll_interval_s: number;
  last_collected_at: string | null;
  last_error: string | null;
  created_at: string;
}

export const mockSources: Source[] = [
  {
    id: 1,
    project_id: 1,
    source_type: "telegram",
    source_config: { channel: "banksta" },
    is_active: true,
    poll_interval_s: 300,
    last_collected_at: "2026-03-14T15:30:00Z",
    last_error: null,
    created_at: "2026-01-15T10:05:00Z",
  },
  {
    id: 2,
    project_id: 1,
    source_type: "vk",
    source_config: { group_id: -12345, domain: "bank_news" },
    is_active: true,
    poll_interval_s: 300,
    last_collected_at: "2026-03-14T15:28:00Z",
    last_error: null,
    created_at: "2026-01-16T11:00:00Z",
  },
  {
    id: 3,
    project_id: 1,
    source_type: "rss",
    source_config: { feed_url: "https://example.com/rss" },
    is_active: true,
    poll_interval_s: 600,
    last_collected_at: "2026-03-14T10:00:00Z",
    last_error: "Feed timeout",
    created_at: "2026-01-17T09:00:00Z",
  },
];
