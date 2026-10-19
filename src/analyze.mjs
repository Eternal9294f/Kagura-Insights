import fs from 'node:fs';

export const PRODUCT = 'Groww app';

const THEMES = [
  {
    id: 'app-stability',
    name: 'App stability & performance',
    keywords: /\b(crash(es|ed|ing)?|hang(s|ing)?|lag(s|ging)?|slow(ly)?|freeze(s|s)?|frozen|bug(s|gy)?|stuck|loading|black screen|spinner|restart(s|ed)?|refresh(es|ed)?|random(ly)?|closes by itself|takes ages)\b/i,
  },
  {
    id: 'pricing-charges',
    name: 'Pricing & charges',
    keywords: /\b(exit load|charge(s|d)?|fee(s)?|gst|brokerage|hidden|deducted|deduction|stt|penalty|transparent|cost(s)?|expensive|breakup)\b/i,
  },
  {
    id: 'support-kyc',
    name: 'Support & KYC',
    keywords: /\b(support|ticket(s)?|kyc|callback|chatbot|complaint(s)?|refund(s|ed)?|response|resolved|template|wait time|agent|human|verification)\b/i,
  },
  {
    id: 'charts-trading-ux',
    name: 'Charts & trading UX',
    keywords: /\b(chart(s)?|watchlist|alert(s)?|indicator(s)?|timeframe|bracket orders?|order types|order pad|market depth|drawing tools|limit order)\b/i,
  },
  {
    id: 'sip-investing',
    name: 'SIP & investing',
    keywords: /\b(sip(s)?|mutual fund(s)?|lumpsum|nav|xirr|folio|portfolio|fund pages|goal based|mandate|expense ratio|auto sweep)\b/i,
  },
];

const FEE_TERMS = [
  { id: 'exit_load', label: 'Exit load', pattern: /exit[\s-]?load/i },
  { id: 'gst', label: 'GST', pattern: /\bgst\b/i },
  { id: 'brokerage', label: 'Brokerage', pattern: /brokerage/i },
  { id: 'stt', label: 'STT', pattern: /\bstt\b/i },
];

const CONFUSION =
  /why|hidden|confus|unclear|surprise|not shown|never showed|not warned|no explanation|still do not understand|explain this|impossible to find|got less|did not expect|or what|not transparent|not notified/i;

export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.some((v) => v !== '')) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); if (row.some((v) => v !== '')) rows.push(row); }
  const [header, ...body] = rows;
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h.trim(), (r[i] ?? '').trim()])));
}

export function loadReviews(csvPath) {
  return parseCsv(fs.readFileSync(csvPath, 'utf8'));
}

function scoreThemes(text) {
  return THEMES.map((t) => ({ ...t, score: (text.match(new RegExp(t.keywords, 'gi')) || []).length }));
}

export function analyzeReviews(reviews) {
  const dated = reviews
    .filter((r) => r.date && r.review_text)
    .sort((a, b) => a.date.localeCompare(b.date));

  const window = { start: dated[0].date, end: dated.at(-1).date };
  const total = dated.length;
  const avgRating =
    dated.reduce((s, r) => s + Number(r.rating || 0), 0) / total;

  const clustered = dated.map((r) => {
    const scores = scoreThemes(r.review_text);
    const best = scores.reduce((a, b) => (b.score > a.score ? b : a));
    return { ...r, theme: best.score > 0 ? best.id : 'other', confidence: best.score };
  });

  const themes = THEMES.map((t) => {
    const members = clustered.filter((r) => r.theme === t.id);
    const quotes = members
      .filter((r) => CONFUSION.test(r.review_text) || Number(r.rating) <= 2)
      .sort((a, b) => a.review_text.length - b.review_text.length || a.review_id.localeCompare(b.review_id));
    const fallback = [...members].sort((a, b) => a.review_text.length - b.review_text.length);
    return {
      id: t.id,
      name: t.name,
      count: members.length,
      share: members.length / total,
      quote: (quotes[0] ?? fallback[0])?.review_text ?? null,
      worstQuote: quotes.at(-1)?.review_text ?? null,
      reviews: members,
    };
  })
    .filter((t) => t.count > 0)
    .sort((a, b) => b.count - a.count || a.id.localeCompare(b.id));

  const topThemes = themes.slice(0, 3);
  const quotes = topThemes.map((t) => ({ theme: t.name, text: t.quote }));

  const feeCandidates = FEE_TERMS.map((f) => {
    const mentions = dated.filter((r) => f.pattern.test(r.review_text));
    const confused = mentions.filter((r) => CONFUSION.test(r.review_text));
    return { ...f, mentions: mentions.length, confusionMentions: confused.length, reviews: confused };
  })
    .filter((f) => f.mentions >= 3)
    .sort((a, b) => b.confusionMentions - a.confusionMentions || b.mentions - a.mentions);

  const fee = feeCandidates[0] ?? null;

  return {
    product: PRODUCT,
    window,
    total,
    avgRating: Math.round(avgRating * 10) / 10,
    themes,
    topThemes,
    quotes,
    feeIssue: fee
      ? {
          term: fee.label,
          id: fee.id,
          mentions: fee.mentions,
          confusionMentions: fee.confusionMentions,
          quotes: fee.reviews.slice(0, 3).map((r) => r.review_text),
        }
      : null,
  };
}
