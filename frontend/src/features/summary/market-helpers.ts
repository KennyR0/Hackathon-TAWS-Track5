import type { MarketAssetViewModel } from '../../shared/types/view-models'
import type { MarketCategory } from './components'

export function buildMarketCategories(assets: MarketAssetViewModel[]): MarketCategory[] {
  const counts = {
    us: assets.filter(asset => asset.instrumentType === 'equity' || asset.instrumentType === 'etf').length,
    crypto: assets.filter(asset => asset.instrumentType === 'crypto').length,
    futures: assets.filter(asset => asset.instrumentType === 'commodity').length,
  }

  return [
    { id: 'us', label: 'Estados Unidos', enabled: counts.us > 0, assetCount: counts.us },
    { id: 'europe', label: 'Europa', enabled: false, assetCount: 0 },
    { id: 'asia', label: 'Asia', enabled: false, assetCount: 0 },
    { id: 'latam', label: 'Latinoamerica', enabled: false, assetCount: 0 },
    { id: 'fx', label: 'Divisas', enabled: false, assetCount: 0 },
    { id: 'crypto', label: 'Criptomonedas', enabled: counts.crypto > 0, assetCount: counts.crypto },
    { id: 'futures', label: 'Futuros', enabled: counts.futures > 0, assetCount: counts.futures },
  ]
}

export function filterAssetsByCategory(assets: MarketAssetViewModel[], categoryId: string): MarketAssetViewModel[] {
  if (categoryId === 'us') return assets.filter(asset => asset.instrumentType === 'equity' || asset.instrumentType === 'etf')
  if (categoryId === 'crypto') return assets.filter(asset => asset.instrumentType === 'crypto')
  if (categoryId === 'futures') return assets.filter(asset => asset.instrumentType === 'commodity')
  return []
}
