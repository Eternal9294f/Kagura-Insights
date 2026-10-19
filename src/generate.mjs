const SOURCE_LINKS = [
  'https://groww.in/help/mutual-funds/order/what-is-exit-load--71',
  'https://groww.in/help/mutual-funds/discoverable/what-is-the-exit-load-on-redeeming-before-1-week',
  'https://investor.sebi.gov.in/exit_load.html',
  'https://www.sebi.gov.in/sebi_data/faqfiles/sep-2024/1727242783639.pdf',
  'https://groww.in/blog/10-debt-funds-with-no-exit-load',
  'https://modelcontextprotocol.io/',
];

export const GROWW_HELP_EXIT_LOAD = SOURCE_LINKS[0];
export const SEBI_EXIT_LOAD = SOURCE_LINKS[2];
export const ALL_SOURCE_LINKS = SOURCE_LINKS;

export function wordCount(text) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function fmt(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

function pct(n) {
  return `${Math.round(n * 100)}%`;
}

export function buildWeeklyPulse(insights) {
  const { product, window, total, topThemes, feeIssue } = insights;
  const [t1, t2, t3] = topThemes;
  const q = insights.quotes.map((x) => x.text);

  const lines = [
    `# Weekly Product Pulse — ${product}`,
    '',
    `**Week of ${fmt(window.end)}** · ${total} reviews · ${fmt(window.start)} – ${fmt(window.end)}`,
    '',
    '**Top themes**',
    `1. **${t1.name}** — ${t1.count} reviews (${pct(t1.share)}): crashes, hangs and lag, worst around market open.`,
    `2. **${t2.name}** — ${t2.count} reviews (${pct(t2.share)}): redemption deductions read as hidden fees, led by ${feeIssue.term.toLowerCase()} (${feeIssue.mentions} mentions, ${feeIssue.confusionMentions} confused).`,
    `3. **${t3.name}** — ${t3.count} reviews (${pct(t3.share)}): tickets open 5–10 days, template replies, no callbacks.`,
    '',
    '**Quotes**',
    ...q.map((text) => `- “${text}”`),
    '',
    '**Key observation**',
    `Stability is the loudest theme by volume, but the sharpest pain is ${feeIssue.term.toLowerCase()} confusion: ${feeIssue.confusionMentions} of ${feeIssue.mentions} mentions treat the deduction as a Groww charge, not a fund-house cost. Crashes cluster 09:15–09:30 IST; charge complaints cluster within days of first redemption.`,
    '',
    '**Action ideas**',
    `1. Show estimated ${feeIssue.term.toLowerCase()} (amount + %) on the redeem confirmation screen, linking the scheme's exit-load terms.`,
    '2. Market-hours crash budget: alert on any crash 09:15–09:30 IST; freeze releases during that window.',
    '3. In-app fee explainer card on fund pages (exit load, expense ratio) + attach redemption transaction IDs to charge-related tickets.',
    '',
  ];

  const text = lines.join('\n').trimEnd();
  const words = wordCount(text);
  if (words > 250) throw new Error(`Weekly pulse is ${words} words (> 250). Trim the template.`);
  return { text, words };
}

export function buildFeeExplainer(insights) {
  const fee = insights.feeIssue.term;
  const end = fmt(insights.window.end);

  const bullets = [
    `${fee} is a fee charged by the mutual fund scheme (the fund house), not by Groww or any broker, when units are redeemed before a period specified for that scheme.`,
    `The rate and qualifying period are scheme-specific and defined in each scheme's offer document/SID — for example some equity schemes charge about 1% if redeemed within a year, while many funds charge nothing after 7–30 days.`,
    `It is deducted automatically from redemption proceeds; Groww shows the approximate ${fee.toLowerCase()} on the redeem order screen before you confirm.`,
    `It is separate from brokerage, GST, STT, stamp duty and capital-gains tax — none of these are ${fee.toLowerCase()}.`,
    `Redeeming before the scheme's ${fee.toLowerCase()} period ends reduces the amount credited; redeeming after it typically results in no deduction.`,
    `Official sources: Groww help — What is exit load? (${GROWW_HELP_EXIT_LOAD}) · SEBI investor education — Exit Load (${SEBI_EXIT_LOAD})`,
  ];

  if (bullets.length > 6) throw new Error('Fee explainer exceeds 6 bullets.');
  const text = [
    `# Fee explainer: ${fee} (mutual funds)`,
    '',
    `Last checked: ${end}`,
    '',
    ...bullets.map((b) => `- ${b}`),
  ].join('\n');
  return { text, bullets };
}

export function buildPayload(insights, pulseText) {
  const { feeIssue, topThemes, window } = insights;
  return {
    date: window.end,
    top_themes: topThemes.map((t) => ({ name: t.name, count: t.count })),
    weekly_pulse: pulseText,
    identified_fee_issue: `${feeIssue.term} deducted on mutual-fund redemption is being read by users as a hidden Groww fee (${feeIssue.confusionMentions} of ${feeIssue.mentions} fee mentions show confusion about who charges it and when it applies).`,
    explanation_bullets: buildFeeExplainer(insights).bullets,
    source_links: ALL_SOURCE_LINKS,
  };
}

export function buildEmailDraft(insights, pulseText, explainerText) {
  const subject = `Weekly Product Pulse + Customer Clarification — ${insights.product} (week of ${insights.window.end})`;
  const body = [
    'Hi team,',
    '',
    'This week\'s review intelligence for the Groww app, followed by a customer-facing clarification on the fee we keep seeing in reviews. Draft only — not sent.',
    '',
    '=== WEEKLY PRODUCT PULSE ===',
    '',
    pulseText,
    '',
    '=== CUSTOMER CLARIFICATION: FEE EXPLAINER ===',
    '',
    explainerText,
    '',
    '— Generated by groww-insights workflow (approval-gated MCP draft)',
  ].join('\n');
  return { subject, body, recipients: ['product-team@groww.example'] };
}

export async function maybeLlmGenerate(insights) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return null;
  const prompt = [
    'You are a product analyst. Using ONLY the structured review insights below, write:',
    '1) A Weekly Product Pulse in markdown, max 250 words: top 3 themes, 3 verbatim quotes, one key observation, 3 action ideas.',
    '2) A fee explainer as exactly 6 neutral, facts-only bullets (no hype, no advice).',
    'Do not invent numbers.',
    JSON.stringify({
      window: insights.window,
      total: insights.total,
      topThemes: insights.topThemes.map((t) => ({ name: t.name, count: t.count })),
      quotes: insights.quotes,
      feeIssue: insights.feeIssue,
      sources: ALL_SOURCE_LINKS,
    }),
  ].join('\n\n');

  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
    body: JSON.stringify({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.2,
    }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.choices?.[0]?.message?.content ?? null;
}
