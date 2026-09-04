export interface SystemDesignTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  nodes: Array<{
    id: string;
    type: string;
    label: string;
    x: number;
    y: number;
    w: number;
    h: number;
    color: string;
  }>;
  arrows: Array<{
    id: string;
    from: string;
    to: string;
    label?: string;
  }>;
}

export const SYSTEM_DESIGN_TEMPLATES: SystemDesignTemplate[] = [
  {
    id: 'blank',
    name: 'Blank Canvas',
    description: 'Clean empty whiteboard ready for custom diagramming',
    category: 'General',
    nodes: [],
    arrows: [],
  },
  {
    id: 'scalable_web_app',
    name: '3-Tier Scalable Web Application',
    description: 'High-availability architecture with CDN, Load Balancer, App Cluster, Redis & PostgreSQL',
    category: 'Web Architectures',
    nodes: [
      { id: 'n1', type: 'client', label: 'Web / Mobile Client', x: 80, y: 220, w: 150, h: 80, color: '#64748b' },
      { id: 'n2', type: 'cdn', label: 'Edge CDN\n(Cloudflare)', x: 300, y: 120, w: 150, h: 80, color: '#f97316' },
      { id: 'n3', type: 'lb', label: 'Load Balancer\n(NGINX / ALB)', x: 300, y: 320, w: 160, h: 85, color: '#3b82f6' },
      { id: 'n4', type: 'app', label: 'App Server Cluster\n(Node / Go)', x: 550, y: 320, w: 170, h: 90, color: '#6366f1' },
      { id: 'n5', type: 'cache', label: 'Redis Cache\n(In-Memory)', x: 800, y: 200, w: 160, h: 85, color: '#ef4444' },
      { id: 'n6', type: 'db', label: 'PostgreSQL DB\n(Primary + Replica)', x: 800, y: 400, w: 170, h: 95, color: '#0ea5e9' },
    ],
    arrows: [
      { id: 'a1', from: 'n1', to: 'n2', label: 'Static Assets' },
      { id: 'a2', from: 'n1', to: 'n3', label: 'Dynamic API' },
      { id: 'a3', from: 'n3', to: 'n4', label: 'Round Robin' },
      { id: 'a4', from: 'n4', to: 'n5', label: 'Cache Lookup' },
      { id: 'a5', from: 'n4', to: 'n6', label: 'Read/Write SQL' },
    ],
  },
  {
    id: 'event_driven_microservices',
    name: 'Event-Driven Microservices',
    description: 'Decoupled services communicating asynchronously via Kafka Message Broker',
    category: 'Microservices',
    nodes: [
      { id: 'm1', type: 'client', label: 'Client Apps', x: 80, y: 250, w: 150, h: 80, color: '#64748b' },
      { id: 'm2', type: 'gateway', label: 'API Gateway\n(Envoy / Kong)', x: 300, y: 250, w: 160, h: 90, color: '#8b5cf6' },
      { id: 'm3', type: 'service', label: 'Order Service', x: 540, y: 150, w: 150, h: 80, color: '#06b6d4' },
      { id: 'm4', type: 'service', label: 'Payment Service', x: 540, y: 350, w: 150, h: 80, color: '#06b6d4' },
      { id: 'm5', type: 'queue', label: 'Kafka Message Bus\n(Events)', x: 760, y: 250, w: 180, h: 90, color: '#ec4899' },
      { id: 'm6', type: 'worker', label: 'Notification Worker', x: 1010, y: 150, w: 160, h: 85, color: '#10b981' },
      { id: 'm7', type: 'worker', label: 'Analytics Pipeline', x: 1010, y: 350, w: 160, h: 85, color: '#10b981' },
    ],
    arrows: [
      { id: 'ma1', from: 'm1', to: 'm2' },
      { id: 'ma2', from: 'm2', to: 'm3' },
      { id: 'ma3', from: 'm2', to: 'm4' },
      { id: 'ma4', from: 'm3', to: 'm5', label: 'order.created' },
      { id: 'ma5', from: 'm4', to: 'm5', label: 'payment.success' },
      { id: 'ma6', from: 'm5', to: 'm6', label: 'Send Email / SMS' },
      { id: 'ma7', from: 'm5', to: 'm7', label: 'ClickHouse Ingestion' },
    ],
  },
  {
    id: 'url_shortener',
    name: 'URL Shortener (TinyURL)',
    description: 'High-throughput URL shortener with Base62 token generator, Redis cache, and analytics',
    category: 'System Design Interview Problems',
    nodes: [
      { id: 'u1', type: 'client', label: 'Users / Browsers', x: 80, y: 240, w: 150, h: 80, color: '#64748b' },
      { id: 'u2', type: 'lb', label: 'Load Balancer', x: 300, y: 240, w: 150, h: 80, color: '#3b82f6' },
      { id: 'u3', type: 'app', label: 'Shortener Service\n(Base62 Encoder)', x: 530, y: 240, w: 170, h: 90, color: '#6366f1' },
      { id: 'u4', type: 'cache', label: 'Redis Cache\n(Top 20% URLs)', x: 770, y: 140, w: 160, h: 85, color: '#ef4444' },
      { id: 'u5', type: 'db', label: 'Distributed NoSQL DB\n(Cassandra / DynamoDB)', x: 770, y: 340, w: 180, h: 90, color: '#0ea5e9' },
    ],
    arrows: [
      { id: 'ua1', from: 'u1', to: 'u2' },
      { id: 'ua2', from: 'u2', to: 'u3' },
      { id: 'ua3', from: 'u3', to: 'u4', label: 'Read Cache Hit' },
      { id: 'ua4', from: 'u3', to: 'u5', label: 'Cache Miss / Insert' },
    ],
  },
];
