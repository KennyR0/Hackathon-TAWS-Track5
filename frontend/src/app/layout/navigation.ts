import { BellRing, Bot, BriefcaseBusiness, Home, Newspaper, Radar, ShieldCheck } from 'lucide-react'

export const navigationItems = [
  { to: '/summary', label: 'Resumen', icon: Home },
  { to: '/radar', label: 'Radar', icon: Radar },
  { to: '/signals', label: 'Señales', icon: BellRing },
  { to: '/reviews', label: 'Revisión', icon: ShieldCheck },
  { to: '/briefings', label: 'Briefings', icon: BriefcaseBusiness },
  { to: '/assistant', label: 'Demo IA', icon: Bot },
  { to: '/audit', label: 'Auditoría', icon: Newspaper },
]
