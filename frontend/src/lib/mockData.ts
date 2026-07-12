import type { Event, Signal, Briefing, AgentRun } from './types';

export async function getEvents(): Promise<Event[]> {
  // Simular retraso de red para estado de carga
  await new Promise(resolve => setTimeout(resolve, 1200));

  return [
    {
      id: 'EVT-1001',
      headline: 'Fed signals potential rate cut in Q3 following inflation report',
      eventAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // hace 30 min
      assets: [{ id: 'AST-1', symbol: 'US10Y', name: 'US 10-Year Treasury Note', instrumentType: 'macro' }],
      mainArticle: {
        id: 'ART-101',
        title: 'Federal Reserve Chairman hints at rate easing',
        url: '#',
        source: { id: 'SRC-1', name: 'WSJ', tier: 'A' },
        publishedAt: new Date(Date.now() - 1000 * 60 * 35).toISOString()
      },
      corroboratingCount: 4
    },
    {
      id: 'EVT-1002',
      headline: 'NVIDIA announces next-gen AI accelerator Blackwell timeline',
      eventAt: new Date(Date.now() - 1000 * 60 * 120).toISOString(), // hace 2 hrs
      assets: [{ id: 'AST-2', symbol: 'NVDA', name: 'NVIDIA Corp', instrumentType: 'equity' }],
      mainArticle: {
        id: 'ART-102',
        title: 'Nvidia reveals roadmap for next generation Blackwell chips',
        url: '#',
        source: { id: 'SRC-2', name: 'Bloomberg', tier: 'A' },
        publishedAt: new Date(Date.now() - 1000 * 60 * 130).toISOString()
      },
      corroboratingCount: 2
    },
    {
      id: 'EVT-1003',
      headline: 'Bitcoin ETFs see record inflows exceeding $1B in a single day',
      eventAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(), // hace 5 hrs
      assets: [
        { id: 'AST-3', symbol: 'BTC', name: 'Bitcoin', instrumentType: 'crypto' },
        { id: 'AST-4', symbol: 'IBIT', name: 'iShares Bitcoin Trust', instrumentType: 'etf' }
      ],
      mainArticle: {
        id: 'ART-103',
        title: 'Crypto ETFs surge on unprecedented demand',
        url: '#',
        source: { id: 'SRC-3', name: 'CoinDesk', tier: 'B' },
        publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 5.2).toISOString()
      },
      corroboratingCount: 1
    },
    {
      id: 'EVT-1004',
      headline: 'Copper prices hit multi-month high on China supply constraints',
      eventAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // hace 1 día
      assets: [{ id: 'AST-5', symbol: 'HG1!', name: 'Copper Futures', instrumentType: 'commodity' }],
      mainArticle: {
        id: 'ART-104',
        title: 'Supply chain bottlenecks drive copper prices upward',
        url: '#',
        source: { id: 'SRC-4', name: 'Reuters', tier: 'A' },
        publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString()
      },
      corroboratingCount: 3
    },
    {
      id: 'EVT-1005',
      headline: 'Unverified rumor regarding Tesla Model 2 cancellation',
      eventAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      assets: [{ id: 'AST-6', symbol: 'TSLA', name: 'Tesla Inc', instrumentType: 'equity' }],
      mainArticle: {
        id: 'ART-105',
        title: 'Is Tesla cancelling its affordable EV project?',
        url: '#',
        source: { id: 'SRC-5', name: 'EVBlog Daily', tier: 'C' },
        publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 2.5).toISOString()
      },
      corroboratingCount: 0
    }
  ];
}

