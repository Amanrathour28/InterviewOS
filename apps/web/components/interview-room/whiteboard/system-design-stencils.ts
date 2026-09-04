export interface SystemDesignStencil {
  id: string;
  label: string;
  category: 'compute' | 'storage' | 'infrastructure' | 'clients';
  icon: string;
  color: string;
  description: string;
  defaultWidth: number;
  defaultHeight: number;
}

export const SYSTEM_DESIGN_STENCILS: SystemDesignStencil[] = [
  // Compute
  {
    id: 'api_gateway',
    label: 'API Gateway',
    category: 'compute',
    icon: 'Network',
    color: '#8b5cf6',
    description: 'Routing, auth, rate limiting, and request transformation',
    defaultWidth: 160,
    defaultHeight: 90,
  },
  {
    id: 'load_balancer',
    label: 'Load Balancer',
    category: 'infrastructure',
    icon: 'Scale',
    color: '#3b82f6',
    description: 'Layer 4/7 traffic distribution (ALB / NGINX / Envoy)',
    defaultWidth: 160,
    defaultHeight: 90,
  },
  {
    id: 'app_server',
    label: 'Application Server',
    category: 'compute',
    icon: 'Server',
    color: '#6366f1',
    description: 'Stateless backend business logic node',
    defaultWidth: 160,
    defaultHeight: 90,
  },
  {
    id: 'microservice',
    label: 'Microservice',
    category: 'compute',
    icon: 'Box',
    color: '#06b6d4',
    description: 'Decoupled domain service (e.g., Auth, Payments, Users)',
    defaultWidth: 160,
    defaultHeight: 90,
  },
  {
    id: 'worker',
    label: 'Async Worker',
    category: 'compute',
    icon: 'Cpu',
    color: '#10b981',
    description: 'Background processing job / Celery worker / Cron',
    defaultWidth: 160,
    defaultHeight: 90,
  },

  // Storage
  {
    id: 'database_sql',
    label: 'SQL Database (PostgreSQL)',
    category: 'storage',
    icon: 'Database',
    color: '#0ea5e9',
    description: 'ACID relational primary database with read replicas',
    defaultWidth: 170,
    defaultHeight: 100,
  },
  {
    id: 'cache_redis',
    label: 'Redis In-Memory Cache',
    category: 'storage',
    icon: 'Zap',
    color: '#ef4444',
    description: 'Sub-millisecond key-value cache and session store',
    defaultWidth: 160,
    defaultHeight: 90,
  },
  {
    id: 'object_storage',
    label: 'Object Storage (S3)',
    category: 'storage',
    icon: 'HardDrive',
    color: '#f59e0b',
    description: 'Blob storage for media, logs, and assets',
    defaultWidth: 160,
    defaultHeight: 90,
  },
  {
    id: 'search_index',
    label: 'Search (Elasticsearch)',
    category: 'storage',
    icon: 'Search',
    color: '#14b8a6',
    description: 'Full-text search cluster & analytics index',
    defaultWidth: 160,
    defaultHeight: 90,
  },

  // Infrastructure
  {
    id: 'cdn',
    label: 'Edge CDN (Cloudflare)',
    category: 'infrastructure',
    icon: 'Globe',
    color: '#f97316',
    description: 'Global static asset caching and DDoS mitigation',
    defaultWidth: 160,
    defaultHeight: 90,
  },
  {
    id: 'message_queue',
    label: 'Message Queue (Kafka)',
    category: 'infrastructure',
    icon: 'Layers',
    color: '#ec4899',
    description: 'High-throughput event streaming & pub/sub broker',
    defaultWidth: 170,
    defaultHeight: 95,
  },

  // Clients
  {
    id: 'client_browser',
    label: 'Web Client / SPA',
    category: 'clients',
    icon: 'Monitor',
    color: '#64748b',
    description: 'End-user browser client application',
    defaultWidth: 150,
    defaultHeight: 85,
  },
  {
    id: 'client_mobile',
    label: 'Mobile App (iOS/Android)',
    category: 'clients',
    icon: 'Smartphone',
    color: '#64748b',
    description: 'Native mobile client application',
    defaultWidth: 150,
    defaultHeight: 85,
  },
  {
    id: 'third_party_api',
    label: '3rd-Party External API',
    category: 'clients',
    icon: 'ExternalLink',
    color: '#94a3b8',
    description: 'Stripe, Twilio, OAuth Providers, Webhooks',
    defaultWidth: 160,
    defaultHeight: 90,
  },
];
