export interface PriceChange {
  name: string
  current: number
  old: number
  change_percent: number
  change_amount: number
}

export interface LastPriceUpdateBy {
  username: string | null
  full_name: string | null
  at: string
}

export interface RecentPriceUpdate {
  price_type: string
  category: string | null
  price: number
  updated_at: string
}

export interface DashboardSummary {
  degraded?: boolean
  highest_price: number
  highest_price_label: string
  avg_24h_change: number
  biggest_change: PriceChange | null
  price_changes: PriceChange[]
  total_bots: number
  active_bots: number
  total_channels: number
  active_channels: number
  total_price_types: number
  total_price_updates: number
  latest_update_time: string | null
  recent_updates_24h: number
  last_price_update_by: LastPriceUpdateBy | null
  recent_price_updates: RecentPriceUpdate[]
}