export async function getSignal(_id: string): Promise<Signal | null> {
  await new Promise(resolve => setTimeout(resolve, 800)); // Simula latencia
  
  // En fase MVP devolvemos siempre este mock (NVDA) independiente del ID real
  return {
    id: 'SIG-9021',
    eventId: 'EVT-1002',
    asset: { id: 'AST-2', symbol: 'NVDA', name: 'NVIDIA Corp', instrumentType: 'equity' },
    status: 'completed',
    impact: 'positive',
    reviewStatus: 'pending_review',
    confidenceScore: 0.87,
    marketSnapshot: {
      id: 'MS-201',
      assetId: 'AST-2',
      price: 135.42,
      currency: 'USD',
      change24h: 3.2, // +3.2%
      benchmarkSymbol: 'SPY',
      benchmarkChange24h: 0.8,
      dataAsOf: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
      retrievedAt: new Date().toISOString()
    },
    evidences: [
      { id: 'E-1', text: 'NVIDIA CEO announced production timeline moving forward 3 months for Blackwell architectures.', articleTitle: 'Nvidia reveals roadmap', sourceName: 'Bloomberg', sourceTier: 'A', hash: '8x9A2B1' },
      { id: 'E-2', text: 'TSMC reports supply chain adjustments capable of handling +15% AI chip capacity.', articleTitle: 'TSMC earnings call transcript', sourceName: 'WSJ', sourceTier: 'A', hash: '3A4F99C' },
      { id: 'E-3', text: 'Major hyperscalers express concerns over cooling constraints for new racks, potentially delaying deployments.', articleTitle: 'Datacenter cooling limits hit', sourceName: 'TechInsights', sourceTier: 'B', hash: '7F1E22' }
    ],
    favorableEvidenceIds: ['E-1', 'E-2'],
    counterEvidenceIds: ['E-3'],
    claims: [
      { id: 'C-1', description: 'Aceleración en el timeline de producción de la próxima generación (Blackwell)', evidenceId: 'E-1' },
      { id: 'C-2', description: 'El principal proveedor (TSMC) confirmó capacidad productiva adicional para cubrir la demanda', evidenceId: 'E-2' },
      { id: 'C-3', description: 'Los clientes finales enfrentan cuellos de botella en infraestructura (refrigeración), lo que podría moderar las compras', evidenceId: 'E-3' }
    ],
    assumptions: [
      'La demanda de CSPs (Cloud Service Providers) se mantiene inelástica al precio',
      'No hay nuevas restricciones de exportación a mercados clave en los próximos 90 días'
    ],
    invalidations: [
      'Si TSMC ajusta su guidance de capex a la baja en el próximo trimestre',
      'Si se anuncian aranceles >10% en importaciones de componentes clave'
    ],
    suggestedResearchActions: [
      'Revisar el transcript de la llamada de ganancias de TSMC sobre proyecciones de empaquetado CoWoS',
      'Correr análisis transversal del sector sobre infraestructura térmica y cooling líquido'
    ]
  };
}

export async function getBriefing(_id: string): Promise<Briefing | null> {
  await new Promise(resolve => setTimeout(resolve, 800)); // Latencia

  // Reusamos la señal de NVDA (completed, reviewed)
  const nvdaSignal = await getSignal('SIG-9021');
  if (nvdaSignal) {
    nvdaSignal.reviewStatus = 'reviewed';
  }

  // Creamos una segunda señal mock (BTC) para simular inconsistencia
  const btcSignal: Signal = {
    id: 'SIG-9022',
    eventId: 'EVT-1003',
    asset: { id: 'AST-3', symbol: 'BTC', name: 'Bitcoin', instrumentType: 'crypto' },
    status: 'insufficient_evidence', // Estado inconsistente para ser compartido
    impact: 'positive',
    reviewStatus: 'discarded', // Review inconsistente para ser compartido
    confidenceScore: 0.3,
    marketSnapshot: {
      id: 'MS-202',
      assetId: 'AST-3',
      price: 68400.0,
      currency: 'USD',
      change24h: 5.4,
      dataAsOf: new Date().toISOString(),
      retrievedAt: new Date().toISOString()
    },
    evidences: [],
    favorableEvidenceIds: [],
    counterEvidenceIds: [],
    claims: [],
    assumptions: ['La volatilidad se mantendrá en rangos históricos'],
    invalidations: ['Nuevas regulaciones SEC'],
    suggestedResearchActions: ['Verificar correlación con flujos de ETF en T-1']
  };

  return {
    id: 'BRF-001',
    title: 'Briefing Semanal: Semiconductores y Crypto',
    generatedAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    status: 'shareable', // Intentamos compartir esto pero contiene una señal descartada
    summary: 'El mercado de tecnología ha mostrado volatilidad en la última semana. Recomendamos monitorear los activos de infraestructura. Además, los ETFs de Bitcoin ven demanda histórica.',
    signals: [nvdaSignal!, btcSignal]
  };
}

export async function getAgentRun(_id: string): Promise<AgentRun | null> {
  await new Promise(resolve => setTimeout(resolve, 600));

  const baseTime = Date.now() - 1000 * 60 * 5; // Hace 5 minutos

  return {
    id: 'run_01hx_44mk',
    signalId: 'SIG-9021',
    dataMode: 'fixture', // DataMode que usó el agente
    status: 'completed',
    startedAt: new Date(baseTime).toISOString(),
    completedAt: new Date(baseTime + 1200).toISOString(),
    steps: [
      {
        id: 'step_1',
        nodeName: 'EventIngestion',
        status: 'success',
        startedAt: new Date(baseTime).toISOString(),
        completedAt: new Date(baseTime + 100).toISOString(),
        provider: 'mock_ingestor'
      },
      {
        id: 'step_2',
        nodeName: 'SourceRetrieval',
        status: 'success',
        startedAt: new Date(baseTime + 101).toISOString(),
        completedAt: new Date(baseTime + 450).toISOString(),
        urls_fetched: 3
      },
      {
        id: 'step_3',
        nodeName: 'EvidenceExtraction (LLM)',
        status: 'success',
        startedAt: new Date(baseTime + 451).toISOString(),
        completedAt: new Date(baseTime + 950).toISOString(),
        tokens_used: 1045
      },
      {
        id: 'step_4',
        nodeName: 'SignalSynthesizer',
        status: 'success',
        startedAt: new Date(baseTime + 951).toISOString(),
        completedAt: new Date(baseTime + 1200).toISOString()
      }
    ]
  };
}
