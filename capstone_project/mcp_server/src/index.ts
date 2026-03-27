#!/usr/bin/env node

/**
 * MCP Server for IT Support Tools
 *
 * Provides tools for:
 * - VPN status checking
 * - Password reset
 * - Service health monitoring
 * - Network diagnostics
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';

// Tool definitions
const TOOLS: Tool[] = [
  {
    name: 'check_vpn_status',
    description: 'Check the status of VPN connection for a user. Returns connection status, latency, and last connected time.',
    inputSchema: {
      type: 'object',
      properties: {
        user_email: {
          type: 'string',
          description: 'Email address of the user to check VPN status for',
        },
      },
      required: ['user_email'],
    },
  },
  {
    name: 'reset_password',
    description: 'Initiate a password reset for a user account. Sends reset email and returns confirmation.',
    inputSchema: {
      type: 'object',
      properties: {
        user_email: {
          type: 'string',
          description: 'Email address of the user requesting password reset',
        },
        send_email: {
          type: 'boolean',
          description: 'Whether to send reset email immediately (default: true)',
          default: true,
        },
      },
      required: ['user_email'],
    },
  },
  {
    name: 'check_service_health',
    description: 'Check the health status of IT services (email, VPN, file server, etc.)',
    inputSchema: {
      type: 'object',
      properties: {
        service_name: {
          type: 'string',
          description: 'Name of the service to check',
          enum: ['email', 'vpn', 'file_server', 'wifi', 'printer', 'all'],
        },
      },
      required: ['service_name'],
    },
  },
  {
    name: 'run_network_diagnostic',
    description: 'Run network diagnostic tests for a user (ping, traceroute, DNS lookup)',
    inputSchema: {
      type: 'object',
      properties: {
        user_email: {
          type: 'string',
          description: 'Email of user experiencing network issues',
        },
        test_type: {
          type: 'string',
          description: 'Type of network test to run',
          enum: ['ping', 'traceroute', 'dns', 'full'],
          default: 'ping',
        },
      },
      required: ['user_email'],
    },
  },
  {
    name: 'check_printer_queue',
    description: 'Check printer queue status and clear stuck jobs if needed',
    inputSchema: {
      type: 'object',
      properties: {
        printer_name: {
          type: 'string',
          description: 'Name of the printer to check',
        },
        clear_queue: {
          type: 'boolean',
          description: 'Whether to clear stuck jobs (default: false)',
          default: false,
        },
      },
      required: ['printer_name'],
    },
  },
  {
    name: 'agent_triage',
    description:
      'Chat pipeline step 1: classify user message into intent, category, and priority.',
    inputSchema: {
      type: 'object',
      properties: {
        user_message: { type: 'string', description: 'User message text' },
        user_email: { type: 'string', description: 'User email' },
      },
      required: ['user_message', 'user_email'],
    },
  },
  {
    name: 'agent_log_ticket',
    description:
      'Chat pipeline step 2: propose ticket title and metadata from triage (DB row created in Python).',
    inputSchema: {
      type: 'object',
      properties: {
        user_message: { type: 'string' },
        user_email: { type: 'string' },
        intent: { type: 'string' },
        category: { type: 'string' },
        priority: { type: 'string' },
      },
      required: ['user_message', 'user_email'],
    },
  },
  {
    name: 'agent_compose_response',
    description:
      'Chat pipeline step 3: compose final user-facing reply from triage + ticket + optional KB/DB RAG excerpts.',
    inputSchema: {
      type: 'object',
      properties: {
        user_message: { type: 'string' },
        user_email: { type: 'string' },
        triage: { type: 'object', description: 'Output from agent_triage' },
        ticket_mcp: { type: 'object', description: 'Output from agent_log_ticket' },
        ticket_id: { type: 'number', description: 'SQLite ticket id if persisted' },
        rag_kb_text: { type: 'string', description: 'Markdown KB retrieval (Python RAG)' },
        rag_db_text: { type: 'string', description: 'DB tickets/messages retrieval (Python RAG)' },
        rag_kb_sources: {
          type: 'array',
          items: { type: 'string' },
          description: 'KB doc labels for citations (e.g. vpn_setup_guide.md)',
        },
        rag_db_sources: {
          type: 'array',
          items: { type: 'string' },
          description: 'DB record labels (e.g. db_ticket:ticket_110)',
        },
      },
      required: ['user_message', 'user_email'],
    },
  },
];

// Simulated tool implementations
// In production, these would call real APIs

async function checkVPNStatus(userEmail: string): Promise<any> {
  // Simulate VPN status check
  const isConnected = Math.random() > 0.3; // 70% chance connected
  const latency = isConnected ? Math.floor(Math.random() * 100) + 10 : null;

  return {
    status: isConnected ? 'connected' : 'disconnected',
    user_email: userEmail,
    latency_ms: latency,
    last_connected: isConnected
      ? new Date().toISOString()
      : new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    server: isConnected ? 'vpn-us-east-1' : null,
    ip_address: isConnected ? '10.0.1.42' : null,
  };
}

async function resetPassword(userEmail: string, sendEmail: boolean = true): Promise<any> {
  // Simulate password reset
  const resetToken = Math.random().toString(36).substring(2, 15);

  return {
    success: true,
    user_email: userEmail,
    reset_token: resetToken,
    email_sent: sendEmail,
    reset_link: `https://portal.acme.com/reset?token=${resetToken}`,
    expires_in: '24 hours',
    message: sendEmail
      ? `Password reset email sent to ${userEmail}`
      : `Reset link generated for ${userEmail}`,
  };
}

async function checkServiceHealth(serviceName: string): Promise<any> {
  // Simulate service health check
  const services = {
    email: { status: 'operational', uptime: '99.9%', response_time_ms: 45 },
    vpn: { status: 'operational', uptime: '99.5%', response_time_ms: 120 },
    file_server: { status: 'degraded', uptime: '98.2%', response_time_ms: 350 },
    wifi: { status: 'operational', uptime: '99.8%', response_time_ms: 20 },
    printer: { status: 'operational', uptime: '97.5%', response_time_ms: 80 },
  };

  if (serviceName === 'all') {
    return {
      timestamp: new Date().toISOString(),
      services: services,
      overall_status: 'mostly_operational',
    };
  }

  const service = services[serviceName as keyof typeof services];
  if (!service) {
    throw new Error(`Unknown service: ${serviceName}`);
  }

  return {
    service_name: serviceName,
    timestamp: new Date().toISOString(),
    ...service,
  };
}

async function runNetworkDiagnostic(userEmail: string, testType: string = 'ping'): Promise<any> {
  // Simulate network diagnostic
  const tests: any = {
    ping: {
      target: 'gateway.acme.com',
      packets_sent: 4,
      packets_received: 4,
      packet_loss: '0%',
      avg_latency_ms: 15,
      status: 'success',
    },
  };

  if (testType === 'traceroute' || testType === 'full') {
    tests.traceroute = {
      target: 'gateway.acme.com',
      hops: 8,
      total_time_ms: 45,
      status: 'success',
    };
  }

  if (testType === 'dns' || testType === 'full') {
    tests.dns = {
      query: 'portal.acme.com',
      resolved_ip: '192.168.1.100',
      response_time_ms: 12,
      status: 'success',
    };
  }

  return {
    user_email: userEmail,
    test_type: testType,
    timestamp: new Date().toISOString(),
    tests: tests,
    overall_status: 'healthy',
    recommendation: 'Network connectivity is normal',
  };
}

function triageCategoryFromMessage(msg: string): string {
  const m = msg.toLowerCase();
  if (m.includes('password')) return 'PASSWORD';
  if (m.includes('vpn') || m.includes('wifi') || m.includes('network') || m.includes('dns') || m.includes('connection'))
    return 'NETWORK';
  if (m.includes('software') || m.includes('excel') || m.includes('outlook') || m.includes('install'))
    return 'SOFTWARE';
  if (m.includes('laptop') || m.includes('screen') || m.includes('printer') || m.includes('hardware'))
    return 'HARDWARE';
  if (m.includes('access') || m.includes('permission')) return 'ACCESS';
  return 'UNKNOWN';
}

function triagePriorityFromMessage(msg: string): string {
  const m = msg.toLowerCase();
  if (m.includes('urgent') || m.includes('critical') || m.includes('down') || m.includes('outage'))
    return 'HIGH';
  return 'MEDIUM';
}

async function agentTriage(userMessage: string, _userEmail: string): Promise<any> {
  const category = triageCategoryFromMessage(userMessage);
  const priority = triagePriorityFromMessage(userMessage);
  return {
    intent: 'SUPPORT_REQUEST',
    category,
    priority,
    confidence: 0.86,
    rationale: 'MCP triage (keyword rules, TS server)',
  };
}

async function agentLogTicket(args: Record<string, unknown>): Promise<any> {
  const userMessage = String(args.user_message ?? '');
  const snippet = userMessage.slice(0, 72).trim();
  const title = snippet ? `Support: ${snippet}` : 'IT support request';
  return {
    title_suggestion: title.slice(0, 200),
    mcp_stage: 'ready_for_db',
    category: args.category,
    priority: args.priority,
  };
}

function bulletsHardware(msg: string): string[] {
  const m = msg.toLowerCase();
  const out: string[] = [];
  if (
    /crash|crashed|data|lost|disk|drive|won't boot|wont boot|dead|blue screen|bsod/.test(m)
  ) {
    out.push(
      "If it will not boot: stop repeated power cycles; unplug power, hold the power button 10s, then restart with the charger connected.",
      'If it boots even once: copy important files to **OneDrive** or a network share **before** running disk repair or reinstalls.',
      'Avoid saving new large files to the machine if you suspect disk failure—ask IT for imaging/recovery options.'
    );
  }
  if (/screen|display|flicker|black/.test(m)) {
    out.push(
      'External monitor test: if the lid is black but an external display works, note that for IT (possible panel or cable).'
    );
  }
  if (out.length === 0) {
    out.push(
      'Try a full shutdown (not just sleep), then power on with AC power connected.',
      'Run any built-in hardware diagnostics from the vendor (e.g. startup diagnostics) and note error codes for IT.'
    );
  }
  return out.slice(0, 5);
}

function bulletsNetwork(msg: string): string[] {
  const m = msg.toLowerCase();
  const out: string[] = [];
  if (m.includes('vpn')) {
    out.push(
      'Quit the VPN client completely, wait 30 seconds, reopen, and reconnect (watch for MFA prompts).',
      'If unstable on Wi‑Fi, try wired Ethernet once to rule out wireless issues.'
    );
  }
  if (/wifi|wi-fi|wireless/.test(m)) {
    out.push('Forget and rejoin the corporate SSID, or run the OS network troubleshooter.');
  }
  if (out.length === 0) {
    out.push(
      'Check physical connections and reboot the modem/router if on site.',
      'Confirm whether colleagues have the same outage (helps narrow service vs device).'
    );
  }
  return out.slice(0, 5);
}

function bulletsPassword(): string[] {
  return [
    'Use the self-service password portal if your org has one; complete MFA within the time limit.',
    'If locked out after failed attempts, wait for the lockout window or contact the service desk with your verified work email.',
  ];
}

function bulletsSoftware(): string[] {
  return [
    'Note the exact app name and version; try a full quit and relaunch first.',
    'Check for pending OS or app updates; install during a maintenance window if policy allows.',
    'If the app crashes on open, capture a screenshot of the error text for IT (ticket already references your report).',
  ];
}

function bulletsAccess(): string[] {
  return [
    'Confirm which folder, app, or system you need access to and your business reason.',
    'Your manager or resource owner may need to approve—mention them in the ticket thread if asked.',
  ];
}

function bulletsUnknown(): string[] {
  return [
    'Reply with any error codes, screenshots, or “what changed” since it last worked.',
    'If this blocks work, say so in the ticket—priority can be adjusted by the service desk.',
  ];
}

function truncateBlock(s: string, limit = 1400): string {
  const t = (s || '').trim();
  if (t.length <= limit) return t;
  return t.slice(0, limit - 3) + '...';
}

function formatRagCitationsBlock(
  kbSources: string[] | undefined,
  dbSources: string[] | undefined
): string {
  const kb = (kbSources || []).filter((x) => x && String(x).trim()).slice(0, 12);
  const db = (dbSources || []).filter((x) => x && String(x).trim()).slice(0, 12);
  if (kb.length === 0 && db.length === 0) return '';
  const parts: string[] = [];
  if (kb.length) parts.push('**Knowledge base:** ' + kb.join(', '));
  if (db.length) parts.push('**Internal records:** ' + db.join(', '));
  return parts.join('\n');
}

/** Mirrors backend/chat_demo/compose_support_reply.py for real stdio MCP. */
function buildSupportReplyText(
  userMessage: string,
  triage: Record<string, unknown>,
  ticketId: number | undefined,
  sourceNote: string,
  ragKbText?: string,
  ragDbText?: string,
  ragKbSources?: string[],
  ragDbSources?: string[]
): string {
  const cat = String(triage.category ?? 'UNKNOWN').toUpperCase();
  const msg = userMessage || '';
  let bullets: string[] = [];
  switch (cat) {
    case 'HARDWARE':
      bullets = bulletsHardware(msg);
      break;
    case 'NETWORK':
      bullets = bulletsNetwork(msg);
      break;
    case 'PASSWORD':
      bullets = bulletsPassword();
      break;
    case 'SOFTWARE':
      bullets = bulletsSoftware();
      break;
    case 'ACCESS':
      bullets = bulletsAccess();
      break;
    default:
      bullets = bulletsUnknown();
  }

  const lines: string[] = [`**Triage:** category **${cat}** (${sourceNote}).`];
  const kb = (ragKbText || '').trim();
  const db = (ragDbText || '').trim();
  if (kb) {
    lines.push('', '**From knowledge base (markdown RAG):**', truncateBlock(kb));
  }
  if (db) {
    lines.push('', '**From internal tickets / messages (DB RAG):**', truncateBlock(db));
  }
  const cite = formatRagCitationsBlock(ragKbSources, ragDbSources);
  if (cite) {
    lines.push('', '**Citations (retrieval):**', cite);
  }
  lines.push('', '**What to try now:**');
  for (const b of bullets) {
    lines.push(`- ${b}`);
  }
  lines.push('');
  if (ticketId != null && !Number.isNaN(Number(ticketId))) {
    lines.push(
      `**Ticket #${ticketId}** is logged so IT can follow up or escalate if needed.`
    );
  } else {
    lines.push(
      '**Note:** No ticket id in this session—describe your issue again when contacting the service desk.'
    );
  }
  lines.push(
    'You can reply in this chat with updates (error codes, screenshots) to attach context to your request.'
  );
  return lines.join('\n');
}

