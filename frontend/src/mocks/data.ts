import type { Article } from '../types/article';
import type { Digest } from '../types/digest';
import type { Feed } from '../types/feed';
import type { UserInterest } from '../types/interest';
import type { NewsletterEdition } from '../types/newsletter';
import type { RewindReport } from '../types/rewind';
import type { User } from '../types/user';

export const mockUser: User = {
  id: 1,
  email: 'dev@curately.local',
  name: 'Dev User',
  picture_url: null,
  google_sub: null,
  created_at: '2026-02-01T00:00:00+00:00',
  last_login_at: '2026-02-17T10:00:00+00:00',
};

export const mockArticles: Article[] = [
  // AI/ML category (4 articles, scores 0.75-0.95)
  {
    id: 1,
    source_feed: 'TechCrunch',
    source_url: 'https://techcrunch.com/2026/02/16/gpt-5-launch',
    title: 'GPT-5 Launch Imminent: Key Changes to Expect',
    author: 'Sarah Chen',
    published_at: '2026-02-16T08:30:00Z',
    raw_content: null,
    summary:
      'GPT-5가 곧 출시될 예정이며, 멀티모달 기능이 크게 향상되었습니다. 특히 코드 생성과 추론 능력에서 눈에 띄는 개선이 이루어졌으며, API 가격은 기존 대비 40% 인하될 것으로 보입니다.',
    detailed_summary: null,
    relevance_score: 0.95,
    categories: ['AI/ML'],
    keywords: ['gpt-5', 'openai', 'llm'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: true,
    is_bookmarked: false,
  },
  {
    id: 2,
    source_feed: 'Hacker News',
    source_url: 'https://news.ycombinator.com/item?id=39012345',
    title: 'Building Reliable AI Agents with Tool Use',
    author: 'James Park',
    published_at: '2026-02-16T07:15:00Z',
    raw_content: null,
    summary:
      'AI 에이전트의 도구 사용 패턴을 안정적으로 구현하는 방법을 다룹니다. ReAct 프레임워크와 함수 호출을 결합한 아키텍처가 프로덕션 환경에서 가장 높은 성공률을 보였으며, 에러 복구 전략이 핵심입니다.',
    detailed_summary: null,
    relevance_score: 0.88,
    categories: ['AI/ML'],
    keywords: ['ai-agents', 'tool-use', 'react-framework'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: false,
  },
  {
    id: 3,
    source_feed: 'Medium',
    source_url: 'https://medium.com/@mleng/fine-tuning-llms-practical-guide-2026',
    title: 'Fine-tuning LLMs on Custom Datasets: A Practical Guide',
    author: 'Alex Rivera',
    published_at: '2026-02-15T22:00:00Z',
    raw_content: null,
    summary:
      'LoRA와 QLoRA를 활용한 LLM 파인튜닝 실전 가이드입니다. 데이터셋 준비부터 하이퍼파라미터 최적화까지 단계별로 설명하며, 8GB VRAM GPU에서도 효과적인 학습이 가능한 방법을 소개합니다.',
    detailed_summary: null,
    relevance_score: 0.82,
    categories: ['AI/ML'],
    keywords: ['fine-tuning', 'lora', 'llm', 'machine-learning'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: false,
  },
  {
    id: 4,
    source_feed: 'Dev.to',
    source_url: 'https://dev.to/devops-weekly/state-of-mlops-2026',
    title: 'The State of MLOps in 2026',
    author: 'Maria Kim',
    published_at: '2026-02-15T18:30:00Z',
    raw_content: null,
    summary:
      '2026년 MLOps 생태계의 현황을 분석합니다. 모델 배포 자동화와 모니터링 도구가 성숙기에 접어들었으며, Feature Store와 ML Pipeline 오케스트레이션이 표준 관행으로 자리잡았습니다.',
    detailed_summary: null,
    relevance_score: 0.75,
    categories: ['AI/ML'],
    keywords: ['mlops', 'ml-pipeline', 'model-deployment'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: false,
  },

  // DevOps category (3 articles, scores 0.55-0.78)
  {
    id: 5,
    source_feed: 'Hacker News',
    source_url: 'https://news.ycombinator.com/item?id=39023456',
    title: 'Kubernetes 1.33 Release: What You Need to Know',
    author: 'David Lee',
    published_at: '2026-02-16T06:00:00Z',
    raw_content: null,
    summary:
      'Kubernetes 1.33이 출시되면서 사이드카 컨테이너 네이티브 지원과 개선된 스케줄링 알고리즘이 도입되었습니다. 메모리 사용량이 15% 감소했으며, Pod 시작 시간도 크게 단축되었습니다.',
    detailed_summary:
      '**Background:** Kubernetes 1.33 is a major release that addresses long-standing pain points in container orchestration. The community has been requesting native sidecar support for years, and this release finally delivers it alongside significant performance improvements.\n\n**Key Takeaways:**\n- Native sidecar container support eliminates the need for workarounds and init container hacks\n- Improved scheduling algorithm reduces pod startup time by up to 25%\n- Memory usage reduced by 15% through optimized etcd interactions\n- New priority-based preemption ensures critical workloads always have resources\n- Graduated features: Pod Disruption Conditions and MinReadySeconds for StatefulSets\n\n**Keywords:** kubernetes, sidecar-containers, scheduling, cloud-native',
    relevance_score: 0.78,
    categories: ['DevOps'],
    keywords: ['kubernetes', 'container', 'orchestration'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: true,
  },
  {
    id: 6,
    source_feed: 'Dev.to',
    source_url: 'https://dev.to/infra/terraform-vs-pulumi-2026',
    title: 'Terraform vs Pulumi: Infrastructure as Code Comparison',
    author: 'Chris Wong',
    published_at: '2026-02-15T20:00:00Z',
    raw_content: null,
    summary:
      'Terraform과 Pulumi의 최신 비교 분석입니다. Terraform은 성숙한 생태계와 안정성이 강점이며, Pulumi는 범용 프로그래밍 언어 지원으로 복잡한 인프라 로직 구현에 유리합니다.',
    detailed_summary: null,
    relevance_score: 0.65,
    categories: ['DevOps'],
    keywords: ['terraform', 'pulumi', 'infrastructure-as-code'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: false,
  },
  {
    id: 7,
    source_feed: 'Medium',
    source_url: 'https://medium.com/@devops-pro/gitops-best-practices-prod',
    title: 'GitOps Best Practices for Production Environments',
    author: 'Emily Zhang',
    published_at: '2026-02-15T16:00:00Z',
    raw_content: null,
    summary:
      '프로덕션 환경에서 GitOps를 효과적으로 적용하기 위한 모범 사례를 소개합니다. ArgoCD와 Flux를 활용한 배포 전략, 시크릿 관리, 그리고 롤백 자동화 패턴을 상세히 다룹니다.',
    detailed_summary: null,
    relevance_score: 0.55,
    categories: ['DevOps'],
    keywords: ['gitops', 'argocd', 'deployment'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: false,
  },

  // Backend category (2 articles, scores 0.45-0.72)
  {
    id: 8,
    source_feed: 'Hacker News',
    source_url: 'https://news.ycombinator.com/item?id=39034567',
    title: 'PostgreSQL 17: Performance Improvements Deep Dive',
    author: 'Tom Anderson',
    published_at: '2026-02-16T05:00:00Z',
    raw_content: null,
    summary:
      'PostgreSQL 17의 성능 개선 사항을 심층 분석합니다. 병렬 쿼리 실행이 30% 향상되었고, JSONB 인덱싱 성능도 대폭 개선되었습니다. 대규모 테이블의 VACUUM 작업 효율성도 눈에 띄게 좋아졌습니다.',
    detailed_summary:
      '**Background:** PostgreSQL 17 continues the tradition of annual major releases with a focus on performance. As organizations handle increasingly large datasets, these improvements directly impact query response times and operational costs.\n\n**Key Takeaways:**\n- Parallel query execution improved by 30%, benefiting complex analytical queries\n- JSONB indexing performance significantly enhanced for document-heavy workloads\n- VACUUM operation efficiency improved for large tables, reducing maintenance windows\n- New incremental backup feature reduces backup storage by up to 60%\n- Logical replication now supports failover, enabling true high-availability setups\n\n**Keywords:** postgresql, database-performance, parallel-queries, jsonb',
    relevance_score: 0.72,
    categories: ['Backend'],
    keywords: ['postgresql', 'database', 'performance'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: true,
    is_bookmarked: true,
  },
  {
    id: 9,
    source_feed: 'Medium',
    source_url: 'https://medium.com/@backend-eng/rate-limiter-distributed-systems',
    title: 'Designing Rate Limiters for Distributed Systems',
    author: 'Lisa Chen',
    published_at: '2026-02-15T14:00:00Z',
    raw_content: null,
    summary:
      '분산 시스템에서 효과적인 Rate Limiter를 설계하는 방법을 다룹니다. Token Bucket과 Sliding Window 알고리즘의 트레이드오프를 비교하고, Redis 기반 구현 시 주의할 점을 설명합니다.',
    detailed_summary: null,
    relevance_score: 0.45,
    categories: ['Backend'],
    keywords: ['rate-limiting', 'distributed-systems', 'redis'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: false,
  },

  // Frontend category (1 article, score 0.38)
  {
    id: 10,
    source_feed: 'Dev.to',
    source_url: 'https://dev.to/frontend/react-server-components-production-lessons',
    title: 'React Server Components: Lessons from Production',
    author: 'Ryan Murphy',
    published_at: '2026-02-15T12:00:00Z',
    raw_content: null,
    summary:
      'React Server Components를 프로덕션에 도입한 경험을 공유합니다. 초기 로딩 속도가 40% 개선되었지만, 캐싱 전략과 서버/클라이언트 컴포넌트 경계 설정에서 예상치 못한 복잡성이 발생했습니다.',
    detailed_summary: null,
    relevance_score: 0.38,
    categories: ['Frontend'],
    keywords: ['react', 'server-components', 'performance'],
    newsletter_date: '2026-02-16',
    created_at: '2026-02-16T06:00:00Z',
    updated_at: '2026-02-16T06:00:00Z',
    is_liked: false,
    is_bookmarked: false,
  },
];

export const mockFeeds: Feed[] = [
  {
    id: 1,
    name: 'TechCrunch',
    url: 'https://techcrunch.com/feed/',
    is_active: true,
    last_fetched_at: '2026-02-16T06:00:00Z',
    created_at: '2025-12-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'Hacker News',
    url: 'https://news.ycombinator.com/rss',
    is_active: true,
    last_fetched_at: '2026-02-16T06:00:00Z',
    created_at: '2025-12-01T00:00:00Z',
  },
  {
    id: 3,
    name: 'Medium Engineering',
    url: 'https://medium.com/feed/tag/engineering',
    is_active: true,
    last_fetched_at: '2026-02-16T06:00:00Z',
    created_at: '2025-12-15T00:00:00Z',
  },
  {
    id: 4,
    name: 'Dev.to',
    url: 'https://dev.to/feed',
    is_active: true,
    last_fetched_at: '2026-02-16T06:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 5,
    name: 'Python Weekly',
    url: 'https://us2.campaign-archive.com/feed?u=e2e180baf855ac797ef407fc7&id=9e26887fc5',
    is_active: false,
    last_fetched_at: '2026-02-10T06:00:00Z',
    created_at: '2026-01-15T00:00:00Z',
  },
];

export const mockInterests: UserInterest[] = [
  {
    id: 1,
    user_id: 1,
    keyword: 'machine-learning',
    weight: 5.2,
    source: 'like',
    updated_at: '2026-02-16T10:35:00Z',
  },
  {
    id: 2,
    user_id: 1,
    keyword: 'kubernetes',
    weight: 3.8,
    source: 'like',
    updated_at: '2026-02-15T09:20:00Z',
  },
  {
    id: 3,
    user_id: 1,
    keyword: 'python',
    weight: 3.1,
    source: 'like',
    updated_at: '2026-02-14T14:10:00Z',
  },
  {
    id: 4,
    user_id: 1,
    keyword: 'typescript',
    weight: 2.5,
    source: 'like',
    updated_at: '2026-02-13T11:00:00Z',
  },
  {
    id: 5,
    user_id: 1,
    keyword: 'react',
    weight: 2.0,
    source: 'like',
    updated_at: '2026-02-12T16:45:00Z',
  },
  {
    id: 6,
    user_id: 1,
    keyword: 'devops',
    weight: 1.8,
    source: 'like',
    updated_at: '2026-02-11T08:30:00Z',
  },
  {
    id: 7,
    user_id: 1,
    keyword: 'postgresql',
    weight: 1.5,
    source: 'like',
    updated_at: '2026-02-10T13:15:00Z',
  },
  {
    id: 8,
    user_id: 1,
    keyword: 'terraform',
    weight: 1.0,
    source: 'manual',
    updated_at: '2026-02-09T10:00:00Z',
  },
];

export const mockEditions: NewsletterEdition[] = [
  { date: '2026-02-16', article_count: 10 },
  { date: '2026-02-15', article_count: 8 },
  { date: '2026-02-14', article_count: 12 },
  { date: '2026-02-13', article_count: 7 },
  { date: '2026-02-12', article_count: 9 },
  { date: '2026-02-11', article_count: 11 },
  { date: '2026-02-10', article_count: 6 },
];

export const mockRewindReports: RewindReport[] = [
  {
    id: 4,
    user_id: 1,
    period_start: '2026-02-09',
    period_end: '2026-02-16',
    report_content: {
      overview:
        'This week focused on AI and infrastructure topics. LLM advancements dominated the news cycle, with significant updates from major AI labs. DevOps tooling also saw notable releases, particularly in the Kubernetes ecosystem.',
      suggestions: ['MLOps', 'AI safety', 'Kubernetes security'],
    },
    hot_topics: [
      { topic: 'LLM Agents', count: 5 },
      { topic: 'Kubernetes', count: 3 },
      { topic: 'PostgreSQL', count: 2 },
      { topic: 'MLOps', count: 2 },
    ],
    trend_changes: [
      { keyword: 'machine-learning', direction: 'rising', weight_change: 2.7 },
      { keyword: 'kubernetes', direction: 'rising', weight_change: 1.3 },
      { keyword: 'docker', direction: 'declining', weight_change: -1.2 },
      { keyword: 'react', direction: 'declining', weight_change: -0.5 },
    ],
    created_at: '2026-02-16T07:00:00Z',
  },
  {
    id: 3,
    user_id: 1,
    period_start: '2026-02-02',
    period_end: '2026-02-09',
    report_content: {
      overview:
        'A strong week for backend engineering topics. Database performance and API design were the most discussed areas, with several high-quality articles on PostgreSQL optimization and GraphQL adoption.',
      suggestions: ['Database observability', 'Caching strategies'],
    },
    hot_topics: [
      { topic: 'PostgreSQL', count: 4 },
      { topic: 'GraphQL', count: 3 },
      { topic: 'API Design', count: 3 },
      { topic: 'Caching', count: 2 },
    ],
    trend_changes: [
      { keyword: 'postgresql', direction: 'rising', weight_change: 1.8 },
      { keyword: 'graphql', direction: 'rising', weight_change: 1.5 },
      { keyword: 'machine-learning', direction: 'declining', weight_change: -0.8 },
      { keyword: 'terraform', direction: 'declining', weight_change: -0.3 },
    ],
    created_at: '2026-02-09T07:00:00Z',
  },
  {
    id: 2,
    user_id: 1,
    period_start: '2026-01-26',
    period_end: '2026-02-02',
    report_content: {
      overview:
        'Frontend and DevOps topics led the week. React Server Components gained significant traction, and there was renewed interest in container orchestration with new Kubernetes tooling announcements.',
      suggestions: ['React performance', 'CI automation'],
    },
    hot_topics: [
      { topic: 'React Server Components', count: 4 },
      { topic: 'Docker', count: 3 },
      { topic: 'TypeScript', count: 2 },
      { topic: 'CI/CD', count: 2 },
    ],
    trend_changes: [
      { keyword: 'react', direction: 'rising', weight_change: 2.1 },
      { keyword: 'docker', direction: 'rising', weight_change: 1.6 },
      { keyword: 'python', direction: 'declining', weight_change: -0.9 },
      { keyword: 'kubernetes', direction: 'declining', weight_change: -0.4 },
    ],
    created_at: '2026-02-02T07:00:00Z',
  },
  {
    id: 1,
    user_id: 1,
    period_start: '2026-01-19',
    period_end: '2026-01-26',
    report_content: {
      overview:
        'AI safety and Python ecosystem updates were the dominant themes. New model evaluation frameworks attracted attention, alongside major Python packaging improvements with uv gaining widespread adoption.',
      suggestions: ['Model evaluation', 'Python tooling'],
    },
    hot_topics: [
      { topic: 'AI Safety', count: 5 },
      { topic: 'Python Packaging', count: 3 },
      { topic: 'Model Evaluation', count: 2 },
      { topic: 'WebAssembly', count: 2 },
    ],
    trend_changes: [
      { keyword: 'python', direction: 'rising', weight_change: 2.3 },
      { keyword: 'machine-learning', direction: 'rising', weight_change: 1.1 },
      { keyword: 'react', direction: 'declining', weight_change: -1.4 },
      { keyword: 'devops', direction: 'declining', weight_change: -0.6 },
    ],
    created_at: '2026-01-26T07:00:00Z',
  },
];

// Keep backward-compatible alias for existing code
export const mockRewindReport: RewindReport = mockRewindReports[0];

export const mockDigest: Digest = {
  id: 1,
  digest_date: '2026-02-16',
  content: {
    headline: 'AI 에이전트 혁신과 클라우드 인프라 진화가 개발 생태계를 재편',
    sections: [
      {
        theme: 'AI/ML',
        title: 'AI 에이전트와 LLM의 급격한 진화',
        body: 'GPT-5 출시가 임박한 가운데, 멀티모달 기능과 코드 생성 능력이 크게 향상될 전망입니다. AI 에이전트의 도구 사용 패턴이 프로덕션 환경에서 검증되고 있으며, ReAct 프레임워크와 함수 호출 조합이 가장 높은 성공률을 보이고 있습니다. LLM 파인튜닝의 접근성도 크게 향상되어 8GB VRAM GPU에서도 효과적인 학습이 가능해졌습니다.',
        article_ids: [1, 2, 3],
      },
      {
        theme: 'DevOps',
        title: 'Kubernetes 생태계 진화와 인프라 도구 경쟁',
        body: 'Kubernetes 1.33 출시로 사이드카 컨테이너 네이티브 지원이라는 오랜 숙원이 해결되었습니다. 메모리 사용량 15% 감소와 Pod 시작 시간 단축도 주목할 만합니다. IaC 영역에서는 Terraform과 Pulumi의 경쟁이 심화되고 있으며, GitOps 모범 사례도 성숙기에 접어들고 있습니다.',
        article_ids: [5, 6, 7],
      },
      {
        theme: 'Backend',
        title: '데이터베이스와 분산 시스템의 진보',
        body: 'PostgreSQL 17이 병렬 쿼리 실행 30% 향상과 JSONB 인덱싱 개선을 포함하여 출시되었습니다. 대규모 테이블의 VACUUM 효율성도 크게 개선되었으며, 분산 시스템에서의 Rate Limiter 설계에 대한 심층 분석도 실무에 바로 적용 가능한 수준입니다.',
        article_ids: [8, 9],
      },
    ],
    key_takeaways: [
      'GPT-5 출시 임박 — 멀티모달 기능 향상, API 가격 40% 인하 예정',
      'AI 에이전트의 프로덕션 적용이 가속화, ReAct + 함수 호출 조합이 최적 아키텍처로 부상',
      'Kubernetes 1.33의 사이드카 네이티브 지원으로 컨테이너 오케스트레이션의 오랜 과제 해결',
      'PostgreSQL 17의 병렬 쿼리 30% 향상은 대규모 데이터 처리에 즉시 적용 가능',
    ],
    connections:
      'AI와 인프라 주제가 긴밀하게 연결되어 있습니다. AI 워크로드의 급격한 증가가 Kubernetes와 같은 클라우드 인프라의 성능 개선을 요구하고 있으며, PostgreSQL의 JSONB 성능 향상은 AI 메타데이터 저장과 벡터 인덱싱에 직접적인 이점을 제공합니다. MLOps의 성숙은 이 모든 요소를 연결하는 접착제 역할을 하고 있습니다.',
  },
  article_ids: [1, 2, 3, 5, 6, 7, 8, 9],
  article_count: 8,
  created_at: '2026-02-16T06:30:00Z',
  updated_at: '2026-02-16T06:30:00Z',
};
