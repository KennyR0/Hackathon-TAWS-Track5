import { useEffect } from 'react'

export function GuidedDemoHighlight({ target }: { target: string }) {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll(`[data-tour-target="${target}"]`))
    nodes.forEach(node => node.classList.add('tour-target-active'))
    nodes[0]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return () => {
      nodes.forEach(node => node.classList.remove('tour-target-active'))
    }
  }, [target])

  return null
}