async function agentComposeResponse(args: Record<string, unknown>): Promise<any> {
  const triage = (args.triage as Record<string, unknown>) || {};
  const tid = args.ticket_id as number | undefined;
  const userMessage = String(args.user_message ?? '');
  const ragKb = String(args.rag_kb_text ?? '');
  const ragDb = String(args.rag_db_text ?? '');
  const ragKbSources = Array.isArray(args.rag_kb_sources)
    ? (args.rag_kb_sources as unknown[]).filter((x): x is string => typeof x === 'string')
    : [];
  const ragDbSources = Array.isArray(args.rag_db_sources)
    ? (args.rag_db_sources as unknown[]).filter((x): x is string => typeof x === 'string')
    : [];
  const reply = buildSupportReplyText(
    userMessage,
    triage,
    tid,
    'MCP TS server',
    ragKb,
    ragDb,
    ragKbSources,
    ragDbSources
  );
  return { reply, tone: 'professional' };
}

async function checkPrinterQueue(printerName: string, clearQueue: boolean = false): Promise<any> {
  // Simulate printer queue check
  const queueLength = Math.floor(Math.random() * 5);
  const hasStuckJobs = queueLength > 3;

  return {
    printer_name: printerName,
    status: queueLength === 0 ? 'idle' : hasStuckJobs ? 'warning' : 'printing',
    queue_length: queueLength,
    stuck_jobs: hasStuckJobs ? 2 : 0,
    cleared_jobs: clearQueue && hasStuckJobs ? 2 : 0,
    message: clearQueue && hasStuckJobs
      ? `Cleared 2 stuck jobs from ${printerName}`
      : `${printerName} has ${queueLength} jobs in queue`,
  };
}

// Create MCP server
const server = new Server(
  {
    name: 'it-support-tools',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Handle tool list request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS,
  };
});

// Handle tool execution request
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'check_vpn_status': {
        const result = await checkVPNStatus(args.user_email as string);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'reset_password': {
        const result = await resetPassword(
          args.user_email as string,
          args.send_email as boolean ?? true
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'check_service_health': {
        const result = await checkServiceHealth(args.service_name as string);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'run_network_diagnostic': {
        const result = await runNetworkDiagnostic(
          args.user_email as string,
          args.test_type as string ?? 'ping'
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'check_printer_queue': {
        const result = await checkPrinterQueue(
          args.printer_name as string,
          args.clear_queue as boolean ?? false
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'agent_triage': {
        const result = await agentTriage(
          args.user_message as string,
          args.user_email as string
        );
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        };
      }

      case 'agent_log_ticket': {
        const result = await agentLogTicket(args as Record<string, unknown>);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        };
      }

      case 'agent_compose_response': {
        const result = await agentComposeResponse(args as Record<string, unknown>);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error executing tool ${name}: ${error}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('IT Support MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
