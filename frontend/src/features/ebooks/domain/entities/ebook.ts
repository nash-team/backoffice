export interface Ebook {
  id: number
  title: string
  theme: string
  audience: string
  num_pages: number
  created_at: string
  updated_at: string
  pages_meta?: PageMeta[]
}

export interface PageMeta {
  page_number: number
  title: string
  format: string
  color_mode: 'COLOR' | 'BLACK_WHITE'
  image_data?: string
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface ThemeOption {
  id: string
  label: string
  description?: string
}

export interface AudienceOption {
  id: string
  label: string
  complexity?: string
}

export interface FormConfig {
  themes: Array<string | ThemeOption>
  audiences: Array<string | AudienceOption>
}
