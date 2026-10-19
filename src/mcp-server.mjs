import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import fs from 'node:fs';
import path from 'node:path';

const outputsDir = path.resolve(process.env.OUTPUTS_DIR || path.join(process.cwd(), 'outputs'));
fs.mkdirSync(outputsDir, { recursive: true });

const server = new McpServer({ name: 'groww-insights-mcp', version: '1.0.0' });

const payloadShape = {
  date: z.string().describe('ISO date of the weekly entry'),
  top_themes: z
    .array(z.object({ name: z.string(), count: z.number() }))
    .describe('Top 3 review themes with review counts'),
  weekly_pulse: z.string().describe('Weekly Product Pulse text (markdown)'),
  identified_fee_issue: z.string().describe('The recurring fee/charge confusion'),
  explanation_bullets: z.array(z.string()).max(6).describe('Fee explainer bullets (max 6, facts only)'),
  source_links: z.array(z.string()).describe('Official source URLs backing the explainer'),
};

server.registerTool(
  'append_note',
  {
    title: 'Append weekly product note',
    description:
      'APPEND-ONLY, approval-gated. Appends the weekly pulse + fee insight as a dated JSON entry to the team notes doc (outputs/notes-log.md).',
    inputSchema: payloadShape,
  },
  async (args) => {
    const file = path.join(outputsDir, 'notes-log.md');
    const entry = {
      date: args.date,
      top_themes: args.top_themes,
      weekly_pulse: args.weekly_pulse,
      identified_fee_issue: args.identified_fee_issue,
      explanation_bullets: args.explanation_bullets,
      source_links: args.source_links,
    };
    const md = `\n\n---\n\n## Entry — ${args.date}\n\n\`\`\`json\n${JSON.stringify(entry, null, 2)}\n\`\`\`\n`;
    fs.appendFileSync(file, md, 'utf8');
    return {
      content: [{ type: 'text', text: `Appended entry for ${args.date} to ${file}` }],
      isError: false,
    };
  },
);

server.registerTool(
  'create_email_draft',
  {
    title: 'Create email draft (never sends)',
    description:
      'APPEND-ONLY, approval-gated. Writes an email DRAFT (subject + body) to outputs/email-draft.md. This tool does NOT send email — no SMTP/API call is made.',
    inputSchema: {
      subject: z.string().describe('Email subject line'),
      body: z.string().describe('Email body (markdown or plain text)'),
      recipients: z.array(z.string()).describe('Draft recipient placeholders'),
    },
  },
  async (args) => {
    const file = path.join(outputsDir, 'email-draft.md');
    const md = `# Email draft (DRAFT ONLY — not sent)\n\n- **To:** ${args.recipients.join(', ')}\n- **Subject:** ${args.subject}\n\n---\n\n${args.body}\n`;
    fs.writeFileSync(file, md, 'utf8');
    return {
      content: [{ type: 'text', text: `Email draft written to ${file} (nothing was sent)` }],
      isError: false,
    };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
