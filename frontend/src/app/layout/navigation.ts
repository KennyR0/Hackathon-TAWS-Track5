import { BellRing, Bot, BriefcaseBusiness, Home, Newspaper, Radar, ShieldCheck } from 'lucide-react'

export const navigationItems = [
  { to: '/summary', label: 'Resumen', icon: Home },
  { to: '/radar', label: 'Radar', icon: Radar },
  { to: '/signals', label: 'Senales', icon: BellRing },
  { to: '/reviews', label: 'Revision', icon: ShieldCheck },
  { to: '/briefings', label: 'Briefings', icon: BriefcaseBusiness },
  { to: '/assistant', label: 'Asistente', icon: Bot },
  { to: '/audit', label: 'Auditoria', icon: Newspaper },
]
