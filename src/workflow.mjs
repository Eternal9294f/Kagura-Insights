import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { loadReviews, analyzeReviews } from './analyze.mjs';
import {
  buildWeeklyPulse,
  buildFeeExplainer,
  buildPayload,
  buildEmailDraft,
  maybeLlmGenerate,
} from './generate.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUTPUTS = path.join(ROOT, 'outputs');
fs.mkdirSync(OUTPUTS, { recursive: true });

const flags = new Set(process.argv.slice(2));

async function requestApproval(payload) {
  if (flags.has('--yes')) return 'y';
  if (flags.has('--no')) return 'n';
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log('\n============ MCP APPROVAL REQUIRED ============');
  console.log(`Pending actions (both approval-gated, no email will ever be sent):`);
  console.log('  1. append_note       -> append to outputs/notes-log.md');
  console.log('  2. create_email_draft -> write outputs/email-draft.md (draft only)');
  console.log(`Date: ${payload.date} | Fee issue: ${payload.identified_fee_issue.slice(0, 80)}...`);
  console.log('================================================');
  const answer = (await rl.question('Approve these MCP actions? [y/N] ')).trim().toLowerCase();
  rl.close();
  return answer;
}

async function runMcpActions(payload, email) {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [path.join(ROOT, 'src', 'mcp-server.mjs')],
    env: { ...process.env, OUTPUTS_DIR: OUTPUTS },
  });
  const client = new Client({ name: 'groww-insights-client', version: '1.0.0' });
  await client.connect(transport);
  try {
    const r1 = await client.callTool({ name: 'append_note', arguments: payload });
    console.log('[MCP] append_note       ->', r1.content?.[0]?.text);
    const r2 = await client.callTool({ name: 'create_email_draft', arguments: email });
    console.log('[MCP] create_email_draft ->', r2.content?.[0]?.text);
  } finally {
    await client.close();
  }
}

async function main() {
  console.log('groww-insights workflow starting...');

  // Step 1: analyze raw reviews
  const reviews = loadReviews(path.join(ROOT, 'reviews.csv'));
  const insights = analyzeReviews(reviews);
  console.log(`Loaded ${insights.total} reviews (${insights.window.start} -> ${insights.window.end}), avg rating ${insights.avgRating}`);
  for (const t of insights.themes) console.log(`  - ${t.name}: ${t.count} (${Math.round(t.share * 100)}%)`);
  console.log(`Detected recurring fee confusion: ${insights.feeIssue?.term ?? 'none'} (${insights.feeIssue?.confusionMentions ?? 0}/${insights.feeIssue?.mentions ?? 0} confused)`);

  // Step 2 + 3: generate pulse and fee explainer (LLM if OPENAI_API_KEY set, else authored templates)
  let pulse, explainer;
  const llmText = await maybeLlmGenerate(insights);
  if (llmText) {
    console.log('Generation mode: OPENAI_API_KEY present -> LLM');
    pulse = { text: llmText, words: null };
    explainer = { text: llmText, bullets: [] };
  } else {
    console.log('Generation mode: no OPENAI_API_KEY -> AI-authored templates (documented in README)');
    pulse = buildWeeklyPulse(insights);
    explainer = buildFeeExplainer(insights);
  }
  console.log(`Weekly pulse: ${pulse.words ?? '?'} words (limit 250)`);
  fs.writeFileSync(path.join(OUTPUTS, 'weekly-pulse.md'), pulse.text + '\n', 'utf8');
  fs.writeFileSync(path.join(OUTPUTS, 'fee-explainer.md'), explainer.text + '\n', 'utf8');
  console.log('Wrote outputs/weekly-pulse.md and outputs/fee-explainer.md');

  // Step 4: approval-gated MCP actions
  const payload = buildPayload(insights, pulse.text);
  const email = buildEmailDraft(insights, pulse.text, explainer.text);
  const answer = await requestApproval(payload);

  if (answer !== 'y') {
    console.log('DENIED by user (or default). No MCP tools were called. Notes doc and email draft untouched.');
    process.exitCode = 2;
    return;
  }

  console.log('APPROVED -> connecting MCP client (stdio) to local MCP server...');
  await runMcpActions(payload, email);
  console.log('\nDone. Artifacts in outputs/: weekly-pulse.md, fee-explainer.md, notes-log.md, email-draft.md');
}

main().catch((err) => {
  console.error('Workflow failed:', err);
  process.exit(1);
});
