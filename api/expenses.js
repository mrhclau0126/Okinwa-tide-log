// Vercel serverless function: /api/expenses
// Proxies expense read/write/delete to a Notion database, keeping the
// Notion integration token safely server-side (never exposed to the browser).
//
// Required environment variables (set these in Vercel Project Settings -> Environment Variables):
//   NOTION_TOKEN        - your Notion integration's "Internal Integration Secret"
//   NOTION_DATABASE_ID  - the database ID the integration has been shared with
//
// Expected Notion database properties (exact names, case-sensitive):
//   Name      (title)
//   Day       (select)      e.g. "Day 1" ... "Day 7"
//   Date      (date)
//   Category  (select)      e.g. "🏨住宿" "🍽餐飲" "🚗交通" "🎫門票活動" "🛍購物" "其他"
//   Amount    (number)
//   Currency  (select)      "JPY" or "HKD"
//   Payer     (select)      "爸爸" "媽媽" "公共"
//   Note      (rich_text)

const NOTION_VERSION = '2022-06-28';

function notionHeaders() {
  return {
    'Authorization': `Bearer ${process.env.NOTION_TOKEN}`,
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json',
  };
}

function pageToExpense(page) {
  const p = page.properties || {};
  const getTitle = (prop) => (prop?.title || []).map((t) => t.plain_text).join('') || '';
  const getSelect = (prop) => prop?.select?.name || '';
  const getNumber = (prop) => (typeof prop?.number === 'number' ? prop.number : 0);
  const getDate = (prop) => prop?.date?.start || '';
  const getRichText = (prop) => (prop?.rich_text || []).map((t) => t.plain_text).join('') || '';
  return {
    id: page.id,
    name: getTitle(p.Name),
    day: getSelect(p.Day),
    date: getDate(p.Date),
    category: getSelect(p.Category),
    amount: getNumber(p.Amount),
    currency: getSelect(p.Currency) || 'JPY',
    payer: getSelect(p.Payer),
    note: getRichText(p.Note),
  };
}

async function handleGet(req, res) {
  const dbId = process.env.NOTION_DATABASE_ID;
  const r = await fetch(`https://api.notion.com/v1/databases/${dbId}/query`, {
    method: 'POST',
    headers: notionHeaders(),
    body: JSON.stringify({
      sorts: [{ property: 'Date', direction: 'ascending' }],
      page_size: 100,
    }),
  });
  if (!r.ok) {
    const err = await r.text();
    return res.status(r.status).json({ error: 'notion_query_failed', detail: err });
  }
  const data = await r.json();
  const expenses = (data.results || []).map(pageToExpense);
  return res.status(200).json({ expenses });
}

async function handlePost(req, res) {
  const dbId = process.env.NOTION_DATABASE_ID;
  const b = req.body || {};
  if (!b.name || !b.amount) {
    return res.status(400).json({ error: 'missing_fields', detail: 'name and amount are required' });
  }
  const properties = {
    Name: { title: [{ text: { content: String(b.name) } }] },
    Day: b.day ? { select: { name: String(b.day) } } : undefined,
    Date: b.date ? { date: { start: b.date } } : undefined,
    Category: b.category ? { select: { name: String(b.category) } } : undefined,
    Amount: { number: Number(b.amount) },
    Currency: { select: { name: b.currency || 'JPY' } },
    Payer: b.payer ? { select: { name: String(b.payer) } } : undefined,
    Note: b.note ? { rich_text: [{ text: { content: String(b.note) } }] } : undefined,
  };
  Object.keys(properties).forEach((k) => properties[k] === undefined && delete properties[k]);

  const r = await fetch('https://api.notion.com/v1/pages', {
    method: 'POST',
    headers: notionHeaders(),
    body: JSON.stringify({ parent: { database_id: dbId }, properties }),
  });
  if (!r.ok) {
    const err = await r.text();
    return res.status(r.status).json({ error: 'notion_create_failed', detail: err });
  }
  const page = await r.json();
  return res.status(200).json({ expense: pageToExpense(page) });
}

async function handleDelete(req, res) {
  const id = req.query.id || (req.body && req.body.id);
  if (!id) return res.status(400).json({ error: 'missing_id' });
  const r = await fetch(`https://api.notion.com/v1/pages/${id}`, {
    method: 'PATCH',
    headers: notionHeaders(),
    body: JSON.stringify({ archived: true }),
  });
  if (!r.ok) {
    const err = await r.text();
    return res.status(r.status).json({ error: 'notion_delete_failed', detail: err });
  }
  return res.status(200).json({ ok: true });
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (!process.env.NOTION_TOKEN || !process.env.NOTION_DATABASE_ID) {
    return res.status(500).json({
      error: 'not_configured',
      detail: 'NOTION_TOKEN / NOTION_DATABASE_ID environment variables are not set on this deployment.',
    });
  }

  try {
    if (req.method === 'GET') return await handleGet(req, res);
    if (req.method === 'POST') return await handlePost(req, res);
    if (req.method === 'DELETE') return await handleDelete(req, res);
    return res.status(405).json({ error: 'method_not_allowed' });
  } catch (e) {
    return res.status(500).json({ error: 'server_error', detail: String(e) });
  }
};
