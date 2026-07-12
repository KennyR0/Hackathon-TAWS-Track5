import { Bot, BriefcaseBusiness, ChartNoAxesCombined, Newspaper, Radar, ShieldCheck } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavigationItem {
  to: string
  label: string
  number: string
  icon: LucideIcon
}

interface NavigationSection {
  label: string
  items: NavigationItem[]
}

export const navigationSections: NavigationSection[] = [
  {
    label: 'Mercado',
    items: [{ to: '/summary', label: 'Panorama', number: '01', icon: ChartNoAxesCombined }],
  },
  {
    label: 'Investigación',
    items: [
      { to: '/radar', label: 'Radar', number: '02', icon: Radar },
      { to: '/signals', label: 'Señales', number: '03', icon: Newspaper },
    ],
  },
  {
    label: 'Operaciones',
    items: [
      { to: '/reviews', label: 'Revisión', number: '04', icon: ShieldCheck },
      { to: '/briefings', label: 'Briefings', number: '05', icon: BriefcaseBusiness },
    ],
  },
  {
    label: 'Control',
    items: [{ to: '/audit', label: 'Auditoría', number: '06', icon: Newspaper }],
  },
]

export const navigationItems: NavigationItem[] = navigationSections.flatMap(section => section.items)

export const mobileNavigationItems: NavigationItem[] = [
  navigationItems[0],
  navigationItems[1],
  navigationItems[3],
  { to: '/assistant', label: 'Consultar', number: 'AI', icon: Bot },
]
