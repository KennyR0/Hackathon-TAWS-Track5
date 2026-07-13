import type { ApiArticle, ApiEvidence } from '../api/contracts'

export function isArticleLinkable(article: Pick<ApiArticle, 'dataMode' | 'isSynthetic' | 'url' | 'linkable'>): boolean {
  if (typeof article.linkable === 'boolean') {
    return article.linkable
  }
  if (article.dataMode === 'fixture' || article.isSynthetic) {
    return false
  }
  return isExternalNewsUrl(article.url)
}

export function isEvidenceLinkable(evidence: Pick<ApiEvidence, 'sourceUrl' | 'linkable'>): boolean {
  if (typeof evidence.linkable === 'boolean') {
    return evidence.linkable
  }
  return isExternalNewsUrl(evidence.sourceUrl)
}

export function isExternalNewsUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'https:') {
      return false
    }
    const hostname = parsed.hostname.toLowerCase().replace(/^www\./, '')
    if (!hostname.includes('.')) {
      return false
    }
    if (hostname === 'fixtures.nexomercado.test') {
      return false
    }
    return !hostname.endsWith('.test')
      && !hostname.endsWith('.localhost')
      && !hostname.endsWith('.invalid')
      && !hostname.endsWith('.example')
  } catch {
    return false
  }
}
